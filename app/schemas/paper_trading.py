from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PaperOrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    quantity: int = Field(gt=0)


class PaperOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    side: str
    quantity: int
    price: Optional[float] = None
    status: str
    rejection_reason: Optional[str] = None
    created_at: datetime


class PaperHoldingOut(BaseModel):
    symbol: str
    name: str
    quantity: int
    avg_buy_price: float
    invested_amount: float
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    price_status: str


class PaperAccountSummary(BaseModel):
    starting_balance: float
    balance: float
    holdings: List[PaperHoldingOut]
    holdings_value: Optional[float] = None
    net_worth: Optional[float] = None
    total_pnl: Optional[float] = None
    total_pnl_percent: Optional[float] = None
