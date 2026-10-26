"""Cache-aside reads for council pages and lists.

Redis is optional. A missing library, a refused connection, or a timed-out
command is logged and ignored. Callers then use Postgres or the in-memory
fallback. This module never stores passwords, session tokens, audit rows,
phone numbers, email addresses, or upload bytes.

On a dedicated Redis, the ceiling is 48GB (REDIS_MAXMEMORY) with allkeys-lru
only as a safety net. That ceiling is not reserved up front. Set
REDIS_MAXMEMORY=off on a small machine. Local Redis:

    docker run --name kofc-redis -p 6379:6379 redis:7
"""

from __future__ import annotations

import json
import logging
import threading
import time

from config import redis_maxmemory, redis_maxmemory_policy, redis_url
from titles import DIRECTOR_ROLE_ABBREVS, OFFICER_ROLE_ABBREVS

log = logging.getLogger("koc10930.cache")

TTL_STABLE = 6 * 60 * 60
TTL_DOCUMENTS = 60 * 60
TTL_FRESH = 10 * 60
_RETRY_SECONDS = 30

PAGE_PUBLIC = "kofc:page:public"
PAGE_MEMBER = "kofc:page:member"
SETTINGS_YEAR = "kofc:settings:year"
SETTINGS_SITE = "kofc:settings:site"
MEMBERS = "kofc:members:list"
OFFICERS = "kofc:officers:current"
DIRECTORS = "kofc:directors:current"
EVENTS = "kofc:events:upcoming"
ANNOUNCEMENTS = "kofc:announcements:list"
PRAYERS = "kofc:prayers:list"
NOMINATIONS = "kofc:nominations:tallies"
DOC_TREASURER = "kofc:documents:treasurer"
DOC_FINANCIAL_SECRETARY = "kofc:documents:financial_secretary"
YEAR_BLOCK = "year.fraternal"

# Past honors, one key per group. "other" keeps an unexpected category from
# disappearing if the five known groups are all present.
HONOR_KEYS = (
    ("knight_month", "kofc:honors:kotm"),
    ("family_month", "kofc:honors:fotm"),
    ("knight_year", "kofc:honors:koty"),
    ("family_year", "kofc:honors:foty"),
    ("past_gk", "kofc:honors:pgk"),
    ("", "kofc:honors:other"),
)

_lock = threading.Lock()
_client = None
_down_until = 0.0
_configured = False


def _mark_down(exc: Exception) -> None:
    global _client, _down_until
    with _lock:
        _client = None
        _down_until = time.monotonic() + _RETRY_SECONDS
    log.warning("Redis cache skipped (%s). Reading from the database.", exc.__class__.__name__)


def _apply_memory(client) -> None:
    size = redis_maxmemory()
    if not size or size.lower() in {"0", "off", "none"}:
        return
    policy = redis_maxmemory_policy()
    try:
        client.config_set("maxmemory", size)
        client.config_set("maxmemory-policy", policy)
    except Exception as exc:
        log.warning("Could not set Redis memory limits (%s).", exc.__class__.__name__)


def _client_or_none():
    global _client, _configured, _down_until
    now = time.monotonic()
    with _lock:
        if now < _down_until:
            return None
        if _client is not None:
            return _client
        url = redis_url()
        if not url:
            return None
        try:
            import redis

            client = redis.Redis.from_url(
                url,
                socket_connect_timeout=0.3,
                socket_timeout=0.5,
                decode_responses=True,
                health_check_interval=30,
            )
            client.ping()
        except Exception as exc:
            _client = None
            _down_until = time.monotonic() + _RETRY_SECONDS
            log.warning("Redis is unavailable (%s). Reading from the database.", exc.__class__.__name__)
            return None
        if not _configured:
            _apply_memory(client)
            _configured = True
        _client = client
        return client


def _unwrap(raw):
    if raw is None:
        return None
    try:
        envelope = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(envelope, dict) or "data" not in envelope:
        return None
    return envelope["data"]


def get_json(key: str):
    client = _client_or_none()
    if client is None:
        return None
    try:
        return _unwrap(client.get(key))
    except Exception as exc:
        _mark_down(exc)
        return None


