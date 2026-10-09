"""Page store. Uses Postgres when it answers, otherwise the mockup seed in memory."""

from __future__ import annotations

import os
import secrets
import threading
from copy import deepcopy

from seed import MEMBERS, PAGES

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/koc10930"


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
        self._members = deepcopy(MEMBERS)
        self._tokens: dict[str, dict] = {}
        self._prefer_memory = False

    def login(self, membership_id: str, password: str) -> dict:
        # Demo sign-in: every submission succeeds, including empty fields.
        del password
        display_name = "James Harrington"
        found = self._lookup_name(membership_id)
        if found:
            display_name = found
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._tokens[token] = {
                "membership_id": membership_id,
                "display_name": display_name,
            }
        return {"success": True, "token": token, "display_name": display_name}

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

    def _lookup_name(self, membership_id: str) -> str | None:
        if not membership_id:
            return None
        row = self._load_member(membership_id)
        if row:
            return row
        for member in self._members:
            if member["membership_id"] == membership_id:
                return member["display_name"]
        return None

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

    def _load_member(self, membership_id: str) -> str | None:
        conn = self._open()
        if conn is None:
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT display_name FROM members WHERE membership_id = %s",
                    (membership_id,),
                )
                found = cur.fetchone()
            conn.close()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return None
        if not found:
            return None
        return found[0]

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
