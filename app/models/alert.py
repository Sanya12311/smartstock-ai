from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(32), ForeignKey("stocks.symbol"), nullable=False, index=True)
    # PRICE_ABOVE, PRICE_BELOW, PROFIT_PERCENT, LOSS_PERCENT,
    # RSI_OVERBOUGHT, RSI_OVERSOLD, MACD_CROSS
    alert_type = Column(String(32), nullable=False)
    threshold = Column(Float, nullable=True)  # not used by MACD_CROSS
    is_active = Column(Boolean, default=True, nullable=False)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)  # for cooldown
    last_state = Column(String(16), nullable=True)  # for crossover detection (MACD_CROSS)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
