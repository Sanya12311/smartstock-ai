"""
TOTP (RFC 6238) two-factor auth — compatible with Google Authenticator,
Authy, etc. via the standard otpauth:// provisioning URI.
"""

import base64
import io

import pyotp
import qrcode

ISSUER_NAME = "SmartStock AI"


def generate_secret() -> str:
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=ISSUER_NAME)


def verify_code(secret: str, code: str) -> bool:
    # valid_window=1 tolerates one 30s step of clock drift on either side —
    # standard practice for TOTP so a slightly-off phone clock isn't locked out.
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def generate_qr_code_base64(provisioning_uri: str) -> str:
    img = qrcode.make(provisioning_uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()
