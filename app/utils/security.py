from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app.config import settings


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Every caller that trusts this for real session/authorization purposes
    (get_current_user, the WebSocket auth in market.py/notifications.py,
    main.py's request-logging identify) relies on it rejecting anything
    that isn't a normal full session token — so a short-lived, single-purpose
    token (like the 2FA pre-auth token below) can never be replayed as a
    real session just because it's a validly-signed JWT.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") is not None:
        return None
    return payload


def create_pre_auth_token(email: str) -> str:
    """
    Issued after email+password succeed for a 2FA-enabled account, before
    the TOTP code is verified. Deliberately short-lived and carries a
    'purpose' claim so decode_access_token() above always rejects it —
    it is only ever accepted by decode_pre_auth_token(), used solely by
    POST /auth/2fa/verify-login.
    """
    return create_access_token(data={"sub": email, "purpose": "2fa_pending"}, expires_delta=timedelta(minutes=5))


def decode_pre_auth_token(token: str) -> Optional[str]:
    """Returns the pending user's email if `token` is a valid, unexpired
    2FA pre-auth token; None otherwise (invalid, expired, or a normal
    session token — this deliberately does NOT accept those either)."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != "2fa_pending":
        return None
    return payload.get("sub")
