from typing import List

from sqlalchemy.orm import Session

from app.models.stock import Stock
from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.services import market_cache, stock_service
from app.services.dhan_client import DhanAPIError


def add_to_watchlist(db: Session, user: User, symbol: str) -> WatchlistItem:
    stock = stock_service.get_stock_by_symbol(db, symbol)
    if stock is None:
        raise ValueError(f"Stock '{symbol}' not found")

    existing = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.id, WatchlistItem.symbol == stock.symbol)
        .first()
    )
    if existing is not None:
        return existing

    item = WatchlistItem(user_id=user.id, symbol=stock.symbol)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def remove_from_watchlist(db: Session, user: User, symbol: str) -> bool:
    item = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.id, WatchlistItem.symbol == symbol.upper())
        .first()
    )
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def _build_watchlist_item(stock: Stock) -> dict:
    cached = market_cache.get(stock.symbol)
    if cached and cached.get("last_price") is not None:
        last_price = cached["last_price"]
        previous_close = cached.get("previous_close")
        change = None
        change_percent = None
        if previous_close:
            change = round(last_price - previous_close, 2)
            change_percent = round((change / previous_close) * 100, 2)
        return {
            "symbol": stock.symbol,
            "name": stock.name,
            "last_price": last_price,
            "change": change,
            "change_percent": change_percent,
            "price_status": "live",
        }

    try:
        quote = stock_service.build_stock_quote(stock)
    except DhanAPIError:
        quote = {}

    last_price = quote.get("last_price")
    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "last_price": last_price,
        "change": quote.get("change"),
        "change_percent": quote.get("change_percent"),
        "price_status": "live" if last_price is not None else "unavailable",
    }


def list_watchlist(db: Session, user: User) -> List[dict]:
    items = db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).order_by(WatchlistItem.created_at).all()
    stocks_by_symbol = {s.symbol: s for s in db.query(Stock).filter(Stock.symbol.in_([i.symbol for i in items])).all()}
    return [_build_watchlist_item(stocks_by_symbol[i.symbol]) for i in items if i.symbol in stocks_by_symbol]
