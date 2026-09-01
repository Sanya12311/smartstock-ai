from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.paper_trading import PaperAccountSummary, PaperOrderOut, PaperOrderRequest
from app.services import paper_trading_service

router = APIRouter(prefix="/paper", tags=["Paper Trading"])


@router.get("/account", response_model=PaperAccountSummary)
def get_paper_account(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return paper_trading_service.get_account_summary(db, current_user)


@router.post("/orders/buy", response_model=PaperOrderOut, status_code=status.HTTP_201_CREATED)
def buy_paper_order(
    payload: PaperOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return paper_trading_service.place_buy_order(db, current_user, payload.symbol, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/orders/sell", response_model=PaperOrderOut, status_code=status.HTTP_201_CREATED)
def sell_paper_order(
    payload: PaperOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return paper_trading_service.place_sell_order(db, current_user, payload.symbol, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/orders", response_model=List[PaperOrderOut])
def get_paper_orders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return paper_trading_service.list_orders(db, current_user)
