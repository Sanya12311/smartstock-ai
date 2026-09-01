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
