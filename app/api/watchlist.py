from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.watchlist import WatchlistAddRequest, WatchlistItemOut
from app.services import watchlist_service

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


@router.get("", response_model=List[WatchlistItemOut])
def get_watchlist(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return watchlist_service.list_watchlist(db, current_user)


@router.post("", status_code=status.HTTP_201_CREATED)
def add_watchlist_item(
    payload: WatchlistAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        watchlist_service.add_to_watchlist(db, current_user, payload.symbol)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def remove_watchlist_item(
    symbol: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    removed = watchlist_service.remove_from_watchlist(db, current_user, symbol)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist item not found")
