from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class HoldingCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    quantity: int = Field(gt=0)
    buy_price: float = Field(gt=0)
    buy_date: date


class HoldingOut(BaseModel):
    id: int
    symbol: str
    name: str
    quantity: int
    buy_price: float
    buy_date: date
    invested_amount: float
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    price_status: str
    created_at: datetime


class AllocationItem(BaseModel):
    symbol: str
    percent: float


class PortfolioRisk(BaseModel):
    risk_level: str
    reasons: List[str]


class PortfolioSummary(BaseModel):
    total_invested: float
    total_current_value: Optional[float] = None
    total_pnl: Optional[float] = None
    total_pnl_percent: Optional[float] = None
    prices_partial: bool
    holdings: List[HoldingOut]
    allocation: List[AllocationItem]
    risk: PortfolioRisk
