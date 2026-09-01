from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.order import OrderOut
from app.services import order_service

router = APIRouter(tags=["Orders"])


@router.get("/trades", response_model=List[OrderOut])
def get_trades(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return order_service.list_trades(db, current_user)
