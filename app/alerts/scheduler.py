import asyncio
import logging
from typing import Optional

from app.alerts.engine import evaluate_all_alerts
from app.database import SessionLocal
from app.websocket.connection_manager import notification_manager

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60

_task: Optional[asyncio.Task] = None
_running = False


def _run_once() -> list:
    db = SessionLocal()
    try:
        return evaluate_all_alerts(db)
    finally:
        db.close()


async def _loop() -> None:
    while _running:
        try:
            notifications = await asyncio.to_thread(_run_once)
            for note in notifications:
                await notification_manager.send_to_user(note["user_id"], note)
        except Exception:
            logger.exception("Alert evaluation cycle failed")
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
