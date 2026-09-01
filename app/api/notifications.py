from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.notification import NotificationOut
from app.services import notification_service
from app.utils.security import decode_access_token
from app.websocket.connection_manager import notification_manager

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", response_model=List[NotificationOut])
def get_notifications(
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return notification_service.list_notifications(db, current_user, unread_only)


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    marked = notification_service.mark_as_read(db, current_user, notification_id)
    if not marked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")


def _authenticate_ws_token(db: Session, token: str) -> Optional[int]:
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        return None
    user = db.query(User).filter(User.email == payload["sub"]).first()
    return user.id if user else None


@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket, token: str = Query(...), db: Session = Depends(get_db)):
    user_id = _authenticate_ws_token(db, token)
    if user_id is None:
        await websocket.close(code=1008)
        return

    await notification_manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await notification_manager.disconnect(websocket, user_id)
