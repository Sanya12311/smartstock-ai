from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: Optional[str] = None
    title: str
    message: str
    category: str
    is_read: bool
    created_at: datetime
