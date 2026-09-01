"""
In-memory cache of the latest live tick per stock symbol.

Live ticks arrive far too fast to write to MySQL on every update, so we keep
only the latest value per symbol in memory here. Anything worth persisting
(e.g. completed trades, daily closes) is written to the database elsewhere,
not on every tick.
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Optional

_lock = threading.Lock()
_cache: Dict[str, dict] = {}


def update(symbol: str, tick: dict) -> dict:
    with _lock:
        entry = {**tick, "updated_at": datetime.now(timezone.utc).isoformat()}
        _cache[symbol] = entry
        return entry


def get(symbol: str) -> Optional[dict]:
    with _lock:
        return _cache.get(symbol)


def get_all() -> Dict[str, dict]:
    with _lock:
        return dict(_cache)
