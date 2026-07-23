from datetime import datetime, timedelta
from typing import Optional, List

from jose import jwt, JWTError

from app.core.config import settings


# ============================================================
#  ACCESS TOKEN
# ============================================================

def create_access_token(
    user_id: int,
    membership_number: str,
    email: str,
    roles: List[str],
    expires_minutes: Optional[int] = None,
) -> str:
    """
    Create a signed JWT access token.
    """

    if expires_minutes is None:
        expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)

    payload = {
        "sub": str(user_id),
        "membership_number": membership_number,
        "email": email,
        "roles": roles,
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return token


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.
    Returns payload dict or None if invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


# ============================================================
#  PASSWORD RESET TOKEN
# ============================================================

RESET_TOKEN_EXPIRE_MINUTES = 30


def create_password_reset_token(user_id: int) -> str:
    """
    Create a short-lived password reset token.
    """
    expire = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "reset": True,
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return token


def verify_password_reset_token(token: str) -> Optional[int]:
    """
    Validate a password reset token.
    Returns user_id if valid, otherwise None.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        if payload.get("reset") is True:
            return int(payload.get("sub"))

        return None

    except JWTError:
        return None
