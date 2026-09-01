from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.stock import Stock
from app.services import market_cache
from app.services.dhan_client import DhanAPIError, get_full_quote


def search_stocks(db: Session, query: str, limit: int = 10) -> List[Stock]:
    pattern = f"%{query.upper()}%"
    return (
        db.query(Stock)
        .filter(Stock.is_active.is_(True))
        .filter((Stock.symbol.ilike(pattern)) | (Stock.name.ilike(pattern)))
        .limit(limit)
        .all()
    )


def get_stock_by_symbol(db: Session, symbol: str) -> Optional[Stock]:
    return db.query(Stock).filter(Stock.symbol == symbol.upper()).first()


def build_stock_quote(stock: Stock) -> dict:
    raw = get_full_quote(stock.exchange_segment, stock.security_id)

    ohlc = raw.get("ohlc", {})
    last_price = raw.get("last_price")
    # Dhan's "ohlc.close" is the prior session's close, used as the
    # reference price for computing change / change percent.
    previous_close = ohlc.get("close")
    net_change = raw.get("net_change")

    change_percent = None
    if net_change is not None and previous_close:
        change_percent = round((net_change / previous_close) * 100, 2)

    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "last_price": last_price,
        "open": ohlc.get("open"),
        "high": ohlc.get("high"),
        "low": ohlc.get("low"),
        "previous_close": previous_close,
        "volume": raw.get("volume"),
        "change": net_change,
        "change_percent": change_percent,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


def resolve_current_price(stock: Stock) -> Tuple[Optional[float], str]:
    """Prefer the live WebSocket cache (Phase 5); fall back to a REST quote (Phase 4)."""
    cached = market_cache.get(stock.symbol)
    if cached and cached.get("last_price") is not None:
        return cached["last_price"], "live"

    try:
        quote = build_stock_quote(stock)
    except DhanAPIError:
        return None, "unavailable"

    last_price = quote.get("last_price")
    if last_price is None:
        return None, "unavailable"
    return last_price, "live"
