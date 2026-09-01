from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.order import OrderOut, OrderPreviewOut, OrderPreviewRequest, OrderRequest
from app.services import order_service
from app.services.order_service import OrderValidationError

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/preview", response_model=OrderPreviewOut)
def preview_order(
    payload: OrderPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return order_service.preview_order(
            db, current_user, payload.symbol, payload.side, payload.quantity, payload.order_type, payload.price
        )
    except OrderValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/buy", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def buy_order(
    payload: OrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return order_service.place_buy_order(
            db, current_user, payload.symbol, payload.quantity, payload.order_type, payload.price
        )
    except OrderValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/sell", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def sell_order(
    payload: OrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return order_service.place_sell_order(
            db, current_user, payload.symbol, payload.quantity, payload.order_type, payload.price
        )
    except OrderValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=List[OrderOut])
def get_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    symbol: Optional[str] = Query(None),
    side: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return order_service.list_orders(db, current_user, status_filter, symbol, side)


@router.get("/{order_id}", response_model=OrderOut)
def get_order_detail(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return order_service.get_order(db, current_user, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{order_id}/refresh", response_model=OrderOut)
def refresh_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pulls the latest status from Dhan on demand. Not in the master API list —
    added because there's no postback/webhook integration yet, so we need
    some way to see PENDING orders move to TRADED/REJECTED/etc.
    """
    try:
        return order_service.refresh_order_status(db, current_user, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a still-pending order via the broker. Not in the master API
    list either, but a real gap: we already track a CANCELLED status
    without ever having a way to actually trigger it.
    """
    try:
        return order_service.cancel_order(db, current_user, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except OrderValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
