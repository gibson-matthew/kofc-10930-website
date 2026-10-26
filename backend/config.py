"""Environment configuration for the API.

Other modules import these helpers. They do not read os.environ themselves.
A missing optional service (Redis, mail) leaves its value empty and the app
keeps the existing fallback. This module never logs secret values.

Local files, from the repo root, loaded only when a variable is not already
set in the process environment:

    .env.local
    .env
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
_LOCAL_JWT = ROOT / ".local" / "jwt_secret"

_jwt_value: str | None = None
_jwt_ephemeral = False


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    load_dotenv(ROOT / ".env.local")
    load_dotenv(ROOT / ".env")


_load_env()


def _raw(name: str) -> str:
    return os.environ.get(name, "").strip()


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def database_url() -> str:
    """Postgres URL, or an empty string when no account is configured."""
    explicit = _raw("DATABASE_URL")
    if explicit:
        return explicit
    user = _raw("POSTGRES_USER")
    if not user:
        return ""
    password = os.environ.get("POSTGRES_PASSWORD", "")
    host = _raw("POSTGRES_HOST") or "localhost"
    port = _raw("POSTGRES_PORT") or "5432"
    name = _raw("POSTGRES_DB") or "koc10930"
    if not port.isdigit():
        port = "5432"
    return (
        f"postgresql://{quote(user, safe='')}:{quote(password, safe='')}"
        f"@{host}:{port}/{quote(name, safe='')}"
    )


def redis_url() -> str:
    """Redis URL. Empty disables the cache. Unset uses the local default."""
    raw = os.environ.get("REDIS_URL")
    if raw is None or not str(raw).strip():
        return "redis://localhost:6379/0"
    value = str(raw).strip()
    if value.lower() in {"off", "none", "disabled"}:
        return ""
    return value


def redis_maxmemory() -> str:
    return os.environ.get("REDIS_MAXMEMORY", "48gb").strip()


def redis_maxmemory_policy() -> str:
    return os.environ.get("REDIS_MAXMEMORY_POLICY", "allkeys-lru").strip() or "allkeys-lru"


def jwt_secret() -> str:
    """Signing key. JWT_SECRET wins. Otherwise a gitignored local file is used."""
    global _jwt_value, _jwt_ephemeral
    if _jwt_value:
        return _jwt_value
    configured = _raw("JWT_SECRET")
    if configured:
        _jwt_value = configured
        return _jwt_value
    try:
        if _LOCAL_JWT.is_file():
            stored = _LOCAL_JWT.read_text(encoding="utf-8").strip()
            if len(stored) >= 16:
                _jwt_value = stored
                return stored
        _LOCAL_JWT.parent.mkdir(parents=True, exist_ok=True)
        stored = secrets.token_urlsafe(48)
        _LOCAL_JWT.write_text(stored + "\n", encoding="utf-8")
        _jwt_value = stored
        return stored
    except Exception:
        _jwt_ephemeral = True
        _jwt_value = secrets.token_urlsafe(48)
        return _jwt_value


def using_dev_secret() -> bool:
    return not _raw("JWT_SECRET")


def dev_secret_is_ephemeral() -> bool:
    jwt_secret()
    return _jwt_ephemeral


def cookie_secure() -> bool:
    return _flag("COOKIE_SECURE", False)


def cookie_samesite() -> str:
    raw = _raw("COOKIE_SAMESITE").lower() or "lax"
    if raw not in {"lax", "strict", "none"}:
        return "lax"
    return raw


def cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS")
    if raw is None or not str(raw).strip():
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def cors_origin_regex() -> str | None:
    raw = os.environ.get("CORS_ORIGIN_REGEX")
    if raw is None or not str(raw).strip():
        return r"http://(localhost|127\.0\.0\.1):517\d"
    value = str(raw).strip()
    if value.lower() in {"off", "none", "0"}:
        return None
    return value


def upload_dir() -> Path:
    raw = _raw("UPLOAD_DIR")
    if not raw:
        return (BACKEND_DIR / "uploads").resolve()
    path = Path(raw)
    if not path.is_absolute():
        return (ROOT / path).resolve()
    return path.resolve()


def mail_enabled() -> bool:
    return _flag("MAIL_ENABLED", False)


def cloudflare_account_id() -> str:
    return _raw("CLOUDFLARE_ACCOUNT_ID")


def cloudflare_email_token() -> str:
    return os.environ.get("CLOUDFLARE_EMAIL_TOKEN", "").strip()


def mail_from() -> str:
    return _raw("MAIL_FROM")


def mail_officer_to() -> str:
    return _raw("MAIL_OFFICER_TO")
