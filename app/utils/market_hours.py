"""
Simplified NSE market-hours check: 9:15-15:30 IST, Monday-Friday.

Does NOT account for exchange holidays (Diwali, Republic Day, etc.) — a
real production system would need Dhan's holiday calendar or NSE's own.
Good enough to catch the common case (weekends, after-hours) before
attempting a real order that Dhan would reject anyway.
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


def is_market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return MARKET_OPEN <= now.time() <= MARKET_CLOSE
