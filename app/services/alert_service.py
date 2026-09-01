from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.user import User
from app.services import stock_service


def create_alert(
    db: Session, user: User, symbol: str, alert_type: str, threshold: Optional[float]
) -> Alert:
    stock = stock_service.get_stock_by_symbol(db, symbol)
    if stock is None:
        raise ValueError(f"Stock '{symbol}' not found")

    alert = Alert(user_id=user.id, symbol=stock.symbol, alert_type=alert_type, threshold=threshold)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def list_alerts(db: Session, user: User) -> List[Alert]:
    return db.query(Alert).filter(Alert.user_id == user.id).order_by(Alert.created_at.desc()).all()


def delete_alert(db: Session, user: User, alert_id: int) -> bool:
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == user.id).first()
    if alert is None:
        return False
    db.delete(alert)
    db.commit()
    return True
