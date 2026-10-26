"""Password hashing and signed session tokens.

Access tokens last 15 minutes. Refresh tokens last 7 days and are rotated.
The browser stores both in httpOnly cookies. A bearer access token is also
accepted so non-browser clients can call protected routes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt
from fastapi import Request

from config import cookie_secure, jwt_secret, using_dev_secret

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
ACCESS_MINUTES = 15
REFRESH_DAYS = 7
_ALGORITHM = "HS256"

# Checked when the membership id is unknown so missing users take about as
# long as a real password comparison.
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt(rounds=12))


class TokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        hashed = password_hash.encode("ascii")
    except Exception:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed)
    except Exception:
        return False


def verify_password_dummy(password: str) -> None:
    try:
        bcrypt.checkpw(password.encode("utf-8"), _DUMMY_HASH)
    except Exception:
        return


def _encode(payload: dict) -> str:
    token = jwt.encode(payload, jwt_secret(), algorithm=_ALGORITHM)
    if isinstance(token, bytes):
        return token.decode("ascii")
    return token


def create_access_token(memberid: str) -> str:
    now = datetime.now(timezone.utc)
    return _encode(
        {
            "sub": memberid,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=ACCESS_MINUTES),
        }
    )


def create_refresh_token(memberid: str) -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    token_id = uuid4().hex
    expires = now + timedelta(days=REFRESH_DAYS)
    token = _encode(
        {
            "sub": memberid,
            "type": "refresh",
            "jti": token_id,
            "iat": now,
            "exp": expires,
        }
    )
    return token, token_id, expires


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, jwt_secret(), algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise TokenError("Not authenticated") from exc


def access_from_request(request: Request) -> str | None:
    token = request.cookies.get(ACCESS_COOKIE)
    if token:
        return token
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        bearer = header[7:].strip()
        if bearer:
            return bearer
    return None
