"""
Deterministic alert evaluation engine.

Runs periodically (see app/alerts/scheduler.py), not on every price tick —
RSI/MACD alerts need a technical analysis call (which hits Dhan's
historical-data endpoint), and doing that on every tick for every symbol
with an active alert would risk hammering Dhan's rate limit. Instead we
batch: one technical analysis fetch per symbol per evaluation cycle, shared
across every alert on that symbol regardless of how many users have one.

Deduplication: a cooldown window prevents the same alert from re-firing
every cycle while its condition stays true. MACD_CROSS additionally tracks
`last_state` so it only fires on an actual sign change, not a rechecked
existing state.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.notification import Notification
from app.models.portfolio_holding import PortfolioHolding
from app.models.stock import Stock
from app.services import analysis_service, stock_service
from app.services.dhan_client import DhanAPIError

COOLDOWN = timedelta(hours=1)

PRICE_ALERT_TYPES = {"PRICE_ABOVE", "PRICE_BELOW"}
PNL_ALERT_TYPES = {"PROFIT_PERCENT", "LOSS_PERCENT"}
TECHNICAL_ALERT_TYPES = {"RSI_OVERBOUGHT", "RSI_OVERSOLD", "MACD_CROSS"}


def _get_current_price(stock: Stock) -> Optional[float]:
    price, _status = stock_service.resolve_current_price(stock)
    return price


def _in_cooldown(alert: Alert) -> bool:
    if alert.last_triggered_at is None:
        return False
    last = alert.last_triggered_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last < COOLDOWN


def _create_notification(
    db: Session, alert: Alert, title: str, message: str, category: str
) -> Notification:
    notification = Notification(
        user_id=alert.user_id,
        alert_id=alert.id,
        symbol=alert.symbol,
        title=title,
        message=message,
        category=category,
    )
    db.add(notification)
    alert.last_triggered_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification)
    return notification


def _check_price_alert(
    db: Session, alert: Alert, stock: Stock, price: Optional[float]
) -> Optional[Notification]:
    if price is None:
        return None
    if alert.alert_type == "PRICE_ABOVE" and price >= alert.threshold:
        return _create_notification(
            db,
            alert,
            f"{stock.symbol} crossed ₹{alert.threshold:,.2f}",
            f"{stock.symbol} is now at ₹{price:,.2f}, above your alert level of ₹{alert.threshold:,.2f}.",
            "PRICE",
        )
    if alert.alert_type == "PRICE_BELOW" and price <= alert.threshold:
        return _create_notification(
            db,
            alert,
            f"{stock.symbol} fell below ₹{alert.threshold:,.2f}",
            f"{stock.symbol} is now at ₹{price:,.2f}, below your alert level of ₹{alert.threshold:,.2f}.",
            "PRICE",
        )
    return None


def _check_pnl_alert(
    db: Session, alert: Alert, stock: Stock, price: Optional[float]
) -> Optional[Notification]:
    if price is None:
        return None

    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.user_id == alert.user_id, PortfolioHolding.symbol == alert.symbol)
        .all()
    )
    for holding in holdings:
        if holding.buy_price <= 0:
            continue
        pnl_percent = ((price - holding.buy_price) / holding.buy_price) * 100

        if alert.alert_type == "PROFIT_PERCENT" and pnl_percent >= alert.threshold:
            return _create_notification(
                db,
                alert,
                f"{stock.symbol} reached +{alert.threshold:.1f}% profit",
                f"Your {stock.symbol} holding is up {pnl_percent:.1f}%, past your target of "
                f"+{alert.threshold:.1f}%.",
                "PROFIT",
            )
        if alert.alert_type == "LOSS_PERCENT" and pnl_percent <= -alert.threshold:
            return _create_notification(
                db,
                alert,
                f"{stock.symbol} fell below -{alert.threshold:.1f}%",
                f"Your {stock.symbol} holding is down {pnl_percent:.1f}%, past your loss limit of "
                f"-{alert.threshold:.1f}%.",
                "LOSS",
            )
    return None


def _check_technical_alert(
    db: Session, alert: Alert, stock: Stock, analysis: Optional[dict]
) -> Optional[Notification]:
    if analysis is None:
        return None
    indicators = analysis["indicators"]

    if alert.alert_type == "RSI_OVERBOUGHT":
        rsi = indicators.get("rsi_14")
        if rsi is not None and rsi >= alert.threshold:
            return _create_notification(
                db,
                alert,
                f"{stock.symbol} RSI overbought",
                f"{stock.symbol}'s RSI is {rsi:.1f}, at or above your overbought level of "
                f"{alert.threshold:.0f}.",
                "TECHNICAL",
            )
        return None

    if alert.alert_type == "RSI_OVERSOLD":
        rsi = indicators.get("rsi_14")
        if rsi is not None and rsi <= alert.threshold:
            return _create_notification(
                db,
                alert,
                f"{stock.symbol} RSI oversold",
                f"{stock.symbol}'s RSI is {rsi:.1f}, at or below your oversold level of "
                f"{alert.threshold:.0f}.",
                "TECHNICAL",
            )
        return None

    if alert.alert_type == "MACD_CROSS":
        macd = indicators.get("macd")
        if macd is None:
            return None
        current_state = "bullish" if macd["histogram"] > 0 else "bearish"
        previous_state = alert.last_state
        alert.last_state = current_state
        db.commit()
        if previous_state is not None and previous_state != current_state:
            return _create_notification(
                db,
                alert,
                f"{stock.symbol} MACD {current_state} crossover",
                f"{stock.symbol}'s MACD just turned {current_state} (histogram {macd['histogram']:.2f}).",
                "TECHNICAL",
            )
        return None

    return None


def evaluate_all_alerts(db: Session) -> List[dict]:
    alerts = db.query(Alert).filter(Alert.is_active.is_(True)).all()
    if not alerts:
        return []

    alerts_by_symbol: Dict[str, List[Alert]] = {}
    for alert in alerts:
        alerts_by_symbol.setdefault(alert.symbol, []).append(alert)

    triggered: List[dict] = []

    for symbol, symbol_alerts in alerts_by_symbol.items():
        stock = db.query(Stock).filter(Stock.symbol == symbol).first()
        if stock is None:
            continue

        price = _get_current_price(stock)

        needs_technical = any(a.alert_type in TECHNICAL_ALERT_TYPES for a in symbol_alerts)
        analysis = None
        if needs_technical:
            try:
                analysis = analysis_service.build_technical_analysis(stock)
            except DhanAPIError:
                analysis = None

        for alert in symbol_alerts:
            if _in_cooldown(alert):
                continue

            notification = None
            if alert.alert_type in PRICE_ALERT_TYPES:
                notification = _check_price_alert(db, alert, stock, price)
            elif alert.alert_type in PNL_ALERT_TYPES:
                notification = _check_pnl_alert(db, alert, stock, price)
            elif alert.alert_type in TECHNICAL_ALERT_TYPES:
                notification = _check_technical_alert(db, alert, stock, analysis)

            if notification is not None:
                triggered.append(
                    {
                        "id": notification.id,
                        "user_id": notification.user_id,
                        "symbol": notification.symbol,
                        "title": notification.title,
                        "message": notification.message,
                        "category": notification.category,
                        "created_at": notification.created_at.isoformat(),
                    }
                )

    return triggered
