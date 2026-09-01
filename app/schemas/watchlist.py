from typing import Optional

from pydantic import BaseModel, Field


class WatchlistAddRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)


class WatchlistItemOut(BaseModel):
    symbol: str
    name: str
    last_price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    price_status: str
