"""
Background service that connects to DhanHQ's Live Market Feed (WebSocket v2),
subscribes to every active stock in our `stocks` table in Quote mode, keeps
an in-memory cache of the latest tick per symbol, and pushes updates to any
connected /ws/market clients.

Protocol verified directly against the official DhanHQ-py SDK source
(https://github.com/dhan-oss/DhanHQ-py/blob/main/src/dhanhq/marketfeed.py),
August 2026:
  - Connect: wss://api-feed.dhan.co?version=2&token=...&clientId=...&authType=2
  - Subscribe: JSON {"RequestCode": 17, "InstrumentList": [...]} (17 = Quote mode)
  - Automatic reconnection and the background thread are handled by the SDK's
    MarketFeed.start(), so we don't reimplement that here.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple

from dhanhq import DhanContext, MarketFeed

from app.config import settings
from app.database import SessionLocal
from app.models.stock import Stock
from app.services import market_cache
from app.websocket.connection_manager import manager

logger = logging.getLogger(__name__)

_feed: Optional[MarketFeed] = None
_security_id_to_symbol: Dict[str, str] = {}
_main_loop: Optional[asyncio.AbstractEventLoop] = None
_status = {"connected": False, "reason": "not started", "subscribed_symbols": []}


def get_status() -> dict:
    return dict(_status)


_SEGMENT_TO_EXCHANGE_CODE = {
    "IDX_I": MarketFeed.IDX,
    "NSE_EQ": MarketFeed.NSE,
    "NSE_FNO": MarketFeed.NSE_FNO,
    "BSE_EQ": MarketFeed.BSE,
}


def _load_instruments() -> List[Tuple[int, str, int]]:
    db = SessionLocal()
    try:
        stocks = db.query(Stock).filter(Stock.is_active.is_(True)).all()
        instruments = []
        for stock in stocks:
            _security_id_to_symbol[stock.security_id] = stock.symbol
            exchange_code = _SEGMENT_TO_EXCHANGE_CODE.get(stock.exchange_segment, MarketFeed.NSE)
            instruments.append((exchange_code, stock.security_id, MarketFeed.Quote))
        return instruments
    finally:
        db.close()


def _on_connect(instance):
    _status.update(connected=True, reason="connected")
    logger.info("Connected to DhanHQ live market feed")


def _on_close(instance):
    _status.update(connected=False, reason="closed")
    logger.warning("DhanHQ live market feed connection closed")


def _on_error(instance, error):
    _status.update(connected=False, reason=str(error))
    logger.error("DhanHQ live market feed error: %s", error)


def _on_message(instance, data):
    if not isinstance(data, dict) or data.get("type") != "Quote Data":
        return

    symbol = _security_id_to_symbol.get(str(data.get("security_id")))
    if symbol is None:
        return

    tick = {
        "symbol": symbol,
        "last_price": float(data["LTP"]),
        "open": float(data["open"]),
        "high": float(data["high"]),
        "low": float(data["low"]),
        "previous_close": float(data["close"]),
        "volume": data["volume"],
    }
    entry = market_cache.update(symbol, tick)

    if _main_loop is not None:
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": "tick", "data": entry}), _main_loop
        )


def start() -> None:
    """Start the DhanHQ live feed in a background thread, if credentials exist.

    Must be called from within a running asyncio event loop (e.g. FastAPI's
    lifespan startup), so broadcasts from the feed's own thread can be handed
    back to that loop safely.
    """
    global _feed, _main_loop

    if not settings.DHAN_CLIENT_ID or not settings.DHAN_ACCESS_TOKEN:
        _status.update(connected=False, reason="Dhan credentials not configured")
        logger.warning("Skipping live market feed: DHAN_CLIENT_ID/DHAN_ACCESS_TOKEN not set")
        return

    instruments = _load_instruments()
    if not instruments:
        _status.update(connected=False, reason="No active stocks to subscribe to")
        return

    _main_loop = asyncio.get_running_loop()
    _status["subscribed_symbols"] = sorted(_security_id_to_symbol.values())

    dhan_context = DhanContext(settings.DHAN_CLIENT_ID, settings.DHAN_ACCESS_TOKEN)
    _feed = MarketFeed(
        dhan_context,
        instruments,
        version="v2",
        on_connect=_on_connect,
        on_message=_on_message,
        on_close=_on_close,
        on_error=_on_error,
    )
    _feed.start()


def stop() -> None:
    if _feed is not None:
        _feed.close_connection()
