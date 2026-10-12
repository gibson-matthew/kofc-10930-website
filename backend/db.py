"""Page and member store. Uses Postgres when it answers, otherwise memory."""

from __future__ import annotations

import logging
import os
import threading
from copy import deepcopy
from datetime import datetime, timezone

from security import hash_password, verify_password, verify_password_dummy
from seed import PAGES

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/koc10930"
# Documented local account. Created only when this membership id is missing.
TEST_MEMBER_ID = "1000000"
TEST_MEMBER_PASSWORD = "Password123!"
TEST_MEMBER_NAME = "Test Member"

log = logging.getLogger("koc10930")


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def _connect():
    try:
        import psycopg
    except ImportError:
        return None
    try:
        return psycopg.connect(_database_url(), connect_timeout=2)
    except Exception:
        return None


class Store:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._memory = {slug: deepcopy(blocks) for slug, blocks in PAGES.items()}
        self._members: list[dict] = []
        self._refresh: dict[str, dict] = {}
        self._prefer_memory = False

    def prepare(self) -> str:
        """Create auth tables and the test member. Returns a short status."""
        hashed = hash_password(TEST_MEMBER_PASSWORD)
        with self._lock:
            self._prefer_memory = False
            self._members = [
                {
                    "membership_id": TEST_MEMBER_ID,
                    "password_hash": hashed,
                    "display_name": TEST_MEMBER_NAME,
                }
            ]
        conn = _connect()
        if conn is None:
            with self._lock:
                self._prefer_memory = True
            return "memory"
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS members (
                      id SERIAL PRIMARY KEY,
                      membership_id TEXT NOT NULL UNIQUE,
                      password_hash TEXT NOT NULL,
                      display_name TEXT NOT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS refresh_tokens (
                      jti TEXT PRIMARY KEY,
                      membership_id TEXT NOT NULL REFERENCES members (membership_id) ON DELETE CASCADE,
                      expires_at TIMESTAMPTZ NOT NULL,
                      revoked_at TIMESTAMPTZ,
                      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS refresh_tokens_member_idx
                    ON refresh_tokens (membership_id)
                    """
                )
                cur.execute(
                    """
                    INSERT INTO members (membership_id, password_hash, display_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (membership_id) DO NOTHING
                    RETURNING id
                    """,
                    (TEST_MEMBER_ID, hashed, TEST_MEMBER_NAME),
                )
                created = cur.fetchone()
                if created:
                    conn.commit()
                    conn.close()
                    return "created"
                cur.execute(
                    "SELECT password_hash FROM members WHERE membership_id = %s",
                    (TEST_MEMBER_ID,),
                )
                row = cur.fetchone()
                if row and row[0] == "sha256:demo-not-checked":
                    cur.execute(
                        """
                        UPDATE members
                        SET password_hash = %s, display_name = %s
                        WHERE membership_id = %s
                        """,
                        (hashed, TEST_MEMBER_NAME, TEST_MEMBER_ID),
                    )
                    conn.commit()
                    conn.close()
                    return "created"
                conn.commit()
                conn.close()
            if row and verify_password(TEST_MEMBER_PASSWORD, row[0]):
                return "present"
            return "different-password"
        except Exception as exc:
            log.warning("PostgreSQL auth setup failed: %s", exc)
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            with self._lock:
                self._prefer_memory = True
            return "memory"

    def authenticate(self, memberid: str, password: str) -> dict | None:
        record = self._member_record(memberid)
        if record is None:
            verify_password_dummy(password)
            return None
        if not verify_password(password, record["password_hash"]):
            return None
        return self._public_member(record)

    def get_member(self, memberid: str) -> dict | None:
        record = self._member_record(memberid)
        if record is None:
            return None
        return self._public_member(record)

    def store_refresh(self, token_id: str, memberid: str, expires_at: datetime) -> None:
        conn = self._open()
        if conn is None:
            with self._lock:
                self._refresh[token_id] = {
                    "membership_id": memberid,
                    "expires_at": expires_at,
                    "revoked": False,
                }
            return
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO refresh_tokens (jti, membership_id, expires_at)
                    VALUES (%s, %s, %s)
                    """,
                    (token_id, memberid, expires_at),
                )
            conn.commit()
            conn.close()
        except Exception as exc:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            raise RuntimeError("refresh token was not stored") from exc

    def rotate_refresh(self, token_id: str, memberid: str) -> bool:
        now = datetime.now(timezone.utc)
        conn = self._open()
        if conn is None:
            with self._lock:
                row = self._refresh.get(token_id)
                if row is None or row["membership_id"] != memberid:
                    return False
                expires_at = row["expires_at"]
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if row["revoked"]:
                    for item in self._refresh.values():
                        if item["membership_id"] == memberid:
                            item["revoked"] = True
                    return False
                if expires_at <= now:
                    return False
                row["revoked"] = True
                return True
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT membership_id, expires_at, revoked_at
                    FROM refresh_tokens
                    WHERE jti = %s
                    FOR UPDATE
                    """,
                    (token_id,),
                )
                row = cur.fetchone()
                if row is None or row[0] != memberid:
                    conn.rollback()
                    conn.close()
                    return False
                expires_at = row[1]
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if row[2] is not None:
                    cur.execute(
                        """
                        UPDATE refresh_tokens
                        SET revoked_at = COALESCE(revoked_at, NOW())
                        WHERE membership_id = %s AND revoked_at IS NULL
                        """,
                        (memberid,),
                    )
                    conn.commit()
                    conn.close()
                    return False
                if expires_at <= now:
                    conn.rollback()
                    conn.close()
                    return False
                cur.execute(
                    """
                    UPDATE refresh_tokens
                    SET revoked_at = NOW()
                    WHERE jti = %s AND revoked_at IS NULL
                    """,
                    (token_id,),
                )
                updated = cur.rowcount == 1
            conn.commit()
            conn.close()
            return updated
        except Exception as exc:
            log.warning("Refresh token check failed: %s", exc)
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            return False

    def revoke_refresh(self, token_id: str) -> None:
        conn = self._open()
        if conn is None:
            with self._lock:
                row = self._refresh.get(token_id)
                if row is not None:
                    row["revoked"] = True
            return
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE refresh_tokens
                    SET revoked_at = COALESCE(revoked_at, NOW())
                    WHERE jti = %s
                    """,
                    (token_id,),
                )
            conn.commit()
            conn.close()
        except Exception as exc:
            log.warning("Could not revoke refresh token: %s", exc)
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass

    def _member_record(self, memberid: str) -> dict | None:
        memberid = memberid.strip()
        if not memberid:
            return None
        conn = self._open()
        if conn is None:
            return self._memory_member(memberid)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT membership_id, password_hash, display_name
                    FROM members
                    WHERE membership_id = %s
                    """,
                    (memberid,),
                )
                row = cur.fetchone()
            conn.close()
        except Exception as exc:
            log.warning("Member lookup failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            return self._memory_member(memberid)
        if row is None:
            return None
        return {
            "membership_id": row[0],
            "password_hash": row[1],
            "display_name": row[2],
        }

    def _memory_member(self, memberid: str) -> dict | None:
        with self._lock:
            for member in self._members:
                if member["membership_id"] == memberid:
                    return dict(member)
        return None

    @staticmethod
    def _public_member(record: dict) -> dict:
        return {
            "memberid": record["membership_id"],
            "display_name": record["display_name"],
        }

    def get_page(self, slug: str) -> dict:
        if slug not in PAGES:
            raise KeyError(slug)
        with self._lock:
            if self._prefer_memory:
                return self._page_payload(slug, self._memory[slug])
        rows = self._load_db(slug)
        if rows is None:
            with self._lock:
                self._prefer_memory = True
                return self._page_payload(slug, self._memory[slug])
        merged = {block["key"]: deepcopy(block) for block in PAGES[slug]}
        for row in rows:
            merged[row["key"]] = row
        blocks = sorted(merged.values(), key=lambda block: (block["sort_order"], block["key"]))
        with self._lock:
            self._memory[slug] = deepcopy(blocks)
        return self._page_payload(slug, blocks)

    def save_member(self, blocks: list[dict]) -> dict:
        normalized = self._normalize(blocks)
        with self._lock:
            current = {block["key"]: deepcopy(block) for block in self._memory["member"]}
            for block in normalized:
                current[block["key"]] = block
            ordered = sorted(current.values(), key=lambda block: (block["sort_order"], block["key"]))
            self._memory["member"] = ordered
            prefer_memory = self._prefer_memory
        if not prefer_memory and not self._save_db(ordered):
            with self._lock:
                self._prefer_memory = True
        return self.get_page("member")

    def _open(self):
        with self._lock:
            if self._prefer_memory:
                return None
        conn = _connect()
        if conn is None:
            with self._lock:
                self._prefer_memory = True
            return None
        return conn

    def _load_db(self, slug: str) -> list[dict] | None:
        conn = self._open()
        if conn is None:
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT b."key", b.field_type, b.value, b.sort_order
                    FROM content_blocks b
                    JOIN pages p ON p.id = b.page_id
                    WHERE p.slug = %s
                    ORDER BY b.sort_order, b."key"
                    """,
                    (slug,),
                )
                fetched = cur.fetchall()
            conn.close()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return None
        return [
            {
                "key": row[0],
                "field_type": row[1],
                "value": row[2],
                "sort_order": row[3],
            }
            for row in fetched
        ]

    def _save_db(self, blocks: list[dict]) -> bool:
        conn = self._open()
        if conn is None:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM pages WHERE slug = %s", ("member",))
                page = cur.fetchone()
                if page is None:
                    conn.rollback()
                    conn.close()
                    return False
                page_id = page[0]
                for block in blocks:
                    cur.execute(
                        """
                        INSERT INTO content_blocks
                          (page_id, "key", field_type, value, sort_order, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (page_id, "key")
                        DO UPDATE SET
                          value = EXCLUDED.value,
                          field_type = EXCLUDED.field_type,
                          sort_order = EXCLUDED.sort_order,
                          updated_at = NOW()
                        """,
                        (
                            page_id,
                            block["key"],
                            block["field_type"],
                            block["value"],
                            block["sort_order"],
                        ),
                    )
            conn.commit()
            conn.close()
            return True
        except Exception:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            return False

    def _normalize(self, blocks: list[dict]) -> list[dict]:
        known = {block["key"]: block for block in PAGES["member"]}
        cleaned: list[dict] = []
        for block in blocks:
            key = block["key"]
            base = known.get(key)
            field_type = block.get("field_type") or (base["field_type"] if base else "text")
            sort_order = block.get("sort_order")
            if sort_order is None:
                sort_order = base["sort_order"] if base else 0
            cleaned.append(
                {
                    "key": key,
                    "field_type": field_type,
                    "value": "" if block.get("value") is None else str(block.get("value")),
                    "sort_order": sort_order,
                }
            )
        return cleaned

    @staticmethod
    def _page_payload(slug: str, blocks: list[dict]) -> dict:
        return {
            "slug": slug,
            "blocks": [
                {
                    "key": block["key"],
                    "field_type": block["field_type"],
                    "value": block["value"],
                    "sort_order": block["sort_order"],
                }
                for block in blocks
            ],
        }


store = Store()
