from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    # bcrypt silently ignores bytes beyond 72, so we cap password length here
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    totp_enabled: bool
    created_at: datetime


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=72)


class AccountDeleteRequest(BaseModel):
    password: str = Field(min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """
    Either a normal full login (access_token set, requires_2fa False) or,
    for a 2FA-enabled account, a "second step needed" response carrying a
    short-lived pre_auth_token that POST /auth/2fa/verify-login exchanges
    for the real access_token once the TOTP code is confirmed.
    """

    access_token: Optional[str] = None
    token_type: str = "bearer"
    requires_2fa: bool = False
    pre_auth_token: Optional[str] = None


class TwoFactorSetupOut(BaseModel):
    secret: str
    provisioning_uri: str
    qr_code_base64: str


class TwoFactorCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class TwoFactorDisableRequest(BaseModel):
    password: str = Field(min_length=1)


class TwoFactorLoginRequest(BaseModel):
    pre_auth_token: str
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
