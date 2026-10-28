"""Privacy-aware audit log.

Necessary events are always stored. Accept-tier events are stored only when
the visitor has accepted optional tracking. A failed write never blocks the
request that triggered it. See TRACKING.md for the event list and the items
this site deliberately does not record.
"""

from __future__ import annotations

import json
import logging
import queue
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from config import database_url

log = logging.getLogger("koc10930.tracking")

CONSENT_COOKIE = "koc_consent"
CONSENT_VERSION = "1"
CONSENT_MAX_AGE = 365 * 24 * 60 * 60
FAILURE_WINDOW = timedelta(minutes=15)
FAILURE_THRESHOLD = 5
_MEMORY_LIMIT = 500
_QUEUE_LIMIT = 1000

_CLIENT_NECESSARY = {"error.frontend"}
_CLIENT_ACCEPT = {
    "page.view",
    "page.leave",
    "ui.click",
    "search.query",
    "search.use",
    "feature.use",
}
_DROP_KEYS = {"password", "token", "authorization", "cookie", "file_path", "path", "secret"}

_lock = threading.Lock()
_memory_events: list[dict] = []
_memory_consents: list[dict] = []
_jobs: queue.Queue = queue.Queue(maxsize=_QUEUE_LIMIT)
_hits: dict[str, list[float]] = {}


def _connect():
    url = database_url()
    if not url:
        return None
    try:
        import psycopg
    except ImportError:
        return None
    try:
        return psycopg.connect(url, connect_timeout=2)
    except Exception:
        return None


