"""
Central logging setup. Without this, every `logging.getLogger(__name__)`
call elsewhere in the app (market feed, schedulers, etc.) is silently
dropped — Python's root logger defaults to WARNING with no handler, so
.info()/.warning() calls never actually appear anywhere.

Rule: NEVER log passwords, JWTs, API keys, or broker secrets. Request
logging below deliberately logs only method/path/status/duration/user —
never headers or bodies, which is where those secrets would live.
"""

import logging

from app.config import settings

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging() -> None:
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(level=level, format=LOG_FORMAT)

    # Quiet down noisy third-party loggers so ours aren't drowned out.
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
