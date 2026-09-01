"""
Symmetric encryption for broker credentials at rest (app_id, app_secret,
access tokens). Never store these in plain text — a database leak would
otherwise directly expose live trading credentials.

Uses a separate key from SECRET_KEY (JWT signing) deliberately: different
purposes should use different keys, so rotating one never affects the other.
"""

from cryptography.fernet import Fernet

from app.config import settings


def _get_fernet() -> Fernet:
    if not settings.BROKER_ENCRYPTION_KEY:
        raise RuntimeError(
            "BROKER_ENCRYPTION_KEY is not configured. Set it in .env (see Phase 14 setup)."
        )
    return Fernet(settings.BROKER_ENCRYPTION_KEY.encode())


def encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return _get_fernet().decrypt(token.encode()).decode()
