from datetime import date

from sqlalchemy.orm import Session

from app.models.portfolio_holding import PortfolioHolding
from app.models.stock import Stock
from app.models.user import User
from app.services import stock_service


def add_holding(
    db: Session, user: User, symbol: str, quantity: int, buy_price: float, buy_date_: date
) -> PortfolioHolding:
    stock = stock_service.get_stock_by_symbol(db, symbol)
    if stock is None:
        raise ValueError(f"Stock '{symbol}' not found")

    holding = PortfolioHolding(
        user_id=user.id,
        symbol=stock.symbol,
        quantity=quantity,
        buy_price=buy_price,
        buy_date=buy_date_,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


def delete_holding(db: Session, user: User, holding_id: int) -> bool:
    holding = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.id == holding_id, PortfolioHolding.user_id == user.id)
        .first()
    )
    if holding is None:
        return False
    db.delete(holding)
    db.commit()
    return True


def build_holding_out(db: Session, holding: PortfolioHolding) -> dict:
    stock = db.query(Stock).filter(Stock.symbol == holding.symbol).first()
    current_price, price_status = stock_service.resolve_current_price(stock)

    invested_amount = round(holding.quantity * holding.buy_price, 2)
    current_value = None
    pnl = None
    pnl_percent = None
    if current_price is not None:
        current_value = round(holding.quantity * current_price, 2)
        pnl = round(current_value - invested_amount, 2)
        pnl_percent = round((pnl / invested_amount) * 100, 2) if invested_amount else None

    return {
        "id": holding.id,
        "symbol": holding.symbol,
        "name": stock.name if stock else holding.symbol,
        "quantity": holding.quantity,
        "buy_price": holding.buy_price,
        "buy_date": holding.buy_date,
        "invested_amount": invested_amount,
        "current_price": current_price,
        "current_value": current_value,
        "pnl": pnl,
        "pnl_percent": pnl_percent,
        "price_status": price_status,
        "created_at": holding.created_at,
    }


def _assess_portfolio_risk(allocation: list, holdings_count: int) -> dict:
    """
    Concentration risk based on per-stock allocation. We don't have sector
    data yet, so this measures concentration in a single stock rather than
    a single sector — the practical version of this rule given what data
    we actually have right now.
    """
    if not allocation:
        return {
            "risk_level": "unavailable",
            "reasons": ["No live prices available yet to assess portfolio concentration."],
        }

    reasons = []
    top = max(allocation, key=lambda a: a["percent"])

    if top["percent"] >= 50:
        level = "HIGH"
        reasons.append(
            f"{top['symbol']} makes up {top['percent']:.1f}% of your portfolio's current value, "
            "which is a high concentration in a single stock."
        )
    elif top["percent"] >= 30:
        level = "MEDIUM"
        reasons.append(
            f"{top['symbol']} makes up {top['percent']:.1f}% of your portfolio's current value, "
            "which increases concentration risk."
        )
    else:
        level = "LOW"

    if holdings_count == 1:
        reasons.append("Your portfolio holds only one stock, so it is not diversified.")
        if level == "LOW":
            level = "MEDIUM"

    if not reasons:
        reasons.append("No significant concentration risk detected across your holdings.")

    return {"risk_level": level, "reasons": reasons}


def get_portfolio_summary(db: Session, user: User) -> dict:
    holdings = db.query(PortfolioHolding).filter(PortfolioHolding.user_id == user.id).all()
    holdings_out = [build_holding_out(db, h) for h in holdings]

    total_invested = round(sum(h["invested_amount"] for h in holdings_out), 2)
    priced = [h for h in holdings_out if h["current_value"] is not None]
    prices_partial = len(priced) != len(holdings_out)

    if not holdings_out:
        # A genuinely empty portfolio has a known value: zero. This is
        # different from "priced is empty because prices are unavailable" —
        # that case (handled below) correctly stays None/unknown instead.
        return {
            "total_invested": 0.0,
            "total_current_value": 0.0,
            "total_pnl": 0.0,
            "total_pnl_percent": None,
            "prices_partial": False,
            "holdings": [],
            "allocation": [],
            "risk": {"risk_level": "unavailable", "reasons": ["No holdings yet."]},
        }

    total_current_value = None
    total_pnl = None
    total_pnl_percent = None
    allocation = []

    if priced:
        total_current_value = round(sum(h["current_value"] for h in priced), 2)
        invested_of_priced = round(sum(h["invested_amount"] for h in priced), 2)
        total_pnl = round(total_current_value - invested_of_priced, 2)
        total_pnl_percent = (
            round((total_pnl / invested_of_priced) * 100, 2) if invested_of_priced else None
        )
        if total_current_value:
            allocation = [
                {
                    "symbol": h["symbol"],
                    "percent": round((h["current_value"] / total_current_value) * 100, 2),
                }
                for h in priced
            ]

    return {
        "total_invested": total_invested,
        "total_current_value": total_current_value,
        "total_pnl": total_pnl,
        "total_pnl_percent": total_pnl_percent,
        "prices_partial": prices_partial,
        "holdings": holdings_out,
        "allocation": allocation,
        "risk": _assess_portfolio_risk(allocation, len(holdings_out)),
    }