def set_json(key: str, value, ttl: int) -> None:
    client = _client_or_none()
    if client is None:
        return
    try:
        client.set(key, json.dumps({"data": value}, default=str), ex=ttl)
    except Exception as exc:
        _mark_down(exc)


def drop(*keys: str) -> None:
    names = [key for key in keys if key]
    if not names:
        return
    client = _client_or_none()
    if client is None:
        return
    try:
        client.delete(*names)
    except Exception as exc:
        _mark_down(exc)


def page_key(slug: str) -> str:
    if slug == "public":
        return PAGE_PUBLIC
    if slug == "member":
        return PAGE_MEMBER
    return f"kofc:page:{slug}"


def document_key(library: str) -> str:
    if library == "treasurer":
        return DOC_TREASURER
    if library == "financial_secretary":
        return DOC_FINANCIAL_SECRETARY
    return f"kofc:documents:{library}"


def store_page(slug: str, payload: dict) -> None:
    set_json(page_key(slug), payload, TTL_STABLE)
    if slug != "member":
        return
    year = ""
    for block in payload.get("blocks") or []:
        if isinstance(block, dict) and block.get("key") == YEAR_BLOCK:
            year = block.get("value") or ""
            break
    set_json(SETTINGS_YEAR, year, TTL_STABLE)
    set_json(SETTINGS_SITE, {YEAR_BLOCK: year}, TTL_STABLE)


def drop_page(slug: str) -> None:
    keys = [page_key(slug)]
    if slug == "member":
        keys.extend([SETTINGS_YEAR, SETTINGS_SITE])
    drop(*keys)


def _roles(members: list, abbrevs: tuple[str, ...]) -> list[dict]:
    found = {}
    allowed = set(abbrevs)
    for member in members:
        if not isinstance(member, dict):
            continue
        title = member.get("title")
        if title in allowed and title not in found:
            found[title] = {
                "title": title,
                "memberid": member.get("memberid"),
                "display_name": member.get("display_name"),
                "photo_url": member.get("photo_url"),
            }
    return [found[title] for title in abbrevs if title in found]


def store_roster(members: list) -> None:
    """Public member fields only. Phone, email, and password hashes stay out."""
    set_json(MEMBERS, members, TTL_STABLE)
    set_json(OFFICERS, _roles(members, OFFICER_ROLE_ABBREVS), TTL_STABLE)
    set_json(DIRECTORS, _roles(members, DIRECTOR_ROLE_ABBREVS), TTL_STABLE)


def drop_members() -> None:
    drop(MEMBERS, OFFICERS, DIRECTORS)


def get_honors():
    client = _client_or_none()
    if client is None:
        return None
    try:
        raws = client.mget([key for _, key in HONOR_KEYS])
    except Exception as exc:
        _mark_down(exc)
        return None
    if not raws or any(item is None for item in raws):
        return None
    rows = []
    for raw in raws:
        group = _unwrap(raw)
        if not isinstance(group, list):
            return None
        rows.extend(group)
    return rows


def store_honors(rows: list) -> None:
    grouped = {category: [] for category, _key in HONOR_KEYS}
    for row in rows:
        category = row.get("category") if isinstance(row, dict) else None
        if category not in grouped:
            category = ""
        grouped[category].append(row)
    client = _client_or_none()
    if client is None:
        return
    try:
        pipe = client.pipeline()
        for category, key in HONOR_KEYS:
            pipe.set(key, json.dumps({"data": grouped[category]}, default=str), ex=TTL_STABLE)
        pipe.execute()
    except Exception as exc:
        _mark_down(exc)


def drop_honors() -> None:
    drop(*(key for _category, key in HONOR_KEYS))


def drop_documents(library: str | None = None) -> None:
    if library:
        drop(document_key(library))
        return
    drop(DOC_TREASURER, DOC_FINANCIAL_SECRETARY)


def drop_events() -> None:
    drop(EVENTS)


def drop_announcements() -> None:
    drop(ANNOUNCEMENTS)


def drop_prayers() -> None:
    drop(PRAYERS)


def drop_nominations() -> None:
    drop(NOMINATIONS)
