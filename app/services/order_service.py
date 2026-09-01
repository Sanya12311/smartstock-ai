"""
Real order placement against a user's connected Dhan account.

Every validation this module CAN perform (connected broker, symbol exists,
quantity/price/order-type sanity, simplified market-hours check) is
enforced before ever calling the broker. Checks requiring data we don't
have — real account balance, actual demat holdings — are deliberately left
to Dhan's own authoritative rejection rather than us fabricating a check we
can't verify (that would need Dhan's separate Funds/Holdings APIs, not yet
integrated).
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.brokers.dhan_broker import DhanBroker, DhanBrokerError
from app.models.broker_account import BrokerAccount
from app.models.notification import Notification
from app.models.order import Order
from app.models.stock import Stock
from app.models.user import User
from app.services import stock_service
from app.utils import encryption
from app.utils.market_hours import is_market_open

logger = logging.getLogger(__name__)
broker = DhanBroker()

VALID_ORDER_TYPES = {"MARKET", "LIMIT"}
NON_TERMINAL_STATUSES = {"TRANSIT", "PENDING"}
TERMINAL_STATUSES = {"TRADED", "PART_TRADED", "REJECTED", "CANCELLED", "EXPIRED"}


class OrderValidationError(Exception):
    """Raised when an order fails our own pre-broker validation checks."""


def _validate_order_shape(quantity: int, order_type: str, price: Optional[float]) -> None:
    if quantity <= 0:
        raise OrderValidationError("quantity must be greater than 0")
    if order_type not in VALID_ORDER_TYPES:
        raise OrderValidationError(f"order_type must be one of {sorted(VALID_ORDER_TYPES)}")
    if order_type == "LIMIT" and (price is None or price <= 0):
        raise OrderValidationError("price is required and must be positive for LIMIT orders")


def _get_connected_broker(db: Session, user: User) -> BrokerAccount:
    account = db.query(BrokerAccount).filter(BrokerAccount.user_id == user.id).first()
    if account is None or account.status != "CONNECTED":
        raise OrderValidationError(
            "No connected broker account. Connect Dhan via /broker/connect/start first."
        )
    return account


def preview_order(
    db: Session, user: User, symbol: str, side: str, quantity: int, order_type: str, price: Optional[float]
) -> dict:
    if side not in ("BUY", "SELL"):
        raise OrderValidationError("side must be 'BUY' or 'SELL'")
    _validate_order_shape(quantity, order_type, price)

    stock = stock_service.get_stock_by_symbol(db, symbol)
    if stock is None:
        raise OrderValidationError(f"Stock '{symbol}' not found")

    current_price, price_status = stock_service.resolve_current_price(stock)
    reference_price = price if order_type == "LIMIT" else current_price
    estimated_value = (
        round(reference_price * quantity, 2) if reference_price is not None else None
    )

    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "side": side,
        "quantity": quantity,
        "order_type": order_type,
        "price": price,
        "current_market_price": current_price,
        "price_status": price_status,
        "estimated_value": estimated_value,
        "market_open": is_market_open(),
    }


def _place_real_order(
    db: Session, user: User, symbol: str, side: str, quantity: int, order_type: str, price: Optional[float]
) -> Order:
    _validate_order_shape(quantity, order_type, price)

    if not is_market_open():
        raise OrderValidationError(
            "Market appears closed (NSE hours: 9:15-15:30 IST, Mon-Fri; exchange holidays "
            "are not accounted for by this check)."
        )

    stock: Optional[Stock] = stock_service.get_stock_by_symbol(db, symbol)
    if stock is None:
        raise OrderValidationError(f"Stock '{symbol}' not found")

    broker_account = _get_connected_broker(db, user)
    access_token = encryption.decrypt(broker_account.access_token_encrypted)
    order_price = price if order_type == "LIMIT" else 0.0

    logger.info(
        "Order request: user_id=%s %s %s qty=%s type=%s", user.id, side, stock.symbol, quantity, order_type
    )

    try:
        result = broker.place_order(
            access_token=access_token,
            client_id=broker_account.dhan_client_id,
            security_id=stock.security_id,
            exchange_segment=stock.exchange_segment,
            transaction_type=side,
            quantity=quantity,
            order_type=order_type,
            product_type="CNC",  # delivery/investment orders, not intraday leverage
            price=order_price,
        )
    except DhanBrokerError as exc:
        order = Order(
            user_id=user.id,
            broker_name=broker_account.broker_name,
            symbol=stock.symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            status="REJECTED",
            rejection_reason=str(exc),
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        logger.warning("Order response: user_id=%s order_id=%s REJECTED: %s", user.id, order.id, exc)
        return order

    logger.info(
        "Order response: user_id=%s broker_order_id=%s status=%s",
        user.id,
        result.get("order_id"),
        result.get("order_status"),
    )

    order = Order(
        user_id=user.id,
        broker_name=broker_account.broker_name,
        symbol=stock.symbol,
        side=side,
        quantity=quantity,
        order_type=order_type,
        price=price,
        broker_order_id=result.get("order_id"),
        status=result.get("order_status", "PENDING"),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def place_buy_order(
    db: Session, user: User, symbol: str, quantity: int, order_type: str, price: Optional[float] = None
) -> Order:
    return _place_real_order(db, user, symbol, "BUY", quantity, order_type, price)


def place_sell_order(
    db: Session, user: User, symbol: str, quantity: int, order_type: str, price: Optional[float] = None
) -> Order:
    return _place_real_order(db, user, symbol, "SELL", quantity, order_type, price)


def list_orders(
    db: Session,
    user: User,
    status_filter: Optional[str] = None,
    symbol: Optional[str] = None,
    side: Optional[str] = None,
) -> List[Order]:
    query = db.query(Order).filter(Order.user_id == user.id)
    if status_filter:
        query = query.filter(Order.status == status_filter.upper())
    if symbol:
        query = query.filter(Order.symbol == symbol.upper())
    if side:
        query = query.filter(Order.side == side.upper())
    return query.order_by(Order.created_at.desc()).all()


def get_order(db: Session, user: User, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if order is None:
        raise ValueError("Order not found")
    return order


def list_trades(db: Session, user: User) -> List[Order]:
    return (
        db.query(Order)
        .filter(Order.user_id == user.id, Order.status.in_(["TRADED", "PART_TRADED"]))
        .order_by(Order.created_at.desc())
        .all()
    )


def refresh_order_status(db: Session, user: User, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if order is None:
        raise ValueError("Order not found")
    if order.broker_order_id is None:
        return order  # never reached the broker (e.g. rejected pre-placement)

    broker_account = _get_connected_broker(db, user)
    access_token = encryption.decrypt(broker_account.access_token_encrypted)

    result = broker.get_order_status(access_token, broker_account.dhan_client_id, order.broker_order_id)
    if result.get("order_status"):
        order.status = result["order_status"]
    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, user: User, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if order is None:
        raise ValueError("Order not found")

    if order.broker_order_id is None:
        raise OrderValidationError("This order never reached the broker, so there is nothing to cancel.")
    if order.status not in NON_TERMINAL_STATUSES:
        raise OrderValidationError(
            f"Order is already {order.status} and can no longer be cancelled."
        )

    broker_account = _get_connected_broker(db, user)
    access_token = encryption.decrypt(broker_account.access_token_encrypted)

    logger.info("Order cancel request: user_id=%s order_id=%s broker_order_id=%s", user.id, order.id, order.broker_order_id)
    result = broker.cancel_order(access_token, broker_account.dhan_client_id, order.broker_order_id)
    order.status = result.get("order_status") or "CANCELLED"
    db.commit()
    db.refresh(order)
    logger.info("Order cancel response: user_id=%s order_id=%s status=%s", user.id, order.id, order.status)
    return order


def refresh_all_pending_orders(db: Session) -> List[dict]:
    """
    Called periodically by app/services/order_scheduler.py — there's no
    webhook/postback integration, so this is how PENDING/TRANSIT orders
    ever find out they became TRADED/REJECTED/etc. Groups by user so each
    user's broker token is only decrypted once per cycle, not once per order.
    Returns the notifications created for orders that reached a terminal
    status, so the caller can push them over the notification WebSocket.
    """
    pending_orders = (
        db.query(Order)
        .filter(Order.status.in_(NON_TERMINAL_STATUSES), Order.broker_order_id.isnot(None))
        .all()
    )
    if not pending_orders:
        return []

    orders_by_user: Dict[int, List[Order]] = {}
    for order in pending_orders:
        orders_by_user.setdefault(order.user_id, []).append(order)

    created_notifications: List[dict] = []

    for user_id, user_orders in orders_by_user.items():
        broker_account = (
            db.query(BrokerAccount)
            .filter(BrokerAccount.user_id == user_id, BrokerAccount.status == "CONNECTED")
            .first()
        )
        if broker_account is None:
            continue
        access_token = encryption.decrypt(broker_account.access_token_encrypted)

        for order in user_orders:
            try:
                result = broker.get_order_status(
                    access_token, broker_account.dhan_client_id, order.broker_order_id
                )
            except DhanBrokerError:
                continue

            new_status = result.get("order_status")
            if not new_status or new_status == order.status:
                continue

            order.status = new_status
            db.commit()

            if new_status in TERMINAL_STATUSES:
                notification = Notification(
                    user_id=user_id,
                    symbol=order.symbol,
                    title=f"Order {new_status.replace('_', ' ').title()}",
                    message=f"Your {order.side} order for {order.quantity} {order.symbol} is now {new_status}.",
                    category="ORDER",
                )
                db.add(notification)
                db.commit()
                db.refresh(notification)
                created_notifications.append(
                    {
                        "id": notification.id,
                        "user_id": user_id,
                        "symbol": notification.symbol,
                        "title": notification.title,
                        "message": notification.message,
                        "category": notification.category,
                        "created_at": notification.created_at.isoformat(),
                    }
                )

    return created_notifications
