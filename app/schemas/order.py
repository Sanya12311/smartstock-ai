from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrderPreviewRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    side: str
    quantity: int = Field(gt=0)
    order_type: str
    price: Optional[float] = Field(default=None, validate_default=True)

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        if v not in ("BUY", "SELL"):
            raise ValueError("side must be 'BUY' or 'SELL'")
        return v

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        if v not in ("MARKET", "LIMIT"):
            raise ValueError("order_type must be 'MARKET' or 'LIMIT'")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v, info):
        if info.data.get("order_type") == "LIMIT" and (v is None or v <= 0):
            raise ValueError("price is required and must be positive for LIMIT orders")
        return v


class OrderPreviewOut(BaseModel):
    symbol: str
    name: str
    side: str
    quantity: int
    order_type: str
    price: Optional[float] = None
    current_market_price: Optional[float] = None
    price_status: str
    estimated_value: Optional[float] = None
    market_open: bool


class OrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    quantity: int = Field(gt=0)
    order_type: str
    price: Optional[float] = Field(default=None, validate_default=True)

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        if v not in ("MARKET", "LIMIT"):
            raise ValueError("order_type must be 'MARKET' or 'LIMIT'")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v, info):
        if info.data.get("order_type") == "LIMIT" and (v is None or v <= 0):
            raise ValueError("price is required and must be positive for LIMIT orders")
        return v


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    broker_name: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    price: Optional[float] = None
    broker_order_id: Optional[str] = None
    status: str
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
