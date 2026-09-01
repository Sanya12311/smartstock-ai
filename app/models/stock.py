from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    # Dhan groups instruments by exchange+segment, e.g. "NSE_EQ"
    exchange_segment = Column(String(16), nullable=False, default="NSE_EQ")
    # Dhan's internal numeric instrument id (not the trading symbol)
    security_id = Column(String(32), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
