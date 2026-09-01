from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services import dhan_feed, market_cache
from app.utils.security import decode_access_token
from app.websocket.connection_manager import manager

router = APIRouter(tags=["Market Data"])


@router.get("/market/status")
def market_status(current_user: User = Depends(get_current_user)):
    return dhan_feed.get_status()


@router.get("/market/live")
def market_live(current_user: User = Depends(get_current_user)):
    """Snapshot of the latest cached tick per symbol (REST fallback / debugging)."""
    return market_cache.get_all()


def _authenticate_ws_token(db: Session, token: str) -> bool:
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        return False
    user = db.query(User).filter(User.email == payload["sub"]).first()
    return user is not None


@router.websocket("/ws/market")
async def ws_market(websocket: WebSocket, token: str = Query(...), db: Session = Depends(get_db)):
    if not _authenticate_ws_token(db, token):
        await websocket.close(code=1008)  # policy violation
        return

    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "snapshot", "data": market_cache.get_all()})
        while True:
            # We don't expect messages from the client; this just keeps the
            # connection open and detects disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
