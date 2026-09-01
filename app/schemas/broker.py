from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BrokerConnectionStart(BaseModel):
    connection_token: str
    redirect_uri_to_register: str
    instructions: str


class BrokerCredentials(BaseModel):
    connection_token: str
    dhan_client_id: str = Field(min_length=1, max_length=32)
    app_id: str = Field(min_length=1)
    app_secret: str = Field(min_length=1)


class BrokerLoginUrl(BaseModel):
    login_url: str


class BrokerStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    broker_name: str
    status: str
    dhan_client_id: Optional[str] = None
    connected_at: Optional[datetime] = None


class BrokerHoldingOut(BaseModel):
    exchange: Optional[str] = None
    trading_symbol: Optional[str] = None
    security_id: Optional[str] = None
    isin: Optional[str] = None
    total_qty: Optional[float] = None
    dp_qty: Optional[float] = None
    t1_qty: Optional[float] = None
    available_qty: Optional[float] = None
    collateral_qty: Optional[float] = None
    avg_cost_price: Optional[float] = None


class BrokerFundsOut(BaseModel):
    available_balance: Optional[float] = None
    sod_limit: Optional[float] = None
    collateral_amount: Optional[float] = None
    receivable_amount: Optional[float] = None
    utilized_amount: Optional[float] = None
    blocked_payout_amount: Optional[float] = None
    withdrawable_balance: Optional[float] = None
