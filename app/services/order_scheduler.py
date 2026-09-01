import asyncio
import logging
from typing import Optional

from app.database import SessionLocal
from app.services import order_service
from app.websocket.connection_manager import notification_manager

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 30

_task: Optional[asyncio.Task] = None
_running = False


def _run_once() -> list:
    db = SessionLocal()
    try:
        return order_service.refresh_all_pending_orders(db)
    finally:
        db.close()


async def _loop() -> None:
    while _running:
        try:
            notifications = await asyncio.to_thread(_run_once)
            for note in notifications:
                await notification_manager.send_to_user(note["user_id"], note)
        except Exception:
            logger.exception("Order status refresh cycle failed")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def start() -> None:
    global _task, _running
    _running = True
    _task = asyncio.get_running_loop().create_task(_loop())


def stop() -> None:
    global _running
    _running = False
    if _task is not None:
        _task.cancel()
