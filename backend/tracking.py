"""Privacy-aware audit log.

Necessary events are always stored. Accept-tier events are stored only when
the visitor has accepted optional tracking. A failed write never blocks the
request that triggered it. See TRACKING.md for the event list and the items
this site deliberately does not record.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

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


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/koc10930")


def _connect():
    try:
        import psycopg
    except ImportError:
        return None
    try:
        return psycopg.connect(_database_url(), connect_timeout=2)
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
    from security import cookie_secure

    stamp = int(datetime.now(timezone.utc).timestamp())
    response.set_cookie(
        CONSENT_COOKIE,
        f"{CONSENT_VERSION}.{choice}.{stamp}",
        max_age=CONSENT_MAX_AGE,
        httponly=False,
        secure=cookie_secure(),
        samesite="lax",
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
    if member.get("is_admin"):
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


def flag_change(request, admin_id, target_id, before, after) -> None:
    old = None if before is None else bool(before.get("is_admin"))
    new = None if after is None else bool(after.get("is_admin"))
    if before is not None and old == new:
        return
    record(
        request,
        "admin.flag_change",
        tier="necessary",
        member_id=admin_id,
        details={
            "content_type": "admin_flag",
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
        from security import access_from_request, decode_token

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
