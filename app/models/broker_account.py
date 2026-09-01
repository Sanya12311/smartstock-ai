from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class BrokerAccount(Base):
    __tablename__ = "broker_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    broker_name = Column(String(32), nullable=False, default="DHAN")
    # Unique per-user path segment registered as the user's Dhan app's
    # Redirect URL, so we can identify which user a callback belongs to.
    connection_token = Column(String(64), nullable=False, unique=True, index=True)

    dhan_client_id = Column(String(32), nullable=True)
    app_id_encrypted = Column(Text, nullable=True)
    app_secret_encrypted = Column(Text, nullable=True)
    consent_app_id = Column(String(128), nullable=True)

    access_token_encrypted = Column(Text, nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)

    # AWAITING_CREDENTIALS -> AWAITING_LOGIN -> CONNECTED / FAILED
    status = Column(String(32), nullable=False, default="AWAITING_CREDENTIALS")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    connected_at = Column(DateTime(timezone=True), nullable=True)