def ensure_audit_schema(cur) -> None:
    """Create the audit tables on an existing database. Failure stays local."""
    cur.execute("SAVEPOINT audit_schema")
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
              id BIGSERIAL PRIMARY KEY,
              event_type TEXT NOT NULL,
              tier TEXT NOT NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              membership_id TEXT,
              ip TEXT,
              user_agent TEXT,
              details JSONB NOT NULL DEFAULT '{}'::jsonb,
              CONSTRAINT audit_events_tier_chk CHECK (tier IN ('necessary', 'accept'))
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS audit_events_type_idx
            ON audit_events (event_type, created_at DESC)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS audit_events_member_idx
            ON audit_events (membership_id, created_at DESC)
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS consent_choices (
              id BIGSERIAL PRIMARY KEY,
              membership_id TEXT,
              choice TEXT NOT NULL,
              version TEXT NOT NULL,
              chosen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              ip TEXT,
              user_agent TEXT,
              CONSTRAINT consent_choices_choice_chk CHECK (choice IN ('accepted', 'declined'))
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS consent_choices_member_idx
            ON consent_choices (membership_id, chosen_at DESC)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS audit_events_created_idx
            ON audit_events (created_at DESC)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS consent_choices_chosen_idx
            ON consent_choices (chosen_at DESC)
            """
        )
        cur.execute("RELEASE SAVEPOINT audit_schema")
    except Exception as exc:
        log.warning("Could not prepare audit tables: %s", exc)
        cur.execute("ROLLBACK TO SAVEPOINT audit_schema")


def _worker() -> None:
    while True:
        job = _jobs.get()
        try:
            job()
        except Exception as exc:
            log.warning("Audit job failed: %s", exc)
        finally:
            _jobs.task_done()


threading.Thread(target=_worker, name="koc-audit", daemon=True).start()


def _enqueue(job) -> None:
    try:
        _jobs.put_nowait(job)
    except queue.Full:
        log.warning("Audit queue is full. Dropping one event.")


def _remember(event: dict) -> None:
    with _lock:
        _memory_events.append(event)
        if len(_memory_events) > _MEMORY_LIMIT:
            del _memory_events[: len(_memory_events) - _MEMORY_LIMIT]


def _insert_event(event: dict) -> bool:
    conn = _connect()
    if conn is None:
        _remember(event)
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_events
                  (event_type, tier, membership_id, ip, user_agent, details)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    event["event_type"],
                    event["tier"],
                    event.get("membership_id"),
                    event.get("ip"),
                    event.get("user_agent"),
                    json.dumps(event.get("details") or {}),
                ),
            )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        log.warning("Could not store audit event %s: %s", event.get("event_type"), exc)
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        _remember(event)
        return False


def client_ip(request) -> str:
    if request.client and request.client.host:
        return str(request.client.host)[:64]
    return ""


def summarize_user_agent(raw: str) -> str:
    ua = raw or ""
    browser = "Browser"
    if "Edg/" in ua:
        browser = "Edge"
    elif "Chrome/" in ua or "CriOS/" in ua:
        browser = "Chrome"
    elif "Firefox/" in ua or "FxiOS/" in ua:
        browser = "Firefox"
    elif "Safari/" in ua:
        browser = "Safari"
    system = "Unknown OS"
    if "Windows" in ua:
        system = "Windows"
    elif "Android" in ua:
        system = "Android"
    elif "iPhone" in ua or "iPad" in ua:
        system = "iOS"
    elif "Mac OS" in ua or "Macintosh" in ua:
        system = "macOS"
    elif "Linux" in ua:
        system = "Linux"
    return f"{browser} on {system}"[:120]


def _clean_details(value) -> dict:
    if not isinstance(value, dict):
        return {}
    cleaned: dict = {}
    for key, item in list(value.items())[:20]:
        name = str(key)[:40]
        if name.lower() in _DROP_KEYS:
            continue
        if isinstance(item, bool) or item is None:
            cleaned[name] = item
        elif isinstance(item, int) and not isinstance(item, bool):
            cleaned[name] = item
        elif isinstance(item, float):
            cleaned[name] = item
        elif isinstance(item, str):
            cleaned[name] = item.replace("\x00", "")[:300]
        elif isinstance(item, list):
            scalars = []
            for entry in item[:40]:
                if isinstance(entry, str):
                    scalars.append(entry.replace("\x00", "")[:120])
                elif isinstance(entry, (int, float)) and not isinstance(entry, bool):
                    scalars.append(entry)
                elif isinstance(entry, dict):
                    small = {}
                    for child_key, child in list(entry.items())[:6]:
                        child_name = str(child_key)[:40]
                        if child_name.lower() in _DROP_KEYS:
                            continue
                        if isinstance(child, str):
                            small[child_name] = child.replace("\x00", "")[:80]
                        elif isinstance(child, bool) or child is None or isinstance(child, (int, float)):
                            small[child_name] = child
                    if small:
                        scalars.append(small)
            cleaned[name] = scalars
    return cleaned


def _member_id_from_value(member_id) -> str | None:
    text = str(member_id or "").strip()
    return text[:32] or None


def _base_event(request, event_type: str, tier: str, member_id, details) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "event_type": event_type[:80],
        "tier": tier,
        "created_at": now,
        "membership_id": _member_id_from_value(member_id),
        "ip": client_ip(request) or None,
        "user_agent": summarize_user_agent(request.headers.get("user-agent", "")) or None,
        "details": _clean_details(details),
    }


def record(request, event_type: str, *, tier: str, member_id=None, details=None) -> None:
    """Queue one audit row. This function does not raise."""
    try:
        if tier not in {"necessary", "accept"}:
            return
        event = _base_event(request, event_type, tier, member_id, details)
        _enqueue(lambda event=event: _insert_event(event))
    except Exception as exc:
        log.warning("Could not queue audit event: %s", exc)


def record_accept(request, event_type: str, *, member_id=None, details=None, language: str = "", timezone_name: str = "") -> None:
    if consent_choice(request) != "accepted":
        return
    extra = _clean_details(details)
    if language:
        extra["language"] = str(language)[:40]
    elif request is not None:
        header = request.headers.get("accept-language", "")
        if header:
            extra["language"] = header.split(",")[0].strip()[:40]
    if timezone_name:
        extra["timezone"] = str(timezone_name)[:64]
    record(request, event_type, tier="accept", member_id=member_id, details=extra)


def consent_choice(request) -> str | None:
    raw = request.cookies.get(CONSENT_COOKIE, "")
    version, choice, stamp = (raw.split(".", 2) + ["", "", ""])[:3]
    if version != CONSENT_VERSION or choice not in {"accepted", "declined"} or not stamp.isdigit():
        return None
    return choice


def apply_consent_cookie(response, choice: str) -> None:
    from config import cookie_samesite, cookie_secure

    stamp = int(datetime.now(timezone.utc).timestamp())
    response.set_cookie(
        CONSENT_COOKIE,
        f"{CONSENT_VERSION}.{choice}.{stamp}",
        max_age=CONSENT_MAX_AGE,
        httponly=False,
        secure=cookie_secure(),
        samesite=cookie_samesite(),
        path="/",
    )


def _insert_consent(row: dict) -> None:
    conn = _connect()
    if conn is None:
        with _lock:
            _memory_consents.append(row)
            if len(_memory_consents) > _MEMORY_LIMIT:
                del _memory_consents[: len(_memory_consents) - _MEMORY_LIMIT]
        return
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO consent_choices
                  (membership_id, choice, version, ip, user_agent)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    row.get("membership_id"),
                    row["choice"],
                    row["version"],
                    row.get("ip"),
                    row.get("user_agent"),
                ),
            )
        conn.commit()
        conn.close()
    except Exception as exc:
        log.warning("Could not store consent choice: %s", exc)
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        with _lock:
            _memory_consents.append(row)


def save_consent(request, response, choice: str, member_id) -> None:
    """Remember Accept or Decline in the cookie, the database, and the audit log."""
    try:
        apply_consent_cookie(response, choice)
        row = {
            "membership_id": _member_id_from_value(member_id),
            "choice": choice,
            "version": CONSENT_VERSION,
            "chosen_at": datetime.now(timezone.utc),
            "ip": client_ip(request) or None,
            "user_agent": summarize_user_agent(request.headers.get("user-agent", "")) or None,
        }
        _enqueue(lambda row=row: _insert_consent(row))
        record(
            request,
            "consent.choice",
            tier="necessary",
            member_id=member_id,
            details={"choice": choice, "version": CONSENT_VERSION},
        )
    except Exception as exc:
        log.warning("Could not save consent: %s", exc)


def allow_client(ip: str, bucket: str, limit: int, window_seconds: int) -> bool:
    now = time.monotonic()
    key = f"{bucket}:{ip or 'unknown'}"
    with _lock:
        hits = [stamp for stamp in _hits.get(key, []) if now - stamp < window_seconds]
        if len(hits) >= limit:
            _hits[key] = hits
            return False
        hits.append(now)
        _hits[key] = hits
        return True


def _failure_counts(ip: str, attempted_id: str) -> tuple[int, int]:
    since = datetime.now(timezone.utc) - FAILURE_WINDOW
    conn = _connect()
    if conn is not None:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE ip = %s),
                      COUNT(*) FILTER (WHERE details->>'attempted_id' = %s)
                    FROM audit_events
                    WHERE event_type = 'auth.login_failure'
                      AND created_at > %s
                    """,
                    (ip or "", attempted_id, since),
                )
                row = cur.fetchone()
            conn.close()
            if row:
                return int(row[0] or 0), int(row[1] or 0)
        except Exception as exc:
            log.warning("Could not count login failures: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
    ip_count = 0
    id_count = 0
    with _lock:
        for event in _memory_events:
            if event.get("event_type") != "auth.login_failure":
                continue
            created = event.get("created_at")
            if not isinstance(created, datetime) or created < since:
                continue
            if ip and event.get("ip") == ip:
                ip_count += 1
            if event.get("details", {}).get("attempted_id") == attempted_id:
                id_count += 1
    return ip_count, id_count


def login_failure(request, attempted_id: str) -> None:
    attempted = str(attempted_id or "").strip()[:32]
    event = _base_event(
        request,
        "auth.login_failure",
        "necessary",
        None,
        {"attempted_id": attempted, "result": "failure"},
    )

    def work(event=event, attempted=attempted) -> None:
        _insert_event(event)
        ip_count, id_count = _failure_counts(event.get("ip") or "", attempted)
        if (ip_count >= FAILURE_THRESHOLD and ip_count % FAILURE_THRESHOLD == 0) or (
            id_count >= FAILURE_THRESHOLD and id_count % FAILURE_THRESHOLD == 0
        ):
            burst = dict(event)
            burst["event_type"] = "security.login_burst"
            burst["details"] = {
                "attempted_id": attempted,
                "ip_count": ip_count,
                "account_count": id_count,
                "window_minutes": 15,
                "threshold": FAILURE_THRESHOLD,
            }
            _insert_event(burst)

    _enqueue(work)


def login_success(request, member: dict) -> None:
    member_id = member.get("memberid")
    record(request, "auth.login_success", tier="necessary", member_id=member_id, details={"result": "success"})
    record(
        request,
        "session.start",
        tier="necessary",
        member_id=member_id,
        details={"session_id": uuid4().hex},
    )
    if member.get("is_admin") or member.get("is_webmaster"):
        record(request, "auth.admin_login", tier="necessary", member_id=member_id, details={"result": "success"})


def _latest_session_start(member_id: str):
    since = datetime.now(timezone.utc) - timedelta(days=8)
    conn = _connect()
    if conn is not None:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT created_at, details->>'session_id'
                    FROM audit_events
                    WHERE event_type = 'session.start'
                      AND membership_id = %s
                      AND created_at > %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (member_id, since),
                )
                row = cur.fetchone()
            conn.close()
            if row:
                return row[0], row[1]
        except Exception as exc:
            log.warning("Could not read session start: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
    with _lock:
        for event in reversed(_memory_events):
            created = event.get("created_at")
            if (
                event.get("event_type") == "session.start"
                and event.get("membership_id") == member_id
                and isinstance(created, datetime)
                and created > since
            ):
                return created, event.get("details", {}).get("session_id")
    return None, None


def logout(request, member_id) -> None:
    member_id = _member_id_from_value(member_id)
    end_event = _base_event(request, "session.end", "necessary", member_id, {})
    logout_event = _base_event(request, "auth.logout", "necessary", member_id, {"result": "success"})

    def work(end_event=end_event, logout_event=logout_event, member_id=member_id) -> None:
        started, session_id = _latest_session_start(member_id) if member_id else (None, None)
        details = {"session_id": session_id or ""}
        if isinstance(started, datetime):
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            details["duration_seconds"] = max(
                0,
                min(int((datetime.now(timezone.utc) - started).total_seconds()), 8 * 24 * 60 * 60),
            )
        end_event["details"] = details
        _insert_event(end_event)
        _insert_event(logout_event)

    _enqueue(work)


def admin_event(request, admin_id, action: str, content_type: str, record_id, **extra) -> None:
    if action not in {"create", "update", "delete"}:
        return
    details = {"content_type": content_type, "record_id": str(record_id), **extra}
    record(request, f"admin.content_{action}", tier="necessary", member_id=admin_id, details=details)


def content_diff(request, admin_id, before: dict | None, blocks: list[dict]) -> None:
    after = {}
    for block in blocks:
        key = str(block.get("key") or "")
        if key:
            after[key] = "" if block.get("value") is None else str(block.get("value"))
    if before is None:
        admin_event(request, admin_id, "update", "content_block", "member-page", snapshot="unavailable")
        return
    created = [key for key in after if key not in before]
    deleted = [key for key in before if key not in after]
    updated = [key for key in after if key in before and str(before.get(key)) != after[key]]
    if created:
        admin_event(request, admin_id, "create", "content_block", "member-page", keys=created[:40])
    if updated:
        admin_event(request, admin_id, "update", "content_block", "member-page", keys=updated[:40])
    if deleted:
        admin_event(request, admin_id, "delete", "content_block", "member-page", keys=deleted[:40])


def title_changes(request, admin_id, before_rows, after_rows) -> None:
    if before_rows is None or after_rows is None:
        admin_event(request, admin_id, "update", "officer_title", "assignments", snapshot="unavailable")
        return
    before = {row.get("memberid"): row.get("title") for row in before_rows}
    after = {row.get("memberid"): row.get("title") for row in after_rows}
    changes = []
    for member_id in sorted(set(before) | set(after), key=lambda value: str(value)):
        old = before.get(member_id)
        new = after.get(member_id)
        if old != new:
            changes.append({"record_id": str(member_id), "before": old or "", "after": new or ""})
    if not changes:
        return
    record(
        request,
        "admin.title_change",
        tier="necessary",
        member_id=admin_id,
        details={"content_type": "officer_title", "changes": changes[:40]},
    )


def flag_change(request, admin_id, target_id, before, after, flag: str = "is_admin") -> None:
    old = None if before is None else bool(before.get(flag))
    new = None if after is None else bool(after.get(flag))
    if before is not None and old == new:
        return
    if flag == "is_webmaster":
        content_type = "webmaster_flag"
    elif flag == "is_cloudflare":
        content_type = "cloudflare_flag"
    else:
        content_type = "admin_flag"
    record(
        request,
        "admin.flag_change",
        tier="necessary",
        member_id=admin_id,
        details={
            "content_type": content_type,
            "record_id": str(target_id),
            "before": old,
            "after": new,
        },
    )


def file_result(request, member_id, kind: str, result: str, *, content_type: str | None = None, size: int | None = None, record_id=None) -> None:
    details = {"kind": kind, "result": result}
    if content_type:
        details["content_type"] = str(content_type)[:80]
    if isinstance(size, int) and size >= 0:
        details["size"] = size
    if record_id is not None:
        details["record_id"] = str(record_id)
    event_type = "file.remove" if result == "removed" else "file.upload"
    record(request, event_type, tier="necessary", member_id=member_id, details=details)


def feature_use(request, member_id, feature: str, details=None) -> None:
    extra = {"feature": feature}
    extra.update(details or {})
    record_accept(request, "feature.use", member_id=member_id, details=extra)


def admin_denied(request, member_id) -> None:
    path = request.url.path[:120]
    record(
        request,
        "security.admin_denied",
        tier="necessary",
        member_id=member_id,
        details={"path": path, "result": "denied"},
    )


def backend_error(request, message: str, status_code: int = 500) -> None:
    member_id = None
    try:
        from auth.security import access_from_request, decode_token

        token = access_from_request(request)
        if token:
            payload = decode_token(token)
            if payload.get("type") == "access" and payload.get("sub"):
                member_id = str(payload["sub"])
    except Exception:
        member_id = None
    text = str(message or "error").replace("\n", " ")[:300]
    record(
        request,
        "error.backend",
        tier="necessary",
        member_id=member_id,
        details={"message": text, "status_code": int(status_code)},
    )


def _cap_page_details(event_type: str, details: dict) -> dict:
    if event_type == "page.leave":
        seconds = details.get("duration_seconds")
        if isinstance(seconds, (int, float)) and not isinstance(seconds, bool):
            details["duration_seconds"] = max(0, min(int(seconds), 86400))
        else:
            details.pop("duration_seconds", None)
    if event_type in {"page.view", "page.leave"}:
        path = details.get("path")
        if isinstance(path, str) and path.startswith("/") and "://" not in path:
            details["path"] = path[:120]
        else:
            details.pop("path", None)
    if event_type in {"search.query", "search.use"}:
        query = details.get("query")
        if isinstance(query, str):
            details["query"] = " ".join(query.split())[:120]
    return details


def ingest_client_events(request, member_id, events: list[dict], language: str = "", timezone_name: str = "") -> None:
    """Store browser events the server allowlist recognizes."""
    accepted = consent_choice(request) == "accepted"
    for item in events[:20]:
        if not isinstance(item, dict):
            continue
        event_type = str(item.get("type") or "")[:40]
        details = _cap_page_details(event_type, _clean_details(item.get("details")))
        if event_type in _CLIENT_NECESSARY:
            record(request, event_type, tier="necessary", member_id=member_id, details=details)
        elif event_type in _CLIENT_ACCEPT and accepted:
            record_accept(
                request,
                event_type,
                member_id=member_id,
                details=details,
                language=language,
                timezone_name=timezone_name,
            )


def _guard(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            log.warning("Tracking %s failed: %s", getattr(fn, "__name__", "call"), exc)
            return None

    return wrapper


for _fn_name in (
    "record",
    "record_accept",
    "consent_choice",
    "save_consent",
    "allow_client",
    "login_failure",
    "login_success",
    "logout",
    "admin_event",
    "content_diff",
    "title_changes",
    "flag_change",
    "file_result",
    "feature_use",
    "admin_denied",
    "backend_error",
    "ingest_client_events",
):
    globals()[_fn_name] = _guard(globals()[_fn_name])


def library_name(path: str) -> str:
    normalized = str(path or "").replace("\\", "/")
    if "/treasurer/" in normalized:
        return "treasurer"
    if "/financial-secretary/" in normalized:
        return "financial_secretary"
    return ""


_ROW_LIMIT = 200
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HIDDEN_DETAIL_KEYS = {"password", "password_hash", "token", "authorization", "cookie", "secret"}


def _unavailable() -> dict:
    return {"available": False, "truncated": False, "rows": [], "summary": None}


def _clip(value, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def _day(value: str) -> str | None:
    text = str(value or "").strip()[:10]
    if not _DATE_RE.match(text):
        return None
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None
    return text


def _like_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _iso(value) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    return ""


def _public_details(value) -> dict:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return {}
    if not isinstance(value, dict):
        return {}
    cleaned = {}
    for key, item in value.items():
        if str(key).lower() in _HIDDEN_DETAIL_KEYS:
            continue
        cleaned[str(key)] = item
    return cleaned


def _recover(cur) -> None:
    """A failed name lookup must not abandon the audit read."""
    connection = cur.connection
    if getattr(connection, "autocommit", False):
        return
    try:
        connection.rollback()
    except Exception:
        pass


def _member_ids_for(cur, text: str) -> list[str]:
    cleaned = _clip(text, 80)
    if not cleaned:
        return []
    try:
        cur.execute(
            """
            SELECT membership_id
            FROM members
            WHERE display_name ILIKE %s ESCAPE '\\'
            LIMIT 100
            """,
            (_like_pattern(cleaned),),
        )
        found = []
        for row in cur.fetchall():
            member_id = row.get("membership_id") if isinstance(row, dict) else row[0]
            if member_id:
                found.append(str(member_id))
        return found
    except Exception as exc:
        log.warning("Could not match member names for the activity log: %s", exc)
        _recover(cur)
        return []


def _names_for(cur, ids: list[str]) -> dict[str, str]:
    unique = list(dict.fromkeys(item for item in ids if item))
    if not unique:
        return {}
    marks = ", ".join(["%s"] * len(unique))
    try:
        cur.execute(
            f"SELECT membership_id, display_name FROM members WHERE membership_id IN ({marks})",
            unique,
        )
        names = {}
        for row in cur.fetchall():
            if isinstance(row, dict):
                member_id, name = row.get("membership_id"), row.get("display_name")
            else:
                member_id, name = row[0], row[1]
            if member_id and name:
                names[str(member_id)] = str(name)
        return names
    except Exception as exc:
        log.warning("Could not attach member names to the activity log: %s", exc)
        _recover(cur)
        return {}


def _user_clause(column: str, text: str, name_ids: list[str]) -> tuple[str, list]:
    parts = [f"COALESCE({column}, '') ILIKE %s ESCAPE '\\'"]
    params: list = [_like_pattern(text)]
    if name_ids:
        marks = ", ".join(["%s"] * len(name_ids))
        parts.append(f"{column} IN ({marks})")
        params.extend(name_ids)
    return "(" + " OR ".join(parts) + ")", params


def _select_events(cur, *, event_type, member_text, name_ids, date_from, date_to, query, query_ids, limit):
    clauses = []
    params: list = []
    if event_type:
        clauses.append("event_type = %s")
        params.append(event_type)
    if date_from:
        clauses.append("created_at >= (%s::date AT TIME ZONE 'America/Chicago')")
        params.append(date_from)
    if date_to:
        clauses.append("created_at < ((%s::date + INTERVAL '1 day') AT TIME ZONE 'America/Chicago')")
        params.append(date_to)
    if member_text:
        id_sql, id_params = _user_clause("membership_id", member_text, name_ids)
        attempted_sql, attempted_params = _user_clause("details->>'attempted_id'", member_text, name_ids)
        clauses.append(f"({id_sql} OR {attempted_sql})")
        params.extend(id_params)
        params.extend(attempted_params)
    if query:
        pattern = _like_pattern(query)
        parts = [
            "event_type ILIKE %s ESCAPE '\\'",
            "COALESCE(membership_id, '') ILIKE %s ESCAPE '\\'",
            "COALESCE(details->>'attempted_id', '') ILIKE %s ESCAPE '\\'",
            "COALESCE(details::text, '') ILIKE %s ESCAPE '\\'",
        ]
        params.extend([pattern, pattern, pattern, pattern])
        if query_ids:
            marks = ", ".join(["%s"] * len(query_ids))
            parts.append(f"membership_id IN ({marks})")
            params.extend(query_ids)
            parts.append(f"COALESCE(details->>'attempted_id', '') IN ({marks})")
            params.extend(query_ids)
        clauses.append("(" + " OR ".join(parts) + ")")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    cur.execute(
        f"""
        SELECT id, event_type, tier, created_at, membership_id, ip, user_agent, details
        FROM audit_events
        {where}
        ORDER BY created_at DESC, id DESC
        LIMIT %s
        """,
        params,
    )
    return list(cur.fetchall())


def _select_consents(cur, *, member_text, name_ids, date_from, date_to, query, query_ids, limit):
    clauses = []
    params: list = []
    if date_from:
        clauses.append("chosen_at >= (%s::date AT TIME ZONE 'America/Chicago')")
        params.append(date_from)
    if date_to:
        clauses.append("chosen_at < ((%s::date + INTERVAL '1 day') AT TIME ZONE 'America/Chicago')")
        params.append(date_to)
    if member_text:
        user_sql, user_params = _user_clause("membership_id", member_text, name_ids)
        clauses.append(user_sql)
        params.extend(user_params)
    if query:
        pattern = _like_pattern(query)
        parts = [
            "choice ILIKE %s ESCAPE '\\'",
            "version ILIKE %s ESCAPE '\\'",
            "COALESCE(membership_id, '') ILIKE %s ESCAPE '\\'",
            "'consent.choice' ILIKE %s ESCAPE '\\'",
        ]
        params.extend([pattern, pattern, pattern, pattern])
        if query_ids:
            marks = ", ".join(["%s"] * len(query_ids))
            parts.append(f"membership_id IN ({marks})")
            params.extend(query_ids)
        clauses.append("(" + " OR ".join(parts) + ")")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    cur.execute(
        f"""
        SELECT id, membership_id, choice, version, chosen_at, ip, user_agent
        FROM consent_choices
        {where}
        ORDER BY chosen_at DESC, id DESC
        LIMIT %s
        """,
        params,
    )
    return list(cur.fetchall())


def _event_row(record: dict) -> dict:
    created = record.get("created_at")
    return {
        "kind": "event",
        "id": int(record["id"]),
        "event_type": record.get("event_type") or "",
        "tier": record.get("tier") or "",
        "created_at": _iso(created),
        "_sort": created if isinstance(created, datetime) else datetime.min.replace(tzinfo=timezone.utc),
        "membership_id": record.get("membership_id") or "",
        "ip": record.get("ip") or "",
        "user_agent": record.get("user_agent") or "",
        "details": _public_details(record.get("details")),
        "choice": "",
        "version": "",
        "display_name": "",
    }


def _consent_row(record: dict) -> dict:
    created = record.get("chosen_at")
    choice = record.get("choice") or ""
    version = record.get("version") or ""
    return {
        "kind": "consent",
        "id": int(record["id"]),
        "event_type": "consent.choice",
        "tier": "necessary",
        "created_at": _iso(created),
        "_sort": created if isinstance(created, datetime) else datetime.min.replace(tzinfo=timezone.utc),
        "membership_id": record.get("membership_id") or "",
        "ip": record.get("ip") or "",
        "user_agent": record.get("user_agent") or "",
        "details": {"choice": choice, "version": version},
        "choice": choice,
        "version": version,
        "display_name": "",
    }


def _as_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _day_span(today: str, count: int = 14) -> list[str]:
    try:
        end = datetime.strptime(str(today)[:10], "%Y-%m-%d").date()
    except ValueError:
        end = datetime.now(timezone.utc).date()
    return [(end - timedelta(days=offset)).isoformat() for offset in range(count - 1, -1, -1)]


def _activity_summary(cur) -> dict:
    """Totals for the webmaster charts. Independent of the table filters."""
    cur.execute(
        """
        SELECT event_type, tier, COUNT(*)::int AS count
        FROM audit_events
        GROUP BY event_type, tier
        """
    )
    counts: dict[str, int] = {}
    necessary = 0
    accept = 0
    for row in cur.fetchall():
        event_type = str(row["event_type"] or "")
        count = int(row["count"] or 0)
        counts[event_type] = counts.get(event_type, 0) + count
        if row["tier"] == "accept":
            accept += count
        else:
            necessary += count
    cur.execute("SELECT to_char((NOW() AT TIME ZONE 'America/Chicago')::date, 'YYYY-MM-DD') AS today")
    today_row = cur.fetchone()
    today = str(today_row["today"]) if today_row and today_row["today"] else datetime.now(timezone.utc).date().isoformat()
    days = _day_span(today)
    cur.execute(
        """
        SELECT to_char((created_at AT TIME ZONE 'America/Chicago')::date, 'YYYY-MM-DD') AS day,
               event_type,
               COUNT(*)::int AS count
        FROM audit_events
        WHERE event_type IN ('auth.login_success', 'auth.login_failure', 'page.view')
          AND (created_at AT TIME ZONE 'America/Chicago')::date >= %s::date
        GROUP BY 1, 2
        """,
        (days[0],),
    )
    by_day: dict[str, dict[str, int]] = {day: {} for day in days}
    for row in cur.fetchall():
        day = str(row["day"] or "")
        if day in by_day:
            by_day[day][str(row["event_type"] or "")] = int(row["count"] or 0)
    cur.execute(
        """
        SELECT choice, COUNT(*)::int AS count
        FROM consent_choices
        GROUP BY choice
        """
    )
    consent = {"accepted": 0, "declined": 0}
    for row in cur.fetchall():
        choice = str(row["choice"] or "")
        if choice in consent:
            consent[choice] = int(row["count"] or 0)
    cur.execute(
        """
        SELECT e.event_type, e.created_at, e.membership_id, e.details, m.display_name
        FROM audit_events e
        LEFT JOIN members m ON m.membership_id = e.membership_id
        WHERE e.event_type IN ('admin.content_create', 'admin.content_update', 'admin.content_delete')
        ORDER BY e.created_at DESC
        LIMIT 6
        """
    )
    changes = []
    for row in cur.fetchall():
        details = _as_dict(row["details"])
        changes.append(
            {
                "event_type": str(row["event_type"] or ""),
                "created_at": _iso(row["created_at"]),
                "membership_id": str(row["membership_id"] or ""),
                "display_name": str(row["display_name"] or ""),
                "content_type": str(details.get("content_type") or ""),
                "record_id": str(details.get("record_id") or ""),
            }
        )
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:8]
    return {
        "events": necessary + accept,
        "necessary": necessary,
        "accept": accept,
        "login_success": counts.get("auth.login_success", 0),
        "login_failure": counts.get("auth.login_failure", 0),
        "login_bursts": counts.get("security.login_burst", 0),
        "logins_by_day": [
            {
                "day": day,
                "success": by_day[day].get("auth.login_success", 0),
                "failure": by_day[day].get("auth.login_failure", 0),
            }
            for day in days
        ],
        "top_events": [{"event_type": name, "count": count} for name, count in ranked],
        "consent_accepted": consent["accepted"],
        "consent_declined": consent["declined"],
        "document_downloads": counts.get("document.download", 0),
        "document_previews": counts.get("document.preview", 0),
        "page_views": counts.get("page.view", 0),
        "page_views_by_day": [
            {"day": day, "count": by_day[day].get("page.view", 0)} for day in days
        ],
        "content_changes": changes,
    }


def list_activity(
    *,
    event_type: str = "",
    member_id: str = "",
    date_from: str = "",
    date_to: str = "",
    query: str = "",
) -> dict:
    """Read audit rows for an admin. A database failure is unavailable, not an exception.

    This reader is intentionally outside _guard. None would look like an empty log.
    It uses tracking's own connection and does not change the site's memory fallback.
    """
    conn = _connect()
    if conn is None:
        return _unavailable()
    try:
        from psycopg.rows import dict_row

        conn.autocommit = True
        event_name = _clip(event_type, 80)
        member_text = _clip(member_id, 80)
        query_text = _clip(query, 120)
        start = _day(date_from)
        end = _day(date_to)
        fetch_limit = _ROW_LIMIT + 1
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SET statement_timeout = '4000'")
            name_ids = _member_ids_for(cur, member_text)
            query_ids = _member_ids_for(cur, query_text)
            events = _select_events(
                cur,
                event_type=event_name,
                member_text=member_text,
                name_ids=name_ids,
                date_from=start,
                date_to=end,
                query=query_text,
                query_ids=query_ids,
                limit=fetch_limit,
            )
            consents = []
            if event_name in {"", "consent.choice"}:
                consents = _select_consents(
                    cur,
                    member_text=member_text,
                    name_ids=name_ids,
                    date_from=start,
                    date_to=end,
                    query=query_text,
                    query_ids=query_ids,
                    limit=fetch_limit,
                )
            rows = [_event_row(record) for record in events]
            rows.extend(_consent_row(record) for record in consents)
            rows.sort(key=lambda row: (row["_sort"], row["id"]), reverse=True)
            truncated = len(rows) > _ROW_LIMIT
            visible = rows[:_ROW_LIMIT]
            ids = []
            for row in visible:
                if row["membership_id"]:
                    ids.append(row["membership_id"])
                attempted = row["details"].get("attempted_id") if row["kind"] == "event" else ""
                if isinstance(attempted, str) and attempted:
                    ids.append(attempted)
            names = _names_for(cur, ids)
            for row in visible:
                mid = row["membership_id"]
                attempted = row["details"].get("attempted_id") if row["kind"] == "event" else ""
                if mid and mid in names:
                    row["display_name"] = names[mid]
                elif isinstance(attempted, str) and attempted in names:
                    row["display_name"] = names[attempted]
                row.pop("_sort", None)
            summary = None
            try:
                summary = _activity_summary(cur)
            except Exception as exc:
                log.warning("Could not summarize activity: %s", exc)
        return {"available": True, "truncated": truncated, "rows": visible, "summary": summary}
    except Exception as exc:
        log.warning("Could not read the activity log: %s", exc)
        return _unavailable()
    finally:
        try:
            conn.close()
        except Exception:
            pass
