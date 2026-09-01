from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy.sql import func

from app.database import Base

STARTING_BALANCE = 1_000_000.0  # ₹10,00,000 virtual balance


class PaperAccount(Base):
    __tablename__ = "paper_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    balance = Column(Float, nullable=False, default=STARTING_BALANCE)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
