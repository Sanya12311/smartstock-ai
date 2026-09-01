from typing import List

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User


def list_notifications(db: Session, user: User, unread_only: bool = False) -> List[Notification]:
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.order_by(Notification.created_at.desc()).all()


def mark_as_read(db: Session, user: User, notification_id: int) -> bool:
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user.id)
        .first()
    )
    if notification is None:
        return False
    notification.is_read = True
    db.commit()
    return True
