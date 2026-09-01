from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    AccountDeleteRequest,
    LoginResponse,
    PasswordChangeRequest,
    Token,
    TwoFactorCodeRequest,
    TwoFactorDisableRequest,
    TwoFactorLoginRequest,
    TwoFactorSetupOut,
    UserCreate,
    UserOut,
)
from app.utils import encryption, totp
from app.utils.rate_limit import rate_limiter
from app.utils.security import (
    create_access_token,
    create_pre_auth_token,
    decode_pre_auth_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limiter(max_requests=5, window_seconds=60))],
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(rate_limiter(max_requests=5, window_seconds=60))],
)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.totp_enabled:
        return LoginResponse(requires_2fa=True, pre_auth_token=create_pre_auth_token(user.email))

    return LoginResponse(access_token=create_access_token(data={"sub": user.email}))


@router.post(
    "/2fa/verify-login",
    response_model=Token,
    dependencies=[Depends(rate_limiter(max_requests=5, window_seconds=60))],
)
def verify_login_2fa(payload: TwoFactorLoginRequest, db: Session = Depends(get_db)):
    email = decode_pre_auth_token(payload.pre_auth_token)
    if email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login session expired, please sign in again")

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.totp_enabled or not user.totp_secret_encrypted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login session expired, please sign in again")

    secret = encryption.decrypt(user.totp_secret_encrypted)
    if not totp.verify_code(secret, payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authenticator code")

    return Token(access_token=create_access_token(data={"sub": user.email}))


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Logout successful. Discard the access token on the client side."}


@router.post(
    "/change-password",
    dependencies=[Depends(rate_limiter(max_requests=5, window_seconds=60))],
)
def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        # 400, not 401: a 401 anywhere is treated app-wide (see api.js) as an
        # expired/invalid token and force-logs the user out, which is wrong
        # for "you typed your current password wrong" while still signed in.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully."}


@router.post(
    "/delete-account",
    dependencies=[Depends(rate_limiter(max_requests=5, window_seconds=60))],
)
def delete_account(
    payload: AccountDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Irreversibly deletes the user's account and everything owned by it.
    Every user-owned table (orders, portfolio, paper trading, broker
    connection, alerts, notifications, chat history, watchlist) has an
    ondelete='CASCADE' foreign key to users.id at the database level (see
    migrations/versions/aa16fe1a1e46_initial_schema.py), so deleting the
    User row is sufficient — MySQL/InnoDB cascades the rest.
    """
    if not verify_password(payload.password, current_user.hashed_password):
        # 400, not 401 — see change_password's comment above.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect")

    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted."}


@router.post(
    "/2fa/setup",
    response_model=TwoFactorSetupOut,
    dependencies=[Depends(rate_limiter(max_requests=5, window_seconds=60))],
)
def setup_2fa(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Generates a new secret and stores it (encrypted) but does NOT enable
    2FA yet — POST /auth/2fa/enable must confirm the user actually scanned
    it correctly first. Calling this again before enabling just replaces
    the pending secret (e.g. the user re-scans after an error).
    """
    if current_user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Two-factor authentication is already enabled")

    secret = totp.generate_secret()
    current_user.totp_secret_encrypted = encryption.encrypt(secret)
    db.commit()

    uri = totp.get_provisioning_uri(secret, current_user.email)
    return TwoFactorSetupOut(secret=secret, provisioning_uri=uri, qr_code_base64=totp.generate_qr_code_base64(uri))


@router.post(
    "/2fa/enable",
    dependencies=[Depends(rate_limiter(max_requests=5, window_seconds=60))],
)
def enable_2fa(
    payload: TwoFactorCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Two-factor authentication is already enabled")
    if not current_user.totp_secret_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Call /auth/2fa/setup first")

    secret = encryption.decrypt(current_user.totp_secret_encrypted)
    if not totp.verify_code(secret, payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authenticator code")

    current_user.totp_enabled = True
    db.commit()
    return {"message": "Two-factor authentication enabled."}


@router.post(
    "/2fa/disable",
    dependencies=[Depends(rate_limiter(max_requests=5, window_seconds=60))],
)
def disable_2fa(
    payload: TwoFactorDisableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect")

    current_user.totp_enabled = False
    current_user.totp_secret_encrypted = None
    db.commit()
    return {"message": "Two-factor authentication disabled."}
