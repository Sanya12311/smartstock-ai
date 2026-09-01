import csv
import io
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import Response
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


@router.get("/trades/export/csv")
def export_trades_csv(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Raw transaction export (date/symbol/side/qty/price/status) for the
    user's own records or a CA/tax preparer — deliberately NOT a computed
    capital-gains/tax report, since accurate FIFO cost-basis matching and
    tax treatment is a professional accounting matter outside this app's
    decision-support scope (see the app-wide "not financial advice" rule).
    """
    trades = order_service.list_trades(db, current_user)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["Trade ID", "Broker", "Symbol", "Side", "Quantity", "Order Type", "Price", "Status", "Executed At (UTC)"]
    )
    for trade in trades:
        writer.writerow(
            [
                trade.id,
                trade.broker_name,
                trade.symbol,
                trade.side,
                trade.quantity,
                trade.order_type,
                trade.price if trade.price is not None else "",
                trade.status,
                trade.updated_at.isoformat() if trade.updated_at else "",
            ]
        )

    filename = f"smartstock_trades_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
