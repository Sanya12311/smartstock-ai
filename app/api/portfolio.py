from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.portfolio import HoldingCreate, HoldingOut, PortfolioSummary
from app.services import portfolio_service

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("", response_model=PortfolioSummary)
def get_portfolio(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return portfolio_service.get_portfolio_summary(db, current_user)


@router.post("/holdings", response_model=HoldingOut, status_code=status.HTTP_201_CREATED)
def add_holding(
    holding_in: HoldingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        holding = portfolio_service.add_holding(
            db,
            current_user,
            holding_in.symbol,
            holding_in.quantity,
            holding_in.buy_price,
            holding_in.buy_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return portfolio_service.build_holding_out(db, holding)


@router.delete("/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holding(
    holding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = portfolio_service.delete_holding(db, current_user, holding_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")
