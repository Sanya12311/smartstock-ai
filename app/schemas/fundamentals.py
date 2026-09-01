from typing import Optional

from pydantic import BaseModel


class FundamentalData(BaseModel):
    symbol: str
    data_available: bool
    note: str
    source: Optional[str] = None
    as_of: Optional[str] = None

    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    eps: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    revenue_growth_percent: Optional[float] = None
    profit_growth_percent: Optional[float] = None
    dividend_yield_percent: Optional[float] = None
    market_cap: Optional[float] = None
