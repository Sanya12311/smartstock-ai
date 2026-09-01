from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALERT_TYPES_NEEDING_THRESHOLD = {
    "PRICE_ABOVE",
    "PRICE_BELOW",
    "PROFIT_PERCENT",
    "LOSS_PERCENT",
    "RSI_OVERBOUGHT",
    "RSI_OVERSOLD",
}
VALID_ALERT_TYPES = ALERT_TYPES_NEEDING_THRESHOLD | {"MACD_CROSS"}


class AlertCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    alert_type: str
    # validate_default=True: without it, Pydantic v2 skips this field's
    # validator entirely when the client omits threshold and the default
    # (None) is used — which would silently let required-threshold alert
    # types through with no threshold at all.
    threshold: Optional[float] = Field(default=None, validate_default=True)

    @field_validator("alert_type")
    @classmethod
    def validate_alert_type(cls, v: str) -> str:
        if v not in VALID_ALERT_TYPES:
            raise ValueError(f"alert_type must be one of {sorted(VALID_ALERT_TYPES)}")
        return v

    @field_validator("threshold")
    @classmethod
    def validate_threshold(cls, v, info):
        alert_type = info.data.get("alert_type")
        if alert_type in ALERT_TYPES_NEEDING_THRESHOLD and v is None:
            raise ValueError(f"threshold is required for alert_type '{alert_type}'")
        return v


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    alert_type: str
    threshold: Optional[float] = None
    is_active: bool
    last_triggered_at: Optional[datetime] = None
    created_at: datetime
