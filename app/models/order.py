from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Order(Base):
    """
    Real orders placed against a user's connected broker (Phase 14).
    A "trade" is just an order that reached TRADED/PART_TRADED — no
    separate trades table, to avoid duplicating the same data.
    """

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_name = Column(String(32), nullable=False, default="DHAN")
    symbol = Column(String(32), ForeignKey("stocks.symbol"), nullable=False, index=True)
    side = Column(String(4), nullable=False)  # BUY / SELL
    quantity = Column(Integer, nullable=False)
    order_type = Column(String(16), nullable=False)  # MARKET / LIMIT
    price = Column(Float, nullable=True)  # only meaningful for LIMIT
    broker_order_id = Column(String(64), nullable=True, index=True)
    # Real Dhan statuses, shown as-is rather than remapped: TRANSIT, PENDING,
    # REJECTED, CANCELLED, PART_TRADED, TRADED, EXPIRED.
    status = Column(String(32), nullable=False, default="PENDING")
    rejection_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
