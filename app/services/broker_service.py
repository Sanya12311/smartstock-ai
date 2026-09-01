import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.brokers.dhan_broker import DhanBrokerError, DhanBroker
from app.models.broker_account import BrokerAccount
from app.models.user import User
from app.utils import encryption

logger = logging.getLogger(__name__)
broker = DhanBroker()


def start_connection(db: Session, user: User) -> BrokerAccount:
    """(Re)start a connection attempt, generating a fresh unique callback token."""
    account = db.query(BrokerAccount).filter(BrokerAccount.user_id == user.id).first()
    token = secrets.token_urlsafe(24)

    if account is None:
        account = BrokerAccount(user_id=user.id, connection_token=token, status="AWAITING_CREDENTIALS")
        db.add(account)
    else:
        account.connection_token = token
        account.status = "AWAITING_CREDENTIALS"
        account.dhan_client_id = None
        account.app_id_encrypted = None
        account.app_secret_encrypted = None
        account.consent_app_id = None
        account.access_token_encrypted = None
        account.token_expiry = None
        account.connected_at = None

    db.commit()
    db.refresh(account)
    return account


def submit_credentials(
    db: Session, user: User, connection_token: str, dhan_client_id: str, app_id: str, app_secret: str
) -> dict:
    account = (
        db.query(BrokerAccount)
        .filter(BrokerAccount.connection_token == connection_token, BrokerAccount.user_id == user.id)
        .first()
    )
    if account is None:
        raise ValueError("Broker connection not found. Start again with POST /broker/connect/start.")

    try:
        result = broker.generate_consent(app_id, app_secret, dhan_client_id)
    except DhanBrokerError as exc:
        account.status = "FAILED"
        db.commit()
        logger.warning("Broker consent generation failed for user_id=%s: %s", user.id, exc)
        raise

    account.dhan_client_id = dhan_client_id
    account.app_id_encrypted = encryption.encrypt(app_id)
    account.app_secret_encrypted = encryption.encrypt(app_secret)
    account.consent_app_id = result["consent_app_id"]
    account.status = "AWAITING_LOGIN"
    db.commit()

    return {"login_url": result["login_url"]}


def complete_connection(db: Session, connection_token: str, callback_params: dict) -> BrokerAccount:
    """Called from the raw browser redirect after the user approves on Dhan's site."""
    account = db.query(BrokerAccount).filter(BrokerAccount.connection_token == connection_token).first()
    if account is None or not account.app_id_encrypted or not account.app_secret_encrypted:
        raise ValueError("Broker connection not found or not yet initiated")

    app_id = encryption.decrypt(account.app_id_encrypted)
    app_secret = encryption.decrypt(account.app_secret_encrypted)

    try:
        result = broker.exchange_token(app_id, app_secret, callback_params)
    except DhanBrokerError as exc:
        account.status = "FAILED"
        db.commit()
        logger.warning("Broker token exchange failed for user_id=%s: %s", account.user_id, exc)
        raise

    account.access_token_encrypted = encryption.encrypt(result["access_token"])
    if result.get("expiry_time"):
        try:
            account.token_expiry = datetime.fromisoformat(result["expiry_time"])
        except ValueError:
            account.token_expiry = None
    account.status = "CONNECTED"
    account.connected_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(account)
    logger.info("Broker connected: user_id=%s broker=%s", account.user_id, account.broker_name)
    return account


def get_status(db: Session, user: User) -> Optional[BrokerAccount]:
    return db.query(BrokerAccount).filter(BrokerAccount.user_id == user.id).first()


def _get_connected_account(db: Session, user: User) -> BrokerAccount:
    account = db.query(BrokerAccount).filter(BrokerAccount.user_id == user.id).first()
    if account is None or account.status != "CONNECTED":
        raise ValueError("No connected broker account. Connect Dhan via /broker/connect/start first.")
    return account


def get_holdings(db: Session, user: User) -> list:
    account = _get_connected_account(db, user)
    access_token = encryption.decrypt(account.access_token_encrypted)
    return broker.get_holdings(access_token, account.dhan_client_id)


def get_funds(db: Session, user: User) -> dict:
    account = _get_connected_account(db, user)
    access_token = encryption.decrypt(account.access_token_encrypted)
    return broker.get_fund_limits(access_token, account.dhan_client_id)


def disconnect(db: Session, user: User) -> bool:
    account = db.query(BrokerAccount).filter(BrokerAccount.user_id == user.id).first()
    if account is None:
        return False
    db.delete(account)
    db.commit()
    logger.info("Broker disconnected: user_id=%s", user.id)
    return True
