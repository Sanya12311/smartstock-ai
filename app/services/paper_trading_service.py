from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.paper_account import STARTING_BALANCE, PaperAccount
from app.models.paper_holding import PaperHolding
from app.models.paper_order import PaperOrder
from app.models.stock import Stock
from app.models.user import User
from app.services import stock_service


def get_or_create_account(db: Session, user: User) -> PaperAccount:
    account = db.query(PaperAccount).filter(PaperAccount.user_id == user.id).first()
    if account is not None:
        return account

    account = PaperAccount(user_id=user.id, balance=STARTING_BALANCE)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def _get_holding(db: Session, user: User, symbol: str) -> Optional[PaperHolding]:
    return (
        db.query(PaperHolding)
        .filter(PaperHolding.user_id == user.id, PaperHolding.symbol == symbol)
        .first()
    )


def _reject(
    db: Session, user: User, symbol: str, side: str, quantity: int, price: Optional[float], reason: str
) -> PaperOrder:
    order = PaperOrder(
        user_id=user.id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        status="REJECTED",
        rejection_reason=reason,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def place_buy_order(db: Session, user: User, symbol: str, quantity: int) -> PaperOrder:
    stock = stock_service.get_stock_by_symbol(db, symbol)
    if stock is None:
        raise ValueError(f"Stock '{symbol}' not found")

    price, price_status = stock_service.resolve_current_price(stock)
    if price is None:
        return _reject(
            db, user, stock.symbol, "BUY", quantity, None,
            "Market price is currently unavailable; cannot execute a paper order without a real price.",
        )

    account = get_or_create_account(db, user)
    cost = round(price * quantity, 2)

    if cost > account.balance:
        return _reject(
            db, user, stock.symbol, "BUY", quantity, price,
            f"Insufficient paper balance: order costs ₹{cost:,.2f} but balance is ₹{account.balance:,.2f}.",
        )

    account.balance = round(account.balance - cost, 2)

    holding = _get_holding(db, user, stock.symbol)
    if holding is None:
        holding = PaperHolding(
            user_id=user.id, symbol=stock.symbol, quantity=quantity, avg_buy_price=price
        )
        db.add(holding)
    else:
        new_quantity = holding.quantity + quantity
        holding.avg_buy_price = round(
            (holding.quantity * holding.avg_buy_price + quantity * price) / new_quantity, 4
        )
        holding.quantity = new_quantity

    order = PaperOrder(
        user_id=user.id, symbol=stock.symbol, side="BUY", quantity=quantity, price=price, status="COMPLETE"
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def place_sell_order(db: Session, user: User, symbol: str, quantity: int) -> PaperOrder:
    stock = stock_service.get_stock_by_symbol(db, symbol)
    if stock is None:
        raise ValueError(f"Stock '{symbol}' not found")

    holding = _get_holding(db, user, stock.symbol)
    if holding is None or holding.quantity < quantity:
        held = holding.quantity if holding else 0
        return _reject(
            db, user, stock.symbol, "SELL", quantity, None,
            f"Insufficient paper holdings: you hold {held} share(s) of {stock.symbol}, "
            f"tried to sell {quantity}.",
        )

    price, price_status = stock_service.resolve_current_price(stock)
    if price is None:
        return _reject(
            db, user, stock.symbol, "SELL", quantity, None,
            "Market price is currently unavailable; cannot execute a paper order without a real price.",
        )

    account = get_or_create_account(db, user)
    proceeds = round(price * quantity, 2)
    account.balance = round(account.balance + proceeds, 2)

    holding.quantity -= quantity
    if holding.quantity == 0:
        db.delete(holding)

    order = PaperOrder(
        user_id=user.id, symbol=stock.symbol, side="SELL", quantity=quantity, price=price, status="COMPLETE"
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def list_orders(db: Session, user: User) -> List[PaperOrder]:
    return (
        db.query(PaperOrder).filter(PaperOrder.user_id == user.id).order_by(PaperOrder.created_at.desc()).all()
    )


def _build_holding_out(db: Session, holding: PaperHolding) -> dict:
    stock = db.query(Stock).filter(Stock.symbol == holding.symbol).first()
    current_price, price_status = stock_service.resolve_current_price(stock)

    invested_amount = round(holding.quantity * holding.avg_buy_price, 2)
    current_value = None
    pnl = None
    pnl_percent = None
    if current_price is not None:
        current_value = round(holding.quantity * current_price, 2)
        pnl = round(current_value - invested_amount, 2)
        pnl_percent = round((pnl / invested_amount) * 100, 2) if invested_amount else None

    return {
        "symbol": holding.symbol,
        "name": stock.name if stock else holding.symbol,
        "quantity": holding.quantity,
        "avg_buy_price": holding.avg_buy_price,
        "invested_amount": invested_amount,
        "current_price": current_price,
        "current_value": current_value,
        "pnl": pnl,
        "pnl_percent": pnl_percent,
        "price_status": price_status,
    }


def get_account_summary(db: Session, user: User) -> dict:
    account = get_or_create_account(db, user)
    holdings = db.query(PaperHolding).filter(PaperHolding.user_id == user.id).all()
    holdings_out = [_build_holding_out(db, h) for h in holdings]

    priced = [h for h in holdings_out if h["current_value"] is not None]
    all_priced = len(priced) == len(holdings_out)
    # Only report a total when every holding has a real price — otherwise
    # treating an unpriced holding as worth 0 would understate net worth
    # and silently misrepresent it, rather than honestly saying "unavailable".
    holdings_value = round(sum(h["current_value"] for h in priced), 2) if all_priced else None

    net_worth = round(account.balance + holdings_value, 2) if holdings_value is not None else None
    total_pnl = round(net_worth - STARTING_BALANCE, 2) if net_worth is not None else None
    total_pnl_percent = (
        round((total_pnl / STARTING_BALANCE) * 100, 2) if total_pnl is not None else None
    )

    return {
        "starting_balance": STARTING_BALANCE,
        "balance": account.balance,
        "holdings": holdings_out,
        "holdings_value": holdings_value,
        "net_worth": net_worth,
        "total_pnl": total_pnl,
        "total_pnl_percent": total_pnl_percent,
    }
