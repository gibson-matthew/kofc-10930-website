"""Page and member store. Uses Postgres when it answers, otherwise memory."""

from __future__ import annotations

import logging
import re
import threading
from copy import deepcopy
from datetime import date, datetime, timezone

from announcements import (
    ANNOUNCEMENT_SEED,
    clean_announcement_body,
    clean_announcement_summary,
    clean_announcement_title,
    sanitize_html,
)
from prayers import (
    PRAYER_SEED,
    clean_prayer_body,
    clean_prayer_title,
    display_person_name,
    display_prayer_body,
    display_prayer_title,
)
from nominations import (
    CATEGORY_ORDER,
    NOMINATION_SEED,
    active_periods,
    build_results,
    clean_nomination_name,
    clean_nomination_reason,
    display_nomination_name,
    display_nomination_reason,
    in_active_period,
    period_for,
    resolve_nominee,
)
from media import (
    RECOG_SLOTS,
    SEED_DOCUMENTS,
    SEED_IMAGES,
    absolute_path,
    clean_document_description,
    clean_document_title,
    delete_stored_file,
    document_path_allowed,
    ensure_seed_documents,
    normalize_library,
    public_url,
    slot_check_sql,
    uploaded_on,
    write_upload,
)
from security import hash_password, verify_password, verify_password_dummy
from seed import EVENT_SEED, HONOR_SEED, PAGES
from test_seed import DIRECTORY_SEED, MEMBER_SEED, directory_fields, ensure_seed_photos, member_photo_path
from titles import (
    DIRECTOR_ROLE_SET,
    OFFICER_ROLE_SET,
    TITLE_ABBREVS,
    normalize_title,
)
import cache
from config import database_url

# Documented local account. Created only when this membership id is missing.
# Password123! is also the shared password for 1000001 and roster ids 1000100–1000149.
TEST_MEMBER_ID = "1000000"
TEST_MEMBER_PASSWORD = "Password123!"
TEST_MEMBER_NAME = "David Hernandez"
TEST_MEMBER_TITLE = "GK"
# Second local account so the webmaster can grant admin access to someone else.
SAMPLE_MEMBER_ID = "1000001"
SAMPLE_MEMBER_NAME = "Sample Brother"
# Quick-link cards removed from Members Quick Links. Deleted on startup so an
# existing database cannot merge them back onto the member page.
_RETIRED_MEMBER_LINK_KEYS = (
    "links.5.title",
    "links.5.action",
    "links.5.detail",
    "links.7.title",
    "links.7.action",
    "links.7.detail",
    "links.8.title",
    "links.8.action",
    "links.8.detail",
    "links.10.title",
    "links.10.body",
    "links.10.action",
    "links.10.detail",
)

log = logging.getLogger("koc10930")


class StoreError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


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


def _field_ok(value, kind: str) -> bool:
    if kind == "str":
        return isinstance(value, str)
    if kind == "str?":
        return value is None or isinstance(value, str)
    if kind == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "int?":
        return value is None or (isinstance(value, int) and not isinstance(value, bool))
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "num":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


def _cache_list(
    rows,
    required: tuple[str, ...],
    banned: tuple[str, ...] = (),
    kinds: dict | None = None,
) -> list | None:
    """Return a cached list only when every row has the public fields and nothing sensitive."""
    if not isinstance(rows, list):
        return None
    for item in rows:
        if not isinstance(item, dict):
            return None
        if any(key in item for key in banned):
            return None
        if any(key not in item for key in required):
            return None
        if kinds is not None and any(not _field_ok(item.get(key), kind) for key, kind in kinds.items()):
            return None
    return rows


_MEMBER_CACHE_FIELDS = (
    "memberid",
    "display_name",
    "title",
    "is_admin",
    "is_webmaster",
    "is_cloudflare",
    "photo_url",
    "crop_x",
    "crop_y",
    "crop_scale",
    "birth_month",
    "birth_day",
    "honorary_life",
)


def _cached_page(slug: str, payload) -> dict | None:
    if not isinstance(payload, dict) or payload.get("slug") != slug:
        return None
    blocks = payload.get("blocks")
    if not isinstance(blocks, list):
        return None
    for block in blocks:
        if not isinstance(block, dict):
            return None
        if not _field_ok(block.get("key"), "str") or not _field_ok(block.get("field_type"), "str"):
            return None
        if not _field_ok(block.get("value"), "str") or not _field_ok(block.get("sort_order"), "int"):
            return None
    return payload


def _cached_tallies(payload) -> dict | None:
    if not isinstance(payload, dict):
        return None
    if not _field_ok(payload.get("month_period"), "str") or not _field_ok(payload.get("year_period"), "str"):
        return None
    categories = payload.get("categories")
    if not isinstance(categories, list):
        return None
    for category in categories:
        if not isinstance(category, dict):
            return None
        if not _field_ok(category.get("category"), "str") or not _field_ok(category.get("label"), "str"):
            return None
        nominees = category.get("nominees")
        if not isinstance(nominees, list):
            return None
        for nominee in nominees:
            if not isinstance(nominee, dict):
                return None
            if not _field_ok(nominee.get("nominee_name"), "str") or not _field_ok(nominee.get("votes"), "int"):
                return None
            if not _field_ok(nominee.get("nominee_member_id"), "str"):
                return None
            people = nominee.get("nominators")
            if not isinstance(people, list):
                return None
            for person in people:
                if not isinstance(person, dict):
                    return None
                if not _field_ok(person.get("member_id"), "str") or not _field_ok(person.get("display_name"), "str"):
                    return None
                if not _field_ok(person.get("reason"), "str"):
                    return None
    return payload


class Store:
    def __init__(self) -> None:
        ensure_seed_photos()
        ensure_seed_documents()
        self._lock = threading.Lock()
        self._memory = {slug: deepcopy(blocks) for slug, blocks in PAGES.items()}
        self._members: list[dict] = []
        self._images: list[dict] = _seed_image_rows()
        self._image_seq = len(self._images) + 1
        self._honors = _seed_honor_rows()
        self._events = _seed_event_rows()
        self._documents = _seed_document_rows()
        self._announcements = _seed_announcement_rows()
        self._prayers = _seed_prayer_rows()
        self._nominations = _seed_nomination_rows()
        self._honor_seq = len(self._honors) + 1
        self._event_seq = len(self._events) + 1
        self._document_seq = len(self._documents) + 1
        self._announcement_seq = len(self._announcements) + 1
        self._prayer_seq = len(self._prayers) + 1
        self._nomination_seq = len(self._nominations) + 1
        self._refresh: dict[str, dict] = {}
        self._prefer_memory = False

    def prepare(self) -> str:
        """Create auth tables, the webmaster, the test roster, and example images."""
        ensure_seed_photos()
        ensure_seed_documents()
        hashed = hash_password(TEST_MEMBER_PASSWORD)
        with self._lock:
            self._prefer_memory = False
            self._members = _memory_member_rows(hashed)
            self._images = _seed_image_rows()
            self._image_seq = len(self._images) + 1
            self._honors = _seed_honor_rows()
            self._events = _seed_event_rows()
            self._documents = _seed_document_rows()
            self._announcements = _seed_announcement_rows()
            self._prayers = _seed_prayer_rows()
            self._nominations = _seed_nomination_rows()
            self._honor_seq = len(self._honors) + 1
            self._event_seq = len(self._events) + 1
            self._document_seq = len(self._documents) + 1
            self._announcement_seq = len(self._announcements) + 1
            self._prayer_seq = len(self._prayers) + 1
            self._nomination_seq = len(self._nominations) + 1
        conn = _connect()
        if conn is None:
            with self._lock:
                self._prefer_memory = True
            return "memory"
        try:
            with conn.cursor() as cur:
                _ensure_schema(cur)
                _remove_retired_link_blocks(cur)
                from tracking import ensure_audit_schema

                ensure_audit_schema(cur)
                _seed_images(cur)
                _ensure_records(cur)
                status = _upsert_test_member(cur, hashed)
                _ensure_sample_member(cur, hashed)
                _ensure_admin(cur)
                _ensure_webmaster(cur)
                _ensure_cloudflare(cur)
                _rename_test_member(cur)
                _ensure_test_roster(cur, hashed)
            conn.commit()
            conn.close()
            return status
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
                cur.execute(_MEMBER_SELECT + " WHERE m.membership_id = %s", (memberid,))
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
        return _record_from_row(row)

    def _memory_member(self, memberid: str) -> dict | None:
        with self._lock:
            for member in self._members:
                if member["membership_id"] == memberid:
                    photo = _profile_in(self._images, memberid)
                    record = dict(member)
                    record["photo_id"] = photo["id"] if photo else None
                    record["photo_path"] = photo["path"] if photo else None
                    record["crop_x"] = photo.get("crop_x", 0) if photo else 0
                    record["crop_y"] = photo.get("crop_y", 0) if photo else 0
                    record["crop_scale"] = photo.get("crop_scale", 1) if photo else 1
                    return record
        return None

    def _public_member(self, record: dict) -> dict:
        title = record.get("title") or None
        if isinstance(title, str):
            title = title.strip() or None
        photo_url = None
        if record.get("photo_id") and record.get("photo_path"):
            photo_url = public_url(int(record["photo_id"]), str(record["photo_path"]))
        return {
            "memberid": record["membership_id"],
            "display_name": record["display_name"],
            "title": title,
            "is_admin": bool(record.get("is_admin")),
            "is_webmaster": bool(record.get("is_webmaster")),
            "is_cloudflare": bool(record.get("is_cloudflare")),
            "photo_url": photo_url,
            "crop_x": float(record.get("crop_x") or 0),
            "crop_y": float(record.get("crop_y") or 0),
            "crop_scale": float(record.get("crop_scale") or 1),
            "birth_month": _birthday_number(record.get("birth_month")),
            "birth_day": _birthday_number(record.get("birth_day")),
            "honorary_life": bool(record.get("honorary_life")),
        }

    def _directory_member(self, record: dict) -> dict:
        row = self._public_member(record)
        row["phone"] = str(record.get("phone") or "").strip()
        row["email"] = str(record.get("email") or "").strip()
        return row

    def _member_records(self) -> list[dict]:
        conn = self._open()
        if conn is None:
            with self._lock:
                rows = []
                for member in self._members:
                    photo = _profile_in(self._images, member["membership_id"])
                    record = dict(member)
                    record["photo_id"] = photo["id"] if photo else None
                    record["photo_path"] = photo["path"] if photo else None
                    record["crop_x"] = photo.get("crop_x", 0) if photo else 0
                    record["crop_y"] = photo.get("crop_y", 0) if photo else 0
                    record["crop_scale"] = photo.get("crop_scale", 1) if photo else 1
                    rows.append(record)
            return rows
        try:
            with conn.cursor() as cur:
                cur.execute(
                    _MEMBER_SELECT
                    + """
                    ORDER BY lower(m.display_name), m.membership_id
                    """
                )
                fetched = cur.fetchall()
            conn.close()
        except Exception as exc:
            log.warning("Member list failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            raise StoreError("Could not load members.", 503) from exc
        return [_record_from_row(row) for row in fetched]

    def list_members(self) -> list[dict]:
        if self._cache_ready():
            cached = _cache_list(
                cache.get_json(cache.MEMBERS),
                _MEMBER_CACHE_FIELDS,
                ("password", "password_hash", "phone", "email", "token"),
                {
                    "memberid": "str",
                    "display_name": "str",
                    "title": "str?",
                    "is_admin": "bool",
                    "is_webmaster": "bool",
                    "is_cloudflare": "bool",
                    "photo_url": "str?",
                    "crop_x": "num",
                    "crop_y": "num",
                    "crop_scale": "num",
                    "birth_month": "int?",
                    "birth_day": "int?",
                    "honorary_life": "bool",
                },
            )
            if cached is not None:
                return cached
        with self._lock:
            was_memory = self._prefer_memory
        rows = [self._public_member(record) for record in self._member_records()]
        rows.sort(key=lambda item: (item["display_name"].lower(), item["memberid"]))
        with self._lock:
            still_memory = self._prefer_memory
        if not was_memory and not still_memory:
            cache.store_roster(rows)
        return rows

    def list_directory(self) -> list[dict]:
        """Member list plus contact fields. The route omits phone and email for non-admins."""
        rows = [self._directory_member(record) for record in self._member_records()]
        rows.sort(key=lambda item: (item["display_name"].lower(), item["memberid"]))
        return rows

    def set_title(self, memberid: str, title: str | None) -> dict:
        try:
            cleaned = normalize_title(title)
        except ValueError as exc:
            raise StoreError(str(exc), 400) from exc
        if cleaned == "PGK":
            raise StoreError("Enter the year this Past Grand Knight served.", 400)
        conn = self._open()
        if conn is None:
            with self._lock:
                target = next((item for item in self._members if item["membership_id"] == memberid), None)
                if target is None:
                    raise StoreError("Member was not found.", 404)
                if cleaned:
                    for member in self._members:
                        if member is not target and member.get("title") == cleaned:
                            member["title"] = None
                target["title"] = cleaned
            record = self._memory_member(memberid)
            if record is None:
                raise StoreError("Member was not found.", 404)
            return self._public_member(record)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT membership_id
                    FROM members
                    WHERE membership_id = %s OR (%s IS NOT NULL AND title = %s)
                    ORDER BY membership_id
                    FOR UPDATE
                    """,
                    (memberid, cleaned, cleaned),
                )
                rows = cur.fetchall()
                if not any(row[0] == memberid for row in rows):
                    conn.rollback()
                    conn.close()
                    raise StoreError("Member was not found.", 404)
                if cleaned:
                    cur.execute(
                        """
                        UPDATE members
                        SET title = NULL
                        WHERE title = %s AND membership_id <> %s
                        """,
                        (cleaned, memberid),
                    )
                cur.execute(
                    """
                    UPDATE members
                    SET title = %s
                    WHERE membership_id = %s
                    """,
                    (cleaned, memberid),
                )
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save the title.", 503) from exc
        member = self.get_member(memberid)
        if member is None:
            raise StoreError("Member was not found.", 404)
        return member

    def assign_pgk(self, memberid: str, period: str, note: str) -> dict:
        memberid = str(memberid or "").strip()
        preview = self.get_member(memberid)
        if preview is None:
            raise StoreError("Member was not found.", 404)
        payload = _pgk_honor_payload(preview["display_name"], "PGK", period, note)
        if payload is None:
            raise StoreError("Enter the year this Past Grand Knight served.", 400)
        conn = self._open()
        if conn is None:
            return self._assign_pgk_memory(memberid, payload)
        copied = None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT display_name
                    FROM members
                    WHERE membership_id = %s
                    FOR UPDATE
                    """,
                    (memberid,),
                )
                locked = cur.fetchone()
                if locked is None:
                    raise StoreError("Member was not found.", 404)
                payload = _pgk_honor_payload(locked[0], "PGK", period, note)
                cur.execute(
                    """
                    SELECT path, crop_x, crop_y, crop_scale
                    FROM images
                    WHERE owner_membership_id = %s AND purpose = 'profile'
                    """,
                    (memberid,),
                )
                photo_row = cur.fetchone()
                existing = _lock_past_gk(cur, payload["name"], payload["period"])
                photo = None
                crop = (0.0, 0.0, 1.0)
                if (existing is None or not existing[1]) and photo_row and photo_row[0]:
                    photo, crop = _copy_member_photo(photo_row[0], photo_row[1], photo_row[2], photo_row[3])
                    copied = photo[0] if photo else None
                unused = _save_past_gk(cur, payload, existing, photo, crop)
                if unused:
                    delete_stored_file(unused)
                    if unused == copied:
                        copied = None
                cur.execute(
                    "UPDATE members SET title = NULL WHERE title = 'PGK' AND membership_id <> %s",
                    (memberid,),
                )
                cur.execute(
                    "UPDATE members SET title = 'PGK' WHERE membership_id = %s",
                    (memberid,),
                )
            conn.commit()
        except StoreError:
            _rollback(conn)
            if copied:
                delete_stored_file(copied)
            raise
        except Exception as exc:
            _rollback(conn)
            if copied:
                delete_stored_file(copied)
            raise StoreError("Could not save Past Grand Knight.", 503) from exc
        try:
            conn.close()
        except Exception:
            pass
        member = self.get_member(memberid)
        if member is None:
            raise StoreError("Member was not found.", 404)
        return member

    def _assign_pgk_memory(self, memberid: str, payload: dict) -> dict:
        record = self._memory_member(memberid)
        if record is None:
            raise StoreError("Member was not found.", 404)
        photo = None
        crop = (0.0, 0.0, 1.0)
        copied = None
        with self._lock:
            match = None
            for item in self._honors:
                if item.get("category") != "past_gk":
                    continue
                if str(item.get("name") or "").casefold() != payload["name"].casefold():
                    continue
                if item.get("period") != payload["period"]:
                    continue
                if match is None or int(item["id"]) > int(match["id"]):
                    match = item
            needs_photo = match is None or not match.get("photo_path")
        if needs_photo and record.get("photo_path"):
            photo, crop = _copy_member_photo(
                record.get("photo_path"),
                record.get("crop_x"),
                record.get("crop_y"),
                record.get("crop_scale"),
            )
            copied = photo[0] if photo else None
        try:
            with self._lock:
                target = next((item for item in self._members if item["membership_id"] == memberid), None)
                if target is None:
                    raise StoreError("Member was not found.", 404)
                unused = _memory_save_past_gk(self, payload, photo, crop)
                if unused:
                    delete_stored_file(unused)
                    if unused == copied:
                        copied = None
                for member in self._members:
                    if member is not target and member.get("title") == "PGK":
                        member["title"] = None
                target["title"] = "PGK"
        except StoreError:
            if copied:
                delete_stored_file(copied)
            raise
        updated = self.get_member(memberid)
        if updated is None:
            raise StoreError("Member was not found.", 404)
        return updated

    def set_admin(self, memberid: str, is_admin: bool) -> dict:
        conn = self._open()
        if conn is None:
            with self._lock:
                target = next((item for item in self._members if item["membership_id"] == memberid), None)
                if target is None:
                    raise StoreError("Member was not found.", 404)
                if target["is_admin"] and not is_admin:
                    admins = sum(1 for item in self._members if item["is_admin"])
                    if admins <= 1:
                        raise StoreError("The council needs at least one admin.", 400)
                target["is_admin"] = bool(is_admin)
            record = self._memory_member(memberid)
            if record is None:
                raise StoreError("Member was not found.", 404)
            return self._public_member(record)
        try:
            with conn.cursor() as cur:
                # Lock the target and every admin in one ordered pass so two
                # demotions cannot both pass the "at least one admin" check.
                cur.execute(
                    """
                    SELECT membership_id, is_admin
                    FROM members
                    WHERE membership_id = %s OR is_admin
                    ORDER BY membership_id
                    FOR UPDATE
                    """,
                    (memberid,),
                )
                rows = cur.fetchall()
                target = next((item for item in rows if item[0] == memberid), None)
                if target is None:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Member was not found.", 404)
                if target[1] and not is_admin and sum(1 for item in rows if item[1]) <= 1:
                    conn.rollback()
                    conn.close()
                    raise StoreError("The council needs at least one admin.", 400)
                cur.execute(
                    "UPDATE members SET is_admin = %s WHERE membership_id = %s",
                    (bool(is_admin), memberid),
                )
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not update admin access.", 503) from exc
        member = self.get_member(memberid)
        if member is None:
            raise StoreError("Member was not found.", 404)
        return member

    def set_webmaster(self, memberid: str, is_webmaster: bool) -> dict:
        conn = self._open()
        if conn is None:
            with self._lock:
                target = next((item for item in self._members if item["membership_id"] == memberid), None)
                if target is None:
                    raise StoreError("Member was not found.", 404)
                if target.get("is_webmaster") and not is_webmaster:
                    webmasters = sum(1 for item in self._members if item.get("is_webmaster"))
                    if webmasters <= 1:
                        raise StoreError("The council needs at least one webmaster.", 400)
                target["is_webmaster"] = bool(is_webmaster)
            record = self._memory_member(memberid)
            if record is None:
                raise StoreError("Member was not found.", 404)
            return self._public_member(record)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT membership_id, is_webmaster
                    FROM members
                    WHERE membership_id = %s OR is_webmaster
                    ORDER BY membership_id
                    FOR UPDATE
                    """,
                    (memberid,),
                )
                rows = cur.fetchall()
                target = next((item for item in rows if item[0] == memberid), None)
                if target is None:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Member was not found.", 404)
                if target[1] and not is_webmaster and sum(1 for item in rows if item[1]) <= 1:
                    conn.rollback()
                    conn.close()
                    raise StoreError("The council needs at least one webmaster.", 400)
                cur.execute(
                    "UPDATE members SET is_webmaster = %s WHERE membership_id = %s",
                    (bool(is_webmaster), memberid),
                )
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not update webmaster access.", 503) from exc
        member = self.get_member(memberid)
        if member is None:
            raise StoreError("Member was not found.", 404)
        return member

    def set_cloudflare(self, memberid: str, is_cloudflare: bool) -> dict:
        conn = self._open()
        if conn is None:
            with self._lock:
                target = next((item for item in self._members if item["membership_id"] == memberid), None)
                if target is None:
                    raise StoreError("Member was not found.", 404)
                if target.get("is_cloudflare") and not is_cloudflare:
                    holders = sum(1 for item in self._members if item.get("is_cloudflare"))
                    if holders <= 1:
                        raise StoreError("The council needs at least one Cloudflare role.", 400)
                target["is_cloudflare"] = bool(is_cloudflare)
            record = self._memory_member(memberid)
            if record is None:
                raise StoreError("Member was not found.", 404)
            return self._public_member(record)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT membership_id, is_cloudflare
                    FROM members
                    WHERE membership_id = %s OR is_cloudflare
                    ORDER BY membership_id
                    FOR UPDATE
                    """,
                    (memberid,),
                )
                rows = cur.fetchall()
                target = next((item for item in rows if item[0] == memberid), None)
                if target is None:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Member was not found.", 404)
                if target[1] and not is_cloudflare and sum(1 for item in rows if item[1]) <= 1:
                    conn.rollback()
                    conn.close()
                    raise StoreError("The council needs at least one Cloudflare role.", 400)
                cur.execute(
                    "UPDATE members SET is_cloudflare = %s WHERE membership_id = %s",
                    (bool(is_cloudflare), memberid),
                )
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not update Cloudflare access.", 503) from exc
        member = self.get_member(memberid)
        if member is None:
            raise StoreError("Member was not found.", 404)
        return member

    def get_email(self, memberid: str) -> str:
        conn = self._open()
        if conn is None:
            record = self._memory_member(memberid)
            if record is None:
                raise StoreError("Member was not found.", 404)
            return str(record.get("email") or "").strip()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT email FROM members WHERE membership_id = %s",
                    (memberid,),
                )
                row = cur.fetchone()
            conn.close()
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not load the personal email.", 503) from exc
        if row is None:
            raise StoreError("Member was not found.", 404)
        return str(row[0] or "").strip()

    def set_email(self, memberid: str, email: str) -> str:
        conn = self._open()
        if conn is None:
            with self._lock:
                target = next((item for item in self._members if item["membership_id"] == memberid), None)
                if target is None:
                    raise StoreError("Member was not found.", 404)
                target["email"] = email
            return email
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE members SET email = %s WHERE membership_id = %s",
                    (email or None, memberid),
                )
                if cur.rowcount != 1:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Member was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save the personal email.", 503) from exc
        return email

    def assign_roles(self, officer: list[dict], director: list[dict]) -> list[dict]:
        desired, managed = _role_plan(officer, director)
        conn = self._open()
        if conn is None:
            with self._lock:
                known = {item["membership_id"] for item in self._members}
                for memberid in desired:
                    if memberid not in known:
                        raise StoreError("Member was not found.", 404)
                for member in self._members:
                    memberid = member["membership_id"]
                    if memberid in desired:
                        member["title"] = desired[memberid]
                    elif member.get("title") in managed:
                        member["title"] = None
            return self.list_members()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT membership_id, title FROM members ORDER BY membership_id FOR UPDATE"
                )
                rows = cur.fetchall()
                known = {row[0] for row in rows}
                for memberid in desired:
                    if memberid not in known:
                        conn.rollback()
                        conn.close()
                        raise StoreError("Member was not found.", 404)
                for memberid, title in rows:
                    if memberid in desired:
                        new_title = desired[memberid]
                    elif title in managed:
                        new_title = None
                    else:
                        continue
                    if new_title != title:
                        cur.execute(
                            "UPDATE members SET title = %s WHERE membership_id = %s",
                            (new_title, memberid),
                        )
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save officer assignments.", 503) from exc
        return self.list_members()

    def _remember_member(
        self,
        memberid: str,
        hashed: str,
        name: str,
        cleaned: str | None,
        birth_month: int | None,
        birth_day: int | None,
    ) -> None:
        with self._lock:
            if cleaned:
                for member in self._members:
                    if member.get("title") == cleaned and member["membership_id"] != memberid:
                        member["title"] = None
            for member in self._members:
                if member["membership_id"] == memberid:
                    member["password_hash"] = hashed
                    member["display_name"] = name
                    member["title"] = cleaned
                    member["birth_month"] = birth_month
                    member["birth_day"] = birth_day
                    return
            self._members.append(
                {
                    "membership_id": memberid,
                    "password_hash": hashed,
                    "display_name": name,
                    "title": cleaned,
                    "is_admin": False,
                    "is_webmaster": False,
                    "is_cloudflare": False,
                    "birth_month": birth_month,
                    "birth_day": birth_day,
                    "honorary_life": False,
                    "phone": "",
                    "email": "",
                }
            )

    def create_member(
        self,
        memberid: str,
        password: str,
        display_name: str,
        title: str | None,
        birth_month: int | None = None,
        birth_day: int | None = None,
        pgk_period: str | None = None,
        pgk_note: str | None = None,
    ) -> dict:
        memberid, name, cleaned = _member_create_fields(memberid, password, display_name, title)
        month, day = _clean_birthday(birth_month, birth_day)
        honor_payload = _pgk_honor_payload(name, cleaned, pgk_period, pgk_note)
        hashed = hash_password(password)
        conn = self._open()
        if conn is None:
            with self._lock:
                if any(item["membership_id"] == memberid for item in self._members):
                    raise StoreError("That membership ID is already in use.", 409)
                if cleaned:
                    for member in self._members:
                        if member.get("title") == cleaned:
                            member["title"] = None
                self._members.append(
                    {
                        "membership_id": memberid,
                        "password_hash": hashed,
                        "display_name": name,
                        "title": cleaned,
                        "is_admin": False,
                        "is_webmaster": False,
                        "is_cloudflare": False,
                        "birth_month": month,
                        "birth_day": day,
                        "honorary_life": False,
                        "phone": "",
                        "email": "",
                    }
                )
                if honor_payload is not None:
                    _memory_save_past_gk(self, honor_payload, None, (0.0, 0.0, 1.0))
            record = self._memory_member(memberid)
            if record is None:
                raise StoreError("Could not create the member.", 503)
            return self._public_member(record)
        try:
            # A failed id repair aborts the Postgres transaction. Roll that
            # work back so the insert itself still runs.
            _guard_member_ids(conn)
            with conn.cursor() as cur:
                row = _insert_member_row(cur, memberid, hashed, name, cleaned, month, day)
                if honor_payload is not None:
                    _save_past_gk(
                        cur,
                        honor_payload,
                        _lock_past_gk(cur, honor_payload["name"], honor_payload["period"]),
                        None,
                        (0.0, 0.0, 1.0),
                    )
            conn.commit()
        except StoreError:
            _rollback(conn)
            raise
        except Exception as exc:
            _rollback(conn)
            if not _member_id_fault(exc):
                raise _member_create_error(exc) from exc
            conn = self._open()
            if conn is None:
                raise _member_create_error(exc) from exc
            try:
                with conn.cursor() as cur:
                    _ensure_member_id_default(cur)
                    _sync_member_id_sequence(cur)
                    row = _insert_member_row(cur, memberid, hashed, name, cleaned, month, day)
                    if honor_payload is not None:
                        _save_past_gk(
                            cur,
                            honor_payload,
                            _lock_past_gk(cur, honor_payload["name"], honor_payload["period"]),
                            None,
                            (0.0, 0.0, 1.0),
                        )
                conn.commit()
            except StoreError:
                _rollback(conn)
                raise
            except Exception as retry_exc:
                _rollback(conn)
                raise _member_create_error(retry_exc) from retry_exc
            else:
                try:
                    conn.close()
                except Exception:
                    pass
        else:
            try:
                conn.close()
            except Exception:
                pass
        if row is None:
            raise StoreError("Could not create the member.", 503)
        self._remember_member(memberid, hashed, name, cleaned, month, day)
        saved_title = row[2]
        if isinstance(saved_title, str):
            saved_title = saved_title.strip() or None
        return {
            "memberid": str(row[0]),
            "display_name": row[1],
            "title": saved_title,
            "is_admin": bool(row[3]),
            "is_webmaster": False,
            "is_cloudflare": False,
            "photo_url": None,
            "crop_x": 0.0,
            "crop_y": 0.0,
            "crop_scale": 1.0,
            "birth_month": month,
            "birth_day": day,
            "honorary_life": False,
        }

    def set_birthday(self, memberid: str, birth_month: int | None, birth_day: int | None) -> dict:
        memberid = memberid.strip()
        month, day = _clean_birthday(birth_month, birth_day)
        conn = self._open()
        if conn is None:
            with self._lock:
                target = next((item for item in self._members if item["membership_id"] == memberid), None)
                if target is None:
                    raise StoreError("Member was not found.", 404)
                target["birth_month"] = month
                target["birth_day"] = day
            record = self._memory_member(memberid)
            if record is None:
                raise StoreError("Member was not found.", 404)
            return self._public_member(record)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE members
                    SET birth_month = %s, birth_day = %s
                    WHERE membership_id = %s
                    RETURNING membership_id
                    """,
                    (month, day, memberid),
                )
                found = cur.fetchone()
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise _member_create_error(exc) if _birthday_fault(exc) else StoreError(
                "Could not save the birthday.", 503
            ) from exc
        if found is None:
            raise StoreError("Member was not found.", 404)
        with self._lock:
            for member in self._members:
                if member["membership_id"] == memberid:
                    member["birth_month"] = month
                    member["birth_day"] = day
                    break
        updated = self.get_member(memberid)
        if updated is None:
            raise StoreError("Member was not found.", 404)
        return updated

    def set_honorary(self, memberid: str, honorary_life: bool) -> dict:
        memberid = memberid.strip()
        flag = bool(honorary_life)
        conn = self._open()
        if conn is None:
            with self._lock:
                target = next((item for item in self._members if item["membership_id"] == memberid), None)
                if target is None:
                    raise StoreError("Member was not found.", 404)
                target["honorary_life"] = flag
            record = self._memory_member(memberid)
            if record is None:
                raise StoreError("Member was not found.", 404)
            return self._public_member(record)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE members
                    SET honorary_life = %s
                    WHERE membership_id = %s
                    RETURNING membership_id
                    """,
                    (flag, memberid),
                )
                found = cur.fetchone()
            if found is None:
                conn.rollback()
                conn.close()
                raise StoreError("Member was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not update Honorary Life Member.", 503) from exc
        with self._lock:
            for member in self._members:
                if member["membership_id"] == memberid:
                    member["honorary_life"] = flag
                    break
        updated = self.get_member(memberid)
        if updated is None:
            raise StoreError("Member was not found.", 404)
        return updated

    def list_honors(self) -> list[dict]:
        if self._cache_ready():
            cached = _cache_list(
                cache.get_honors(),
                ("id", "category", "name", "period", "note", "photo_url", "crop_x", "crop_y", "crop_scale"),
                ("photo_path", "file_path"),
                {
                    "id": "int",
                    "category": "str",
                    "name": "str",
                    "period": "str",
                    "note": "str",
                    "photo_url": "str?",
                    "crop_x": "num",
                    "crop_y": "num",
                    "crop_scale": "num",
                },
            )
            if cached is not None:
                return cached
        conn = self._open()
        if conn is None:
            with self._lock:
                rows = [dict(item) for item in self._honors]
            rows.sort(key=_honor_sort_key)
            return [_public_honor(item) for item in rows]
        try:
            with conn.cursor() as cur:
                cur.execute(
                    _HONOR_SELECT
                    + """
                    ORDER BY category, sort_year DESC, sort_month DESC NULLS LAST, id DESC
                    """
                )
                fetched = cur.fetchall()
            conn.close()
        except Exception as exc:
            log.warning("Honor list failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            raise StoreError("Could not load past honors.", 503) from exc
        rows = [_public_honor(_honor_from_row(row)) for row in fetched]
        cache.store_honors(rows)
        return rows

    def honor_file(self, honor_id: int) -> tuple[str, str] | None:
        row = self._honor_record(honor_id)
        if row is None or not row.get("photo_path"):
            return None
        path = str(row["photo_path"]).replace("\\", "/")
        if not path.startswith("backend/uploads/"):
            return None
        return path, row.get("photo_type") or "application/octet-stream"

    def create_honor(
        self,
        fields: dict,
        photo: tuple[str, str] | None,
        crop: tuple[float, float, float] | None = None,
    ) -> dict:
        payload = _honor_fields(fields)
        stored_crop = crop if crop is not None else (0.0, 0.0, 1.0)
        conn = self._open()
        if conn is None:
            with self._lock:
                honor_id = self._honor_seq
                self._honor_seq += 1
                self._honors.append(_memory_honor(honor_id, payload, photo, stored_crop))
            row = self._honor_record(honor_id)
            if row is None:
                raise StoreError("Could not save the honor.", 503)
            return _public_honor(row)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO honors
                      (category, name, period, sort_year, sort_month, note, photo_path, photo_type,
                       crop_x, crop_y, crop_scale)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    _honor_params(payload, photo, stored_crop),
                )
                honor_id = cur.fetchone()[0]
            conn.commit()
            conn.close()
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save the honor.", 503) from exc
        row = self._honor_record(honor_id)
        if row is None:
            raise StoreError("Could not save the honor.", 503)
        return _public_honor(row)

    def update_honor(
        self,
        honor_id: int,
        fields: dict,
        photo: tuple[str, str] | None,
        clear_photo: bool,
        crop: tuple[float, float, float] | None = None,
    ) -> dict:
        payload = _honor_fields(fields)
        previous = self._honor_record(honor_id)
        if previous is None:
            raise StoreError("Honor was not found.", 404)
        if photo is not None:
            next_crop = crop if crop is not None else (0.0, 0.0, 1.0)
        elif clear_photo:
            next_crop = (0.0, 0.0, 1.0)
        elif crop is not None:
            next_crop = crop
        else:
            next_crop = (
                float(previous.get("crop_x") or 0),
                float(previous.get("crop_y") or 0),
                float(previous.get("crop_scale") or 1),
            )
        conn = self._open()
        if conn is None:
            with self._lock:
                target = next((item for item in self._honors if item["id"] == honor_id), None)
                if target is None:
                    raise StoreError("Honor was not found.", 404)
                old_path = target.get("photo_path")
                target.update(payload)
                target["crop_x"], target["crop_y"], target["crop_scale"] = next_crop
                if photo is not None:
                    target["photo_path"] = photo[0]
                    target["photo_type"] = photo[1]
                elif clear_photo:
                    target["photo_path"] = None
                    target["photo_type"] = None
            if photo is not None or clear_photo:
                if old_path and old_path != (photo[0] if photo else None):
                    delete_stored_file(old_path)
            row = self._honor_record(honor_id)
            if row is None:
                raise StoreError("Honor was not found.", 404)
            return _public_honor(row)
        next_path = previous.get("photo_path")
        next_type = previous.get("photo_type")
        if photo is not None:
            next_path, next_type = photo
        elif clear_photo:
            next_path, next_type = None, None
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM honors WHERE id = %s FOR UPDATE", (honor_id,))
                if cur.fetchone() is None:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Honor was not found.", 404)
                cur.execute(
                    """
                    UPDATE honors
                    SET category = %s, name = %s, period = %s, sort_year = %s,
                        sort_month = %s, note = %s, photo_path = %s, photo_type = %s,
                        crop_x = %s, crop_y = %s, crop_scale = %s
                    WHERE id = %s
                    """,
                    (
                        *_honor_params(payload, (next_path, next_type) if next_path else None, next_crop),
                        honor_id,
                    ),
                )
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save the honor.", 503) from exc
        if (photo is not None or clear_photo) and previous.get("photo_path") and previous.get("photo_path") != next_path:
            delete_stored_file(str(previous["photo_path"]))
        row = self._honor_record(honor_id)
        if row is None:
            raise StoreError("Honor was not found.", 404)
        return _public_honor(row)

    def delete_honor(self, honor_id: int) -> None:
        previous = self._honor_record(honor_id)
        if previous is None:
            raise StoreError("Honor was not found.", 404)
        conn = self._open()
        if conn is None:
            with self._lock:
                self._honors = [item for item in self._honors if item["id"] != honor_id]
            if previous.get("photo_path"):
                delete_stored_file(str(previous["photo_path"]))
            return
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM honors WHERE id = %s", (honor_id,))
                if cur.rowcount != 1:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Honor was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not remove the honor.", 503) from exc
        if previous.get("photo_path"):
            delete_stored_file(str(previous["photo_path"]))

    def list_events(self) -> list[dict]:
        if self._cache_ready():
            cached = _cache_list(
                cache.get_json(cache.EVENTS),
                ("id", "title", "event_date", "event_time", "location", "description"),
                (),
                {
                    "id": "int",
                    "title": "str",
                    "event_date": "str",
                    "event_time": "str?",
                    "location": "str?",
                    "description": "str",
                },
            )
            if cached is not None:
                return cached
        conn = self._open()
        if conn is None:
            with self._lock:
                rows = [dict(item) for item in self._events]
            rows.sort(key=lambda item: (item["event_date"], item["id"]))
            return [_public_event(item) for item in rows]
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, event_date, event_time, location, description
                    FROM council_events
                    ORDER BY event_date, id
                    """
                )
                fetched = cur.fetchall()
            conn.close()
        except Exception as exc:
            log.warning("Event list failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            raise StoreError("Could not load events.", 503) from exc
        rows = [_public_event(_event_from_row(row)) for row in fetched]
        cache.set_json(cache.EVENTS, rows, cache.TTL_FRESH)
        return rows

    def create_event(self, fields: dict) -> dict:
        payload = _event_fields(fields)
        conn = self._open()
        if conn is None:
            with self._lock:
                event_id = self._event_seq
                self._event_seq += 1
                self._events.append({"id": event_id, **payload})
            row = self._event_record(event_id)
            if row is None:
                raise StoreError("Could not save the event.", 503)
            return _public_event(row)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO council_events
                      (title, event_date, event_time, location, description, sort_order)
                    VALUES (%s, %s, %s, %s, %s, 0)
                    RETURNING id
                    """,
                    (
                        payload["title"],
                        date.fromisoformat(payload["event_date"]),
                        payload["event_time"],
                        payload["location"],
                        payload["description"],
                    ),
                )
                event_id = cur.fetchone()[0]
            conn.commit()
            conn.close()
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save the event.", 503) from exc
        row = self._event_record(event_id)
        if row is None:
            raise StoreError("Could not save the event.", 503)
        return _public_event(row)

    def update_event(self, event_id: int, fields: dict) -> dict:
        payload = _event_fields(fields)
        if self._event_record(event_id) is None:
            raise StoreError("Event was not found.", 404)
        conn = self._open()
        if conn is None:
            with self._lock:
                target = next((item for item in self._events if item["id"] == event_id), None)
                if target is None:
                    raise StoreError("Event was not found.", 404)
                target.update(payload)
            row = self._event_record(event_id)
            if row is None:
                raise StoreError("Event was not found.", 404)
            return _public_event(row)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE council_events
                    SET title = %s, event_date = %s, event_time = %s, location = %s, description = %s
                    WHERE id = %s
                    """,
                    (
                        payload["title"],
                        date.fromisoformat(payload["event_date"]),
                        payload["event_time"],
                        payload["location"],
                        payload["description"],
                        event_id,
                    ),
                )
                if cur.rowcount != 1:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Event was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save the event.", 503) from exc
        row = self._event_record(event_id)
        if row is None:
            raise StoreError("Event was not found.", 404)
        return _public_event(row)

    def delete_event(self, event_id: int) -> None:
        if self._event_record(event_id) is None:
            raise StoreError("Event was not found.", 404)
        conn = self._open()
        if conn is None:
            with self._lock:
                self._events = [item for item in self._events if item["id"] != event_id]
            return
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM council_events WHERE id = %s", (event_id,))
                if cur.rowcount != 1:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Event was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not remove the event.", 503) from exc

    def list_documents(self, library: str) -> list[dict]:
        cleaned = normalize_library(library)
        if self._cache_ready():
            cached = _cache_list(
                cache.get_json(cache.document_key(cleaned)),
                ("id", "library", "title", "description", "original_name", "content_type", "uploaded_on"),
                ("file_path", "path"),
                {
                    "id": "int",
                    "library": "str",
                    "title": "str",
                    "description": "str",
                    "original_name": "str",
                    "content_type": "str",
                    "uploaded_on": "str",
                },
            )
            if cached is not None:
                return cached
        conn = self._open()
        if conn is None:
            with self._lock:
                rows = _sorted_documents(self._documents, cleaned)
            return [_public_document(item) for item in rows]
        try:
            with conn.cursor() as cur:
                cur.execute(
                    _DOCUMENT_SELECT
                    + """
                    WHERE library = %s
                    ORDER BY uploaded_at DESC, id DESC
                    """,
                    (cleaned,),
                )
                fetched = cur.fetchall()
            conn.close()
        except Exception as exc:
            log.warning("Document list failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            raise StoreError("Could not load documents.", 503) from exc
        rows = [_public_document(_document_from_row(row)) for row in fetched]
        cache.set_json(cache.document_key(cleaned), rows, cache.TTL_DOCUMENTS)
        return rows

    def document_file(self, document_id: int) -> tuple[str, str, str] | None:
        row = self._document_record(document_id)
        if row is None:
            return None
        path = str(row.get("file_path") or "").replace("\\", "/")
        if not document_path_allowed(str(row.get("library") or ""), path):
            return None
        return path, row.get("content_type") or "application/octet-stream", row.get("original_name") or "document"

    def create_document(
        self,
        library: str,
        title: str,
        description: str,
        file_path: str,
        original_name: str,
        content_type: str,
        uploaded_by: str | None,
    ) -> dict:
        cleaned = normalize_library(library)
        cleaned_title = clean_document_title(title)
        cleaned_description = clean_document_description(description)
        stored_path = str(file_path or "").replace("\\", "/")
        if not document_path_allowed(cleaned, stored_path):
            raise StoreError("Document path is not allowed.", 400)
        stored_name = str(original_name or "").strip()
        stored_type = str(content_type or "").strip().lower()
        if not stored_name or not stored_type:
            raise StoreError("Choose a document.", 400)
        uploaded_at = datetime.now(timezone.utc)
        conn = self._open()
        if conn is None:
            with self._lock:
                document_id = self._document_seq
                self._document_seq += 1
                self._documents.append(
                    {
                        "id": document_id,
                        "library": cleaned,
                        "title": cleaned_title,
                        "description": cleaned_description,
                        "file_path": stored_path,
                        "original_name": stored_name,
                        "content_type": stored_type,
                        "uploaded_by": uploaded_by,
                        "uploaded_at": uploaded_at,
                    }
                )
            return _public_document(
                {
                    "id": document_id,
                    "library": cleaned,
                    "title": cleaned_title,
                    "description": cleaned_description,
                    "original_name": stored_name,
                    "content_type": stored_type,
                    "uploaded_at": uploaded_at,
                }
            )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents (
                      library, title, description, file_path, original_name,
                      content_type, uploaded_by, uploaded_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, library, title, description, file_path,
                              original_name, content_type, uploaded_by, uploaded_at
                    """,
                    (
                        cleaned,
                        cleaned_title,
                        cleaned_description,
                        stored_path,
                        stored_name,
                        stored_type,
                        uploaded_by,
                        uploaded_at,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
            conn.close()
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save the document.", 503) from exc
        if row is None:
            raise StoreError("Could not save the document.", 503)
        return _public_document(_document_from_row(row))

    def delete_document(self, document_id: int) -> None:
        previous = self._document_record(document_id)
        if previous is None:
            raise StoreError("Document was not found.", 404)
        conn = self._open()
        if conn is None:
            with self._lock:
                self._documents = [item for item in self._documents if item["id"] != document_id]
            delete_stored_file(str(previous.get("file_path") or ""))
            return
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM documents WHERE id = %s", (document_id,))
                if cur.rowcount != 1:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Document was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not remove the document.", 503) from exc
        delete_stored_file(str(previous.get("file_path") or ""))

    def list_announcements(self) -> list[dict]:
        if self._cache_ready():
            cached = _cache_list(
                cache.get_json(cache.ANNOUNCEMENTS),
                ("id", "title", "summary", "body", "posted_on"),
                (),
                {
                    "id": "int",
                    "title": "str",
                    "summary": "str",
                    "body": "str",
                    "posted_on": "str",
                },
            )
            if cached is not None:
                return cached
        conn = self._open()
        if conn is None:
            with self._lock:
                rows = _sorted_announcements(self._announcements)
            return [_public_announcement(item) for item in rows]
        try:
            with conn.cursor() as cur:
                cur.execute(
                    _ANNOUNCEMENT_SELECT
                    + """
                    ORDER BY created_at DESC, id DESC
                    """
                )
                fetched = cur.fetchall()
            conn.close()
        except Exception as exc:
            log.warning("Announcement list failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            raise StoreError("Could not load announcements.", 503) from exc
        rows = [_public_announcement(_announcement_from_row(row)) for row in fetched]
        cache.set_json(cache.ANNOUNCEMENTS, rows, cache.TTL_FRESH)
        return rows

    def get_announcement(self, announcement_id: int) -> dict | None:
        conn = self._open()
        if conn is None:
            with self._lock:
                for item in self._announcements:
                    if item["id"] == announcement_id:
                        return _public_announcement(item)
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(_ANNOUNCEMENT_SELECT + " WHERE id = %s", (announcement_id,))
                row = cur.fetchone()
            conn.close()
        except Exception as exc:
            log.warning("Announcement lookup failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            raise StoreError("Could not load the announcement.", 503) from exc
        if row is None:
            return None
        return _public_announcement(_announcement_from_row(row))

    def create_announcement(self, title: str, summary: str, body: str, created_by: str | None) -> dict:
        cleaned_title = _announcement_value(clean_announcement_title, title)
        cleaned_summary = _announcement_value(clean_announcement_summary, summary)
        cleaned_body = _announcement_value(clean_announcement_body, body)
        actor = str(created_by or "").strip()[:32] or None
        created_at = datetime.now(timezone.utc)
        conn = self._open()
        if conn is None:
            with self._lock:
                announcement_id = self._announcement_seq
                self._announcement_seq += 1
                row = {
                    "id": announcement_id,
                    "title": cleaned_title,
                    "summary": cleaned_summary,
                    "body": cleaned_body,
                    "created_by": actor,
                    "created_at": created_at,
                    "updated_at": created_at,
                }
                self._announcements.append(row)
            return _public_announcement(row)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO announcements (
                      title, summary, body, created_by, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, title, summary, body, created_by, created_at, updated_at
                    """,
                    (cleaned_title, cleaned_summary, cleaned_body, actor, created_at, created_at),
                )
                row = cur.fetchone()
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save the announcement.", 503) from exc
        if row is None:
            raise StoreError("Could not save the announcement.", 503)
        return _public_announcement(_announcement_from_row(row))

    def update_announcement(self, announcement_id: int, title: str, summary: str, body: str) -> dict:
        cleaned_title = _announcement_value(clean_announcement_title, title)
        cleaned_summary = _announcement_value(clean_announcement_summary, summary)
        cleaned_body = _announcement_value(clean_announcement_body, body)
        updated_at = datetime.now(timezone.utc)
        conn = self._open()
        if conn is None:
            with self._lock:
                for item in self._announcements:
                    if item["id"] != announcement_id:
                        continue
                    item["title"] = cleaned_title
                    item["summary"] = cleaned_summary
                    item["body"] = cleaned_body
                    item["updated_at"] = updated_at
                    return _public_announcement(item)
            raise StoreError("Announcement was not found.", 404)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE announcements
                    SET title = %s, summary = %s, body = %s, updated_at = %s
                    WHERE id = %s
                    RETURNING id, title, summary, body, created_by, created_at, updated_at
                    """,
                    (cleaned_title, cleaned_summary, cleaned_body, updated_at, announcement_id),
                )
                row = cur.fetchone()
            if row is None:
                conn.rollback()
                conn.close()
                raise StoreError("Announcement was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save the announcement.", 503) from exc
        return _public_announcement(_announcement_from_row(row))

    def delete_announcement(self, announcement_id: int) -> None:
        conn = self._open()
        if conn is None:
            with self._lock:
                before = len(self._announcements)
                self._announcements = [item for item in self._announcements if item["id"] != announcement_id]
                if len(self._announcements) == before:
                    raise StoreError("Announcement was not found.", 404)
            return
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM announcements WHERE id = %s", (announcement_id,))
                if cur.rowcount != 1:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Announcement was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not remove the announcement.", 503) from exc

    def list_prayers(self, viewer_id: str | None) -> list[dict]:
        viewer = str(viewer_id or "").strip()
        if self._cache_ready():
            cached = _prayers_for_viewer(cache.get_json(cache.PRAYERS), viewer)
            if cached is not None:
                return cached
        conn = self._open()
        if conn is None:
            with self._lock:
                rows = _sorted_prayers(self._prayers)
                names = {
                    item.get("membership_id"): item.get("display_name")
                    for item in self._members
                }
            return [
                _public_prayer(item, viewer, names.get(item.get("member_id")))
                for item in rows
            ]
        try:
            with conn.cursor() as cur:
                cur.execute(
                    _PRAYER_SELECT
                    + """
                    ORDER BY p.created_at DESC, p.id DESC
                    """
                )
                fetched = cur.fetchall()
            conn.close()
        except Exception as exc:
            log.warning("Prayer list failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            raise StoreError("Could not load prayer requests.", 503) from exc
        public_rows = []
        stored_rows = []
        for row in fetched:
            item = _prayer_from_row(row)
            public_rows.append(_public_prayer(item, viewer, row[6]))
            stored_rows.append(_prayer_cache_row(item, row[6]))
        cache.set_json(cache.PRAYERS, stored_rows, cache.TTL_FRESH)
        return public_rows

    def create_prayer(self, title: str, body: str, member_id: str | None) -> dict:
        cleaned_title = _prayer_value(clean_prayer_title, title)
        cleaned_body = _prayer_value(clean_prayer_body, body)
        actor = str(member_id or "").strip()
        if not actor:
            raise StoreError("Sign in to add a prayer request.", 401)
        created_at = datetime.now(timezone.utc)
        conn = self._open()
        if conn is None:
            with self._lock:
                prayer_id = self._prayer_seq
                self._prayer_seq += 1
                row = {
                    "id": prayer_id,
                    "member_id": actor,
                    "title": cleaned_title,
                    "body": cleaned_body,
                    "created_at": created_at,
                    "updated_at": created_at,
                }
                self._prayers.append(row)
                author = self._memory_author(actor)
            return _public_prayer(row, actor, author)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO prayer_requests (
                      member_id, title, body, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, title, body, member_id, created_at, updated_at
                    """,
                    (actor, cleaned_title, cleaned_body, created_at, created_at),
                )
                stored = cur.fetchone()
                author = _author_name(cur, actor) if stored is not None else "Member"
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save the prayer request.", 503) from exc
        if stored is None:
            raise StoreError("Could not save the prayer request.", 503)
        return _public_prayer(_prayer_from_row(stored), actor, author)

    def update_prayer(self, prayer_id: int, title: str, body: str, member_id: str | None) -> dict:
        cleaned_title = _prayer_value(clean_prayer_title, title)
        cleaned_body = _prayer_value(clean_prayer_body, body)
        actor = str(member_id or "").strip()
        updated_at = datetime.now(timezone.utc)
        conn = self._open()
        if conn is None:
            with self._lock:
                for item in self._prayers:
                    if item["id"] != prayer_id:
                        continue
                    if str(item.get("member_id") or "") != actor:
                        raise StoreError("You can only change your own prayer request.", 403)
                    item["title"] = cleaned_title
                    item["body"] = cleaned_body
                    item["updated_at"] = updated_at
                    author = self._memory_author(item.get("member_id"))
                    return _public_prayer(item, actor, author)
            raise StoreError("Prayer request was not found.", 404)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT member_id FROM prayer_requests WHERE id = %s", (prayer_id,))
                found = cur.fetchone()
                if found is None:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Prayer request was not found.", 404)
                if str(found[0] or "") != actor:
                    conn.rollback()
                    conn.close()
                    raise StoreError("You can only change your own prayer request.", 403)
                cur.execute(
                    """
                    UPDATE prayer_requests
                    SET title = %s, body = %s, updated_at = %s
                    WHERE id = %s AND member_id = %s
                    RETURNING id, title, body, member_id, created_at, updated_at
                    """,
                    (cleaned_title, cleaned_body, updated_at, prayer_id, actor),
                )
                stored = cur.fetchone()
                author = _author_name(cur, actor) if stored is not None else "Member"
            if stored is None:
                conn.rollback()
                conn.close()
                raise StoreError("Prayer request was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save the prayer request.", 503) from exc
        return _public_prayer(_prayer_from_row(stored), actor, author)

    def delete_prayer(self, prayer_id: int, member_id: str | None, is_admin: bool) -> None:
        actor = str(member_id or "").strip()
        conn = self._open()
        if conn is None:
            with self._lock:
                match = next((item for item in self._prayers if item["id"] == prayer_id), None)
                if match is None:
                    raise StoreError("Prayer request was not found.", 404)
                owner = str(match.get("member_id") or "")
                if owner != actor and not is_admin:
                    raise StoreError("You can only remove your own prayer request.", 403)
                self._prayers = [item for item in self._prayers if item["id"] != prayer_id]
            return
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT member_id FROM prayer_requests WHERE id = %s", (prayer_id,))
                found = cur.fetchone()
                if found is None:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Prayer request was not found.", 404)
                owner = str(found[0] or "")
                if owner != actor and not is_admin:
                    conn.rollback()
                    conn.close()
                    raise StoreError("You can only remove your own prayer request.", 403)
                cur.execute("DELETE FROM prayer_requests WHERE id = %s", (prayer_id,))
                if cur.rowcount != 1:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Prayer request was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not remove the prayer request.", 503) from exc

    def list_nominations(self, member_id: str | None) -> dict:
        actor = str(member_id or "").strip()
        month_period, year_period = active_periods()
        conn = self._open()
        if conn is None:
            with self._lock:
                rows = [
                    dict(item)
                    for item in self._nominations
                    if str(item.get("member_id") or "") == actor
                    and in_active_period(str(item.get("category") or ""), str(item.get("period") or ""), month_period, year_period)
                ]
            rows.sort(key=lambda item: _nomination_order(item.get("category")))
            return _nomination_bundle(rows, month_period, year_period)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    _NOMINATION_SELECT
                    + """
                    WHERE member_id = %s
                      AND (
                        (category IN ('knight_month', 'family_month') AND period = %s)
                        OR (category IN ('knight_year', 'family_year') AND period = %s)
                      )
                    ORDER BY created_at DESC, id DESC
                    """,
                    (actor, month_period, year_period),
                )
                fetched = cur.fetchall()
            conn.close()
        except Exception as exc:
            log.warning("Nomination list failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            raise StoreError("Could not load nominations.", 503) from exc
        rows = [_nomination_from_row(row) for row in fetched]
        rows.sort(key=lambda item: _nomination_order(item.get("category")))
        return _nomination_bundle(rows, month_period, year_period)

    def nomination_results(self) -> dict:
        month_period, year_period = active_periods()
        if self._cache_ready():
            cached = _cached_tallies(cache.get_json(cache.NOMINATIONS))
            if cached is not None:
                return cached
        conn = self._open()
        if conn is None:
            with self._lock:
                rows = []
                for item in self._nominations:
                    if not in_active_period(
                        str(item.get("category") or ""),
                        str(item.get("period") or ""),
                        month_period,
                        year_period,
                    ):
                        continue
                    copied = dict(item)
                    copied["voter_name"] = self._memory_author(item.get("member_id"))
                    rows.append(copied)
            return build_results(rows, month_period, year_period)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT n.id, n.member_id, n.category, n.nominee_member_id, n.nominee_name,
                           n.reason, n.period, n.created_at,
                           COALESCE(NULLIF(btrim(m.display_name), ''), 'Member')
                    FROM nominations n
                    LEFT JOIN members m ON m.membership_id = n.member_id
                    WHERE (n.category IN ('knight_month', 'family_month') AND n.period = %s)
                       OR (n.category IN ('knight_year', 'family_year') AND n.period = %s)
                    """,
                    (month_period, year_period),
                )
                fetched = cur.fetchall()
            conn.close()
        except Exception as exc:
            log.warning("Nomination results failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            raise StoreError("Could not load nomination results.", 503) from exc
        rows = []
        for row in fetched:
            item = _nomination_from_row(row)
            item["voter_name"] = row[8]
            rows.append(item)
        payload = build_results(rows, month_period, year_period)
        cache.set_json(cache.NOMINATIONS, payload, cache.TTL_FRESH)
        return payload

    def save_nomination(
        self,
        category: str,
        nominee_member_id: str,
        nominee_name: str,
        reason: str,
        member_id: str | None,
    ) -> dict:
        chosen = str(category or "").strip()
        if chosen not in CATEGORY_ORDER:
            raise StoreError("Choose a category.", 400)
        try:
            cleaned_reason = clean_nomination_reason(reason)
            period = period_for(chosen)
        except ValueError as exc:
            raise StoreError(str(exc), 400) from exc
        actor = str(member_id or "").strip()
        if not actor:
            raise StoreError("Sign in to submit a nomination.", 401)
        created_at = datetime.now(timezone.utc)
        conn = self._open()
        if conn is None:
            with self._lock:
                try:
                    nominee_id, cleaned_name = resolve_nominee(
                        chosen,
                        nominee_member_id,
                        nominee_name,
                        self._lookup_member_name,
                    )
                except ValueError as exc:
                    raise StoreError(str(exc), 400) from exc
                for item in self._nominations:
                    if (
                        str(item.get("member_id") or "") == actor
                        and item.get("category") == chosen
                        and str(item.get("period") or "") == period
                    ):
                        item["nominee_member_id"] = nominee_id or ""
                        item["nominee_name"] = cleaned_name
                        item["reason"] = cleaned_reason
                        return _public_nomination(item)
                nomination_id = self._nomination_seq
                self._nomination_seq += 1
                row = {
                    "id": nomination_id,
                    "member_id": actor,
                    "category": chosen,
                    "nominee_member_id": nominee_id or "",
                    "nominee_name": cleaned_name,
                    "reason": cleaned_reason,
                    "period": period,
                    "created_at": created_at,
                }
                self._nominations.append(row)
            return _public_nomination(row)
        try:
            with conn.cursor() as cur:
                def lookup(wanted: str, cursor=cur) -> str | None:
                    cursor.execute(
                        "SELECT display_name FROM members WHERE membership_id = %s",
                        (wanted,),
                    )
                    found = cursor.fetchone()
                    if found is None:
                        return None
                    return found[0]

                try:
                    nominee_id, cleaned_name = resolve_nominee(
                        chosen,
                        nominee_member_id,
                        nominee_name,
                        lookup,
                    )
                except ValueError as exc:
                    raise StoreError(str(exc), 400) from exc
                cur.execute(
                    """
                    INSERT INTO nominations (
                      member_id, category, nominee_member_id, nominee_name, reason, period, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT ON CONSTRAINT nominations_one_per_period
                    DO UPDATE SET
                      nominee_member_id = EXCLUDED.nominee_member_id,
                      nominee_name = EXCLUDED.nominee_name,
                      reason = EXCLUDED.reason
                    RETURNING id, member_id, category, nominee_member_id, nominee_name, reason, period, created_at
                    """,
                    (actor, chosen, nominee_id, cleaned_name, cleaned_reason, period, created_at),
                )
                stored = cur.fetchone()
            conn.commit()
            conn.close()
        except StoreError:
            _rollback(conn)
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save the nomination.", 503) from exc
        if stored is None:
            raise StoreError("Could not save the nomination.", 503)
        return _public_nomination(_nomination_from_row(stored))

    def withdraw_nomination(self, nomination_id: int, member_id: str | None) -> None:
        actor = str(member_id or "").strip()
        conn = self._open()
        if conn is None:
            with self._lock:
                match = next((item for item in self._nominations if item["id"] == nomination_id), None)
                if match is None:
                    raise StoreError("Nomination was not found.", 404)
                if str(match.get("member_id") or "") != actor:
                    raise StoreError("You can only withdraw your own nomination.", 403)
                self._nominations = [item for item in self._nominations if item["id"] != nomination_id]
            return
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT member_id FROM nominations WHERE id = %s", (nomination_id,))
                found = cur.fetchone()
                if found is None:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Nomination was not found.", 404)
                if str(found[0] or "") != actor:
                    conn.rollback()
                    conn.close()
                    raise StoreError("You can only withdraw your own nomination.", 403)
                cur.execute(
                    "DELETE FROM nominations WHERE id = %s AND member_id = %s",
                    (nomination_id, actor),
                )
                if cur.rowcount != 1:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Nomination was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not withdraw the nomination.", 503) from exc

    def _lookup_member_name(self, member_id: str) -> str | None:
        wanted = str(member_id or "").strip()
        for item in self._members:
            if item.get("membership_id") == wanted:
                return item.get("display_name")
        return None

    def _memory_author(self, member_id: str | None) -> str:
        wanted = str(member_id or "").strip()
        for item in self._members:
            if item.get("membership_id") == wanted:
                return display_person_name(item.get("display_name"))
        return "Member"

    def _document_record(self, document_id: int) -> dict | None:
        conn = self._open()
        if conn is None:
            with self._lock:
                for item in self._documents:
                    if item["id"] == document_id:
                        return dict(item)
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(_DOCUMENT_SELECT + " WHERE id = %s", (document_id,))
                row = cur.fetchone()
            conn.close()
        except Exception as exc:
            log.warning("Document lookup failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            raise StoreError("Could not load the document.", 503) from exc
        if row is None:
            return None
        return _document_from_row(row)

    def _honor_record(self, honor_id: int) -> dict | None:
        conn = self._open()
        if conn is None:
            with self._lock:
                for item in self._honors:
                    if item["id"] == honor_id:
                        return dict(item)
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(_HONOR_SELECT + " WHERE id = %s", (honor_id,))
                row = cur.fetchone()
            conn.close()
        except Exception as exc:
            log.warning("Honor lookup failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            return None
        if row is None:
            return None
        return _honor_from_row(row)

    def _event_record(self, event_id: int) -> dict | None:
        conn = self._open()
        if conn is None:
            with self._lock:
                for item in self._events:
                    if item["id"] == event_id:
                        return dict(item)
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, event_date, event_time, location, description
                    FROM council_events
                    WHERE id = %s
                    """,
                    (event_id,),
                )
                row = cur.fetchone()
            conn.close()
        except Exception as exc:
            log.warning("Event lookup failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            return None
        if row is None:
            return None
        return _event_from_row(row)

    def list_images(self, purpose: str | None = "library") -> list[dict]:
        conn = self._open()
        if conn is None:
            with self._lock:
                rows = [dict(image) for image in self._images if purpose is None or image["purpose"] == purpose]
            return [_public_image(image) for image in _sorted_images(rows)]
        try:
            with conn.cursor() as cur:
                if purpose is None:
                    cur.execute(_IMAGE_SELECT + " ORDER BY CASE WHEN slot IS NULL THEN 1 ELSE 0 END, slot, id")
                else:
                    cur.execute(
                        _IMAGE_SELECT + " WHERE purpose = %s ORDER BY CASE WHEN slot IS NULL THEN 1 ELSE 0 END, slot, id",
                        (purpose,),
                    )
                fetched = cur.fetchall()
            conn.close()
        except Exception as exc:
            log.warning("Image list failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            raise StoreError("Could not load images.", 503) from exc
        return [_public_image(_image_from_row(row)) for row in fetched]

    def public_slots(self) -> dict:
        images = self.list_images("library")
        by_slot = {image["slot"]: image for image in images if image.get("slot")}
        slides = []
        for slot in ("carousel.1", "carousel.2", "carousel.3", "carousel.4"):
            image = by_slot.get(slot)
            slides.append(_slot_payload(slot, image))
        recognition = [_slot_payload(slot, by_slot.get(slot)) for slot in RECOG_SLOTS]
        logo = by_slot.get("logo")
        return {
            "logo": logo["url"] if logo else None,
            "slides": slides,
            "recognition": recognition,
        }

    def get_image(self, image_id: int) -> dict | None:
        conn = self._open()
        if conn is None:
            with self._lock:
                for image in self._images:
                    if image["id"] == image_id:
                        return dict(image)
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(_IMAGE_SELECT + " WHERE id = %s", (image_id,))
                row = cur.fetchone()
            conn.close()
        except Exception as exc:
            log.warning("Image lookup failed: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
            return None
        if row is None:
            return None
        return _image_from_row(row)

    def add_library_image(
        self,
        path: str,
        original_name: str,
        content_type: str,
        owner: str | None,
        crop: tuple[float, float, float] | None = None,
    ) -> dict:
        stored_crop = crop if crop is not None else (0.0, 0.0, 1.0)
        return self._insert_image(path, original_name, content_type, "library", None, owner, stored_crop)

    def replace_image(
        self,
        image_id: int,
        path: str,
        original_name: str,
        content_type: str,
        crop: tuple[float, float, float] | None = None,
    ) -> dict:
        current = self.get_image(image_id)
        if current is None:
            delete_stored_file(path)
            raise StoreError("Image was not found.", 404)
        if current["purpose"] == "profile":
            delete_stored_file(path)
            raise StoreError("Profile photos are replaced from Settings.", 400)
        crop_x, crop_y, crop_scale = crop if crop is not None else (0.0, 0.0, 1.0)
        conn = self._open()
        if conn is None:
            with self._lock:
                for image in self._images:
                    if image["id"] == image_id:
                        old = image["path"]
                        image["path"] = path
                        image["original_name"] = original_name
                        image["content_type"] = content_type
                        image["crop_x"] = crop_x
                        image["crop_y"] = crop_y
                        image["crop_scale"] = crop_scale
                        delete_stored_file(old)
                        return _public_image(image)
            delete_stored_file(path)
            raise StoreError("Image was not found.", 404)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE images
                    SET path = %s, original_name = %s, content_type = %s,
                        crop_x = %s, crop_y = %s, crop_scale = %s
                    WHERE id = %s AND purpose <> 'profile'
                    """,
                    (path, original_name, content_type, crop_x, crop_y, crop_scale, image_id),
                )
                if cur.rowcount != 1:
                    conn.rollback()
                    conn.close()
                    delete_stored_file(path)
                    raise StoreError("Image was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            delete_stored_file(path)
            raise StoreError("Could not replace the image.", 503) from exc
        delete_stored_file(current["path"])
        updated = self.get_image(image_id)
        if updated is None:
            raise StoreError("Image was not found.", 404)
        return _public_image(updated)

    def update_library_crop(self, image_id: int, crop: tuple[float, float, float]) -> dict:
        crop_x, crop_y, crop_scale = crop
        current = self.get_image(image_id)
        if current is None:
            raise StoreError("Image was not found.", 404)
        if current["purpose"] == "profile":
            raise StoreError("Profile photos are adjusted from Settings.", 400)
        conn = self._open()
        if conn is None:
            with self._lock:
                for image in self._images:
                    if image["id"] == image_id:
                        if image["purpose"] == "profile":
                            raise StoreError("Profile photos are adjusted from Settings.", 400)
                        image["crop_x"] = crop_x
                        image["crop_y"] = crop_y
                        image["crop_scale"] = crop_scale
                        return _public_image(image)
            raise StoreError("Image was not found.", 404)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE images
                    SET crop_x = %s, crop_y = %s, crop_scale = %s
                    WHERE id = %s AND purpose <> 'profile'
                    """,
                    (crop_x, crop_y, crop_scale, image_id),
                )
                if cur.rowcount != 1:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Image was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save the viewing angle.", 503) from exc
        updated = self.get_image(image_id)
        if updated is None:
            raise StoreError("Image was not found.", 404)
        return _public_image(updated)

    def delete_image(self, image_id: int) -> None:
        current = self.get_image(image_id)
        if current is None:
            raise StoreError("Image was not found.", 404)
        if current["purpose"] == "profile":
            raise StoreError("Remove a profile photo from that member's settings.", 400)
        conn = self._open()
        if conn is None:
            with self._lock:
                self._images = [image for image in self._images if image["id"] != image_id]
            delete_stored_file(current["path"])
            return
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM images WHERE id = %s AND purpose <> 'profile'", (image_id,))
                if cur.rowcount != 1:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Image was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not remove the image.", 503) from exc
        delete_stored_file(current["path"])

    def assign_slot(self, image_id: int, slot: str | None) -> dict:
        current = self.get_image(image_id)
        if current is None:
            raise StoreError("Image was not found.", 404)
        if current["purpose"] == "profile":
            raise StoreError("Profile photos are not used in site slots.", 400)
        conn = self._open()
        if conn is None:
            with self._lock:
                if slot:
                    for image in self._images:
                        if image["slot"] == slot and image["id"] != image_id:
                            image["slot"] = None
                for image in self._images:
                    if image["id"] == image_id:
                        image["slot"] = slot
                        return _public_image(image)
            raise StoreError("Image was not found.", 404)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT purpose FROM images WHERE id = %s FOR UPDATE", (image_id,))
                row = cur.fetchone()
                if row is None:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Image was not found.", 404)
                if row[0] == "profile":
                    conn.rollback()
                    conn.close()
                    raise StoreError("Profile photos are not used in site slots.", 400)
                if slot:
                    cur.execute(
                        "UPDATE images SET slot = NULL WHERE slot = %s AND id <> %s",
                        (slot, image_id),
                    )
                cur.execute("UPDATE images SET slot = %s WHERE id = %s", (slot, image_id))
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not update the image slot.", 503) from exc
        updated = self.get_image(image_id)
        if updated is None:
            raise StoreError("Image was not found.", 404)
        return _public_image(updated)

    def set_profile_image(
        self,
        memberid: str,
        path: str,
        original_name: str,
        content_type: str,
        crop: tuple[float, float, float] = (0, 0, 1),
    ) -> dict:
        crop_x, crop_y, crop_scale = crop
        if self.get_member(memberid) is None:
            delete_stored_file(path)
            raise StoreError("Member was not found.", 404)
        conn = self._open()
        if conn is None:
            with self._lock:
                old = None
                for image in self._images:
                    if image["purpose"] == "profile" and image["owner_membership_id"] == memberid:
                        old = image["path"]
                        image["path"] = path
                        image["original_name"] = original_name
                        image["content_type"] = content_type
                        image["crop_x"] = crop_x
                        image["crop_y"] = crop_y
                        image["crop_scale"] = crop_scale
                        break
                else:
                    self._images.append(
                        {
                            "id": self._image_seq,
                            "path": path,
                            "original_name": original_name,
                            "content_type": content_type,
                            "purpose": "profile",
                            "slot": None,
                            "owner_membership_id": memberid,
                            "crop_x": crop_x,
                            "crop_y": crop_y,
                            "crop_scale": crop_scale,
                        }
                    )
                    self._image_seq += 1
            if old:
                delete_stored_file(old)
            record = self._memory_member(memberid)
            if record is None:
                raise StoreError("Member was not found.", 404)
            return self._public_member(record)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, path FROM images
                    WHERE owner_membership_id = %s AND purpose = 'profile'
                    FOR UPDATE
                    """,
                    (memberid,),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """
                        UPDATE images
                        SET path = %s,
                            original_name = %s,
                            content_type = %s,
                            crop_x = %s,
                            crop_y = %s,
                            crop_scale = %s
                        WHERE id = %s
                        """,
                        (path, original_name, content_type, crop_x, crop_y, crop_scale, existing[0]),
                    )
                    old_path = existing[1]
                else:
                    cur.execute(
                        """
                        INSERT INTO images
                          (path, original_name, content_type, purpose, slot,
                           owner_membership_id, crop_x, crop_y, crop_scale)
                        VALUES (%s, %s, %s, 'profile', NULL, %s, %s, %s, %s)
                        """,
                        (path, original_name, content_type, memberid, crop_x, crop_y, crop_scale),
                    )
                    old_path = None
            conn.commit()
            conn.close()
        except Exception as exc:
            _rollback(conn)
            delete_stored_file(path)
            raise StoreError("Could not save the profile photo.", 503) from exc
        if old_path:
            delete_stored_file(old_path)
        member = self.get_member(memberid)
        if member is None:
            raise StoreError("Member was not found.", 404)
        return member

    def update_profile_crop(self, memberid: str, crop: tuple[float, float, float]) -> dict:
        crop_x, crop_y, crop_scale = crop
        conn = self._open()
        if conn is None:
            with self._lock:
                photo = _profile_in(self._images, memberid)
                if photo is None:
                    raise StoreError("Upload a profile photo first.", 404)
                photo["crop_x"] = crop_x
                photo["crop_y"] = crop_y
                photo["crop_scale"] = crop_scale
            record = self._memory_member(memberid)
            if record is None:
                raise StoreError("Member was not found.", 404)
            return self._public_member(record)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE images
                    SET crop_x = %s, crop_y = %s, crop_scale = %s
                    WHERE owner_membership_id = %s AND purpose = 'profile'
                    """,
                    (crop_x, crop_y, crop_scale, memberid),
                )
                if cur.rowcount != 1:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Upload a profile photo first.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not save the viewing angle.", 503) from exc
        member = self.get_member(memberid)
        if member is None:
            raise StoreError("Member was not found.", 404)
        return member

    def clear_profile_image(self, memberid: str) -> dict:
        conn = self._open()
        if conn is None:
            with self._lock:
                kept = []
                old = None
                for image in self._images:
                    if image["purpose"] == "profile" and image["owner_membership_id"] == memberid:
                        old = image["path"]
                        continue
                    kept.append(image)
                self._images = kept
            if old:
                delete_stored_file(old)
            record = self._memory_member(memberid)
            if record is None:
                raise StoreError("Member was not found.", 404)
            return self._public_member(record)
        old_path = None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM images
                    WHERE owner_membership_id = %s AND purpose = 'profile'
                    RETURNING path
                    """,
                    (memberid,),
                )
                row = cur.fetchone()
                if row:
                    old_path = row[0]
                cur.execute("SELECT 1 FROM members WHERE membership_id = %s", (memberid,))
                if cur.fetchone() is None:
                    conn.rollback()
                    conn.close()
                    raise StoreError("Member was not found.", 404)
            conn.commit()
            conn.close()
        except StoreError:
            raise
        except Exception as exc:
            _rollback(conn)
            raise StoreError("Could not remove the profile photo.", 503) from exc
        if old_path:
            delete_stored_file(old_path)
        member = self.get_member(memberid)
        if member is None:
            raise StoreError("Member was not found.", 404)
        return member

    def _insert_image(
        self,
        path: str,
        original_name: str,
        content_type: str,
        purpose: str,
        slot: str | None,
        owner: str | None,
        crop: tuple[float, float, float] = (0, 0, 1),
    ) -> dict:
        crop_x, crop_y, crop_scale = crop
        conn = self._open()
        if conn is None:
            with self._lock:
                image = {
                    "id": self._image_seq,
                    "path": path,
                    "original_name": original_name,
                    "content_type": content_type,
                    "purpose": purpose,
                    "slot": slot,
                    "owner_membership_id": owner,
                    "crop_x": crop_x,
                    "crop_y": crop_y,
                    "crop_scale": crop_scale,
                }
                self._image_seq += 1
                self._images.append(image)
                return _public_image(image)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO images
                      (path, original_name, content_type, purpose, slot, owner_membership_id,
                       crop_x, crop_y, crop_scale)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (path, original_name, content_type, purpose, slot, owner, crop_x, crop_y, crop_scale),
                )
                image_id = cur.fetchone()[0]
            conn.commit()
            conn.close()
        except Exception as exc:
            _rollback(conn)
            delete_stored_file(path)
            raise StoreError("Could not save the image.", 503) from exc
        image = self.get_image(image_id)
        if image is None:
            raise StoreError("Could not save the image.", 503)
        return _public_image(image)

    def get_page(self, slug: str) -> dict:
        if slug not in PAGES:
            raise KeyError(slug)
        if self._cache_ready():
            cached = _cached_page(slug, cache.get_json(cache.page_key(slug)))
            if cached is not None:
                with self._lock:
                    if not self._prefer_memory:
                        self._memory[slug] = deepcopy(cached["blocks"])
                        return cached
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
            if row["key"] in _RETIRED_MEMBER_LINK_KEYS:
                continue
            merged[row["key"]] = row
        blocks = sorted(merged.values(), key=lambda block: (block["sort_order"], block["key"]))
        with self._lock:
            self._memory[slug] = deepcopy(blocks)
        payload = self._page_payload(slug, blocks)
        cache.store_page(slug, payload)
        return payload

    def save_member(self, blocks: list[dict]) -> dict:
        normalized = self._normalize(blocks)
        with self._lock:
            current = {
                block["key"]: deepcopy(block)
                for block in self._memory["member"]
                if block["key"] not in _RETIRED_MEMBER_LINK_KEYS
            }
            for block in normalized:
                if block["key"] in _RETIRED_MEMBER_LINK_KEYS:
                    continue
                current[block["key"]] = block
            ordered = sorted(current.values(), key=lambda block: (block["sort_order"], block["key"]))
            self._memory["member"] = ordered
            prefer_memory = self._prefer_memory
        if not prefer_memory and not self._save_db(ordered):
            with self._lock:
                self._prefer_memory = True
            prefer_memory = True
        if prefer_memory:
            return self._page_payload("member", ordered)
        cache.drop_page("member")
        return self.get_page("member")

    def _cache_ready(self) -> bool:
        with self._lock:
            return not self._prefer_memory

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


_IMAGE_SELECT = """
SELECT id, path, original_name, content_type, purpose, slot, owner_membership_id,
       crop_x, crop_y, crop_scale
FROM images
"""

_HONOR_SELECT = """
SELECT id, category, name, period, sort_year, sort_month, note, photo_path, photo_type,
       crop_x, crop_y, crop_scale
FROM honors
"""

_BIRTHDAY_CHECK = """
CHECK (
  (birth_month IS NULL AND birth_day IS NULL)
  OR (
    birth_month BETWEEN 1 AND 12
    AND birth_day BETWEEN 1 AND 31
    AND (
      (birth_month = 2 AND birth_day <= 29)
      OR (birth_month IN (4, 6, 9, 11) AND birth_day <= 30)
      OR (birth_month IN (1, 3, 5, 7, 8, 10, 12) AND birth_day <= 31)
    )
  )
)
"""

_MEMBER_COLUMNS = """
CREATE TABLE IF NOT EXISTS members (
  id SERIAL PRIMARY KEY,
  membership_id TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  title TEXT,
  is_admin BOOLEAN NOT NULL DEFAULT FALSE,
  is_webmaster BOOLEAN NOT NULL DEFAULT FALSE,
  is_cloudflare BOOLEAN NOT NULL DEFAULT FALSE,
  birth_month SMALLINT,
  birth_day SMALLINT,
  honorary_life BOOLEAN NOT NULL DEFAULT FALSE,
  phone TEXT,
  email TEXT
)
"""

_MEMBER_SELECT = """
SELECT m.membership_id, m.password_hash, m.display_name, m.title, m.is_admin,
       i.id, i.path, i.crop_x, i.crop_y, i.crop_scale,
       m.birth_month, m.birth_day, m.honorary_life, m.phone, m.email,
       m.is_webmaster, m.is_cloudflare
FROM members m
LEFT JOIN images i
  ON i.owner_membership_id = m.membership_id AND i.purpose = 'profile'
"""


def _rollback(conn) -> None:
    try:
        conn.rollback()
        conn.close()
    except Exception:
        pass


def _memory_contact(membership_id: str) -> dict:
    honorary, phone, email = directory_fields(membership_id)
    return {
        "honorary_life": honorary,
        "phone": phone or "",
        "email": email or "",
    }


def _memory_member_rows(hashed: str) -> list[dict]:
    rows = [
        {
            "membership_id": TEST_MEMBER_ID,
            "password_hash": hashed,
            "display_name": TEST_MEMBER_NAME,
            "title": TEST_MEMBER_TITLE,
            "is_admin": True,
            "is_webmaster": True,
            "is_cloudflare": True,
            "birth_month": None,
            "birth_day": None,
            **_memory_contact(TEST_MEMBER_ID),
        },
        {
            "membership_id": SAMPLE_MEMBER_ID,
            "password_hash": hashed,
            "display_name": SAMPLE_MEMBER_NAME,
            "title": None,
            "is_admin": False,
            "is_webmaster": False,
            "is_cloudflare": False,
            "birth_month": None,
            "birth_day": None,
            **_memory_contact(SAMPLE_MEMBER_ID),
        },
    ]
    for member in MEMBER_SEED:
        rows.append(
            {
                "membership_id": member.membership_id,
                "password_hash": hashed,
                "display_name": member.display_name,
                "title": member.title,
                "is_admin": member.is_admin,
                "is_webmaster": False,
                "is_cloudflare": False,
                "birth_month": member.birth_month,
                "birth_day": member.birth_day,
                **_memory_contact(member.membership_id),
            }
        )
    return rows


def _seed_image_rows() -> list[dict]:
    rows = []
    for index, (path, original, content_type, slot) in enumerate(SEED_IMAGES, start=1):
        rows.append(
            {
                "id": index,
                "path": path,
                "original_name": original,
                "content_type": content_type,
                "purpose": "library",
                "slot": slot,
                "owner_membership_id": None,
                "crop_x": 0,
                "crop_y": 0,
                "crop_scale": 1,
            }
        )
    next_id = len(rows) + 1
    for member in MEMBER_SEED:
        rows.append(
            {
                "id": next_id,
                "path": member_photo_path(member.membership_id),
                "original_name": f"{member.membership_id}.png",
                "content_type": "image/png",
                "purpose": "profile",
                "slot": None,
                "owner_membership_id": member.membership_id,
                "crop_x": 0,
                "crop_y": 0,
                "crop_scale": 1,
            }
        )
        next_id += 1
    return rows


def _profile_in(images: list[dict], memberid: str) -> dict | None:
    for image in images:
        if image["purpose"] == "profile" and image["owner_membership_id"] == memberid:
            return image
    return None


def _birthday_number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number


def _clean_birthday(month, day) -> tuple[int | None, int | None]:
    if month is None and day is None:
        return None, None
    if month is None or day is None or isinstance(month, bool) or isinstance(day, bool):
        raise StoreError("Choose a valid birthday.", 400)
    if not isinstance(month, int) or not isinstance(day, int):
        raise StoreError("Choose a valid birthday.", 400)
    if month < 1 or month > 12:
        raise StoreError("Choose a valid birthday.", 400)
    limit = 29 if month == 2 else 30 if month in (4, 6, 9, 11) else 31
    if day < 1 or day > limit:
        raise StoreError("Choose a valid birthday.", 400)
    return month, day


def _record_from_row(row) -> dict:
    return {
        "membership_id": row[0],
        "password_hash": row[1],
        "display_name": row[2],
        "title": row[3],
        "is_admin": bool(row[4]),
        "photo_id": row[5],
        "photo_path": row[6],
        "crop_x": float(row[7]) if len(row) > 7 and row[7] is not None else 0,
        "crop_y": float(row[8]) if len(row) > 8 and row[8] is not None else 0,
        "crop_scale": float(row[9]) if len(row) > 9 and row[9] is not None else 1,
        "birth_month": _birthday_number(row[10]) if len(row) > 10 else None,
        "birth_day": _birthday_number(row[11]) if len(row) > 11 else None,
        "honorary_life": bool(row[12]) if len(row) > 12 and row[12] is not None else False,
        "phone": str(row[13] or "").strip() if len(row) > 13 else "",
        "email": str(row[14] or "").strip() if len(row) > 14 else "",
        "is_webmaster": bool(row[15]) if len(row) > 15 and row[15] is not None else False,
        "is_cloudflare": bool(row[16]) if len(row) > 16 and row[16] is not None else False,
    }


def _image_from_row(row) -> dict:
    return {
        "id": row[0],
        "path": row[1],
        "original_name": row[2],
        "content_type": row[3],
        "purpose": row[4],
        "slot": row[5],
        "owner_membership_id": row[6],
        "crop_x": float(row[7]) if len(row) > 7 and row[7] is not None else 0,
        "crop_y": float(row[8]) if len(row) > 8 and row[8] is not None else 0,
        "crop_scale": float(row[9]) if len(row) > 9 and row[9] is not None else 1,
    }


def _public_image(image: dict) -> dict:
    return {
        "id": image["id"],
        "url": public_url(int(image["id"]), image["path"]),
        "original_name": image["original_name"],
        "content_type": image["content_type"],
        "purpose": image["purpose"],
        "slot": image.get("slot"),
        "owner_membership_id": image.get("owner_membership_id"),
        "crop_x": float(image.get("crop_x") or 0),
        "crop_y": float(image.get("crop_y") or 0),
        "crop_scale": float(image.get("crop_scale") or 1),
    }


def _sorted_images(images: list[dict]) -> list[dict]:
    return sorted(images, key=lambda image: (image.get("slot") is None, image.get("slot") or "", image["id"]))


MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
HONOR_CATEGORIES = (
    "knight_month",
    "family_month",
    "knight_year",
    "family_year",
    "past_gk",
)
MONTH_HONORS = frozenset({"knight_month", "family_month"})
YEAR_HONORS = frozenset({"knight_year", "family_year"})
_PGK_PERIOD = re.compile(r"^(\d{4})(?:[–-](\d{2}))?$")
_CATEGORY_ORDER = {name: index for index, name in enumerate(HONOR_CATEGORIES)}


def _member_create_fields(memberid: str, password: str, display_name: str, title: str | None):
    cleaned_id = str(memberid or "").strip()
    if not cleaned_id.isdigit() or len(cleaned_id) > 32:
        raise StoreError("Membership ID must contain only digits.", 400)
    if len(password) < 8 or len(password.encode("utf-8")) > 72:
        raise StoreError("Password must be 8 to 72 characters.", 400)
    name = " ".join(str(display_name or "").split())
    if not name or len(name) > 80:
        raise StoreError("Enter the member's name.", 400)
    try:
        cleaned = normalize_title(title)
    except ValueError as exc:
        raise StoreError(str(exc), 400) from exc
    return cleaned_id, name, cleaned


def _require_year(value) -> int:
    try:
        year = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise StoreError("Enter a year.", 400) from exc
    if year < 1900 or year > 2100:
        raise StoreError("Enter a year between 1900 and 2100.", 400)
    return year


def _clean_line(value, limit: int, label: str, required: bool) -> str:
    text = " ".join(str(value or "").split())
    if required and not text:
        raise StoreError(f"{label} is required.", 400)
    if len(text) > limit:
        raise StoreError(f"{label} is too long.", 400)
    return text


def _pgk_honor_payload(name: str, title: str | None, period: str | None, note: str | None):
    if title != "PGK":
        return None
    if not str(period or "").strip():
        raise StoreError("Enter the year this Past Grand Knight served.", 400)
    return _honor_fields(
        {
            "category": "past_gk",
            "name": name,
            "note": note or "",
            "period": period or "",
            "year": "",
            "month": "",
        }
    )


def _copy_member_photo(path, crop_x, crop_y, crop_scale):
    crop = (float(crop_x or 0), float(crop_y or 0), float(crop_scale or 1))
    normalized = str(path or "").replace("\\", "/")
    lower = normalized.lower()
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        ext = "jpg"
    elif lower.endswith(".webp"):
        ext = "webp"
    elif lower.endswith(".png"):
        ext = "png"
    else:
        return None, crop
    try:
        data = absolute_path(normalized).read_bytes()
        if not data:
            return None, crop
        stored = write_upload(data, ext)
    except Exception:
        return None, crop
    content = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[ext]
    return (stored, content), crop


def _lock_past_gk(cur, name: str, period: str):
    cur.execute(
        """
        SELECT id, photo_path, note
        FROM honors
        WHERE category = 'past_gk' AND lower(name) = lower(%s) AND period = %s
        ORDER BY id DESC
        LIMIT 1
        FOR UPDATE
        """,
        (name, period),
    )
    return cur.fetchone()


def _save_past_gk(cur, payload: dict, existing, photo, crop) -> str | None:
    """Create or update one Past Grand Knights row. A blank note keeps the saved note.

    Returns a copied photo path that was not stored.
    """
    note = payload["note"] or ((existing[2] or "") if existing else "")
    if existing is None:
        body = dict(payload)
        body["note"] = note
        _insert_honor_sql(cur, body, photo, crop)
        return None
    if existing[1]:
        cur.execute(
            "UPDATE honors SET name = %s, note = %s WHERE id = %s",
            (payload["name"], note, existing[0]),
        )
        return photo[0] if photo else None
    path, content_type = photo if photo else (None, None)
    cur.execute(
        """
        UPDATE honors
        SET name = %s, note = %s, photo_path = %s, photo_type = %s,
            crop_x = %s, crop_y = %s, crop_scale = %s
        WHERE id = %s
        """,
        (
            payload["name"],
            note,
            path,
            content_type,
            crop[0],
            crop[1],
            crop[2],
            existing[0],
        ),
    )
    return None


def _insert_honor_sql(cur, payload: dict, photo, crop) -> None:
    cur.execute(
        """
        INSERT INTO honors
          (category, name, period, sort_year, sort_month, note, photo_path, photo_type,
           crop_x, crop_y, crop_scale)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        _honor_params(payload, photo, crop),
    )


def _honor_fields(fields: dict) -> dict:
    category = str(fields.get("category") or "").strip()
    if category not in HONOR_CATEGORIES:
        raise StoreError("Choose a past-honor list.", 400)
    name = _clean_line(fields.get("name"), 80, "Name", True)
    note = _clean_line(fields.get("note"), 280, "Note", False)
    if category in MONTH_HONORS:
        try:
            month = int(str(fields.get("month")).strip())
        except (TypeError, ValueError) as exc:
            raise StoreError("Choose a month.", 400) from exc
        if month < 1 or month > 12:
            raise StoreError("Choose a month.", 400)
        year = _require_year(fields.get("year"))
        return {
            "category": category,
            "name": name,
            "period": f"{MONTH_NAMES[month - 1]} {year}",
            "sort_year": year,
            "sort_month": month,
            "note": note,
        }
    if category in YEAR_HONORS:
        year = _require_year(fields.get("year"))
        return {
            "category": category,
            "name": name,
            "period": str(year),
            "sort_year": year,
            "sort_month": None,
            "note": note,
        }
    match = _PGK_PERIOD.fullmatch(_clean_line(fields.get("period"), 12, "Year", True))
    if match is None:
        raise StoreError("Enter a year, such as 2024 or 2024–25.", 400)
    year = int(match.group(1))
    if year < 1900 or year > 2100:
        raise StoreError("Enter a year between 1900 and 2100.", 400)
    end = match.group(2)
    period = str(year) if end is None else f"{year}–{end}"
    return {
        "category": category,
        "name": name,
        "period": period,
        "sort_year": year,
        "sort_month": None,
        "note": note,
    }


def _event_fields(fields: dict) -> dict:
    title = _clean_line(fields.get("title"), 120, "Title", True)
    raw_date = str(fields.get("event_date") or "").strip()
    try:
        parsed = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise StoreError("Choose a date on the calendar.", 400) from exc
    if parsed.year < 1900 or parsed.year > 2100:
        raise StoreError("Choose a date on the calendar.", 400)
    event_time = _clean_line(fields.get("event_time"), 40, "Time", False) or None
    location = _clean_line(fields.get("location"), 120, "Location", False) or None
    description = str(fields.get("description") or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not description:
        raise StoreError("Description is required.", 400)
    if len(description) > 2000:
        raise StoreError("Description is too long.", 400)
    return {
        "title": title,
        "event_date": parsed.isoformat(),
        "event_time": event_time,
        "location": location,
        "description": description,
    }


def _honor_params(payload: dict, photo: tuple[str, str] | None, crop: tuple[float, float, float]):
    path, content_type = photo if photo else (None, None)
    crop_x, crop_y, crop_scale = crop
    return (
        payload["category"],
        payload["name"],
        payload["period"],
        payload["sort_year"],
        payload["sort_month"],
        payload["note"],
        path,
        content_type,
        crop_x,
        crop_y,
        crop_scale,
    )


def _memory_save_past_gk(store, payload: dict, photo, crop) -> str | None:
    """Create or update one in-memory Past Grand Knights row. Caller holds the lock."""
    match = None
    for item in store._honors:
        if item.get("category") != "past_gk":
            continue
        if str(item.get("name") or "").casefold() != str(payload["name"]).casefold():
            continue
        if item.get("period") != payload["period"]:
            continue
        if match is None or int(item["id"]) > int(match["id"]):
            match = item
    note = payload["note"] or ((match.get("note") or "") if match else "")
    if match is None:
        honor_id = store._honor_seq
        store._honor_seq += 1
        body = dict(payload)
        body["note"] = note
        store._honors.append(_memory_honor(honor_id, body, photo, crop))
        return None
    match["name"] = payload["name"]
    match["note"] = note
    if match.get("photo_path"):
        return photo[0] if photo else None
    if photo is not None:
        match["photo_path"] = photo[0]
        match["photo_type"] = photo[1]
        match["crop_x"], match["crop_y"], match["crop_scale"] = crop
    return None


def _memory_honor(
    honor_id: int,
    payload: dict,
    photo: tuple[str, str] | None,
    crop: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> dict:
    path, content_type = photo if photo else (None, None)
    crop_x, crop_y, crop_scale = crop
    return {
        "id": honor_id,
        **payload,
        "photo_path": path,
        "photo_type": content_type,
        "crop_x": crop_x,
        "crop_y": crop_y,
        "crop_scale": crop_scale,
    }


def _public_honor(row: dict) -> dict:
    photo_url = f"/api/honors/{row['id']}/photo" if row.get("photo_path") else None
    return {
        "id": int(row["id"]),
        "category": row["category"],
        "name": row["name"],
        "period": row["period"],
        "note": row.get("note") or "",
        "photo_url": photo_url,
        "crop_x": float(row.get("crop_x") or 0),
        "crop_y": float(row.get("crop_y") or 0),
        "crop_scale": float(row.get("crop_scale") or 1),
    }


def _honor_from_row(row) -> dict:
    event_month = row[5]
    return {
        "id": row[0],
        "category": row[1],
        "name": row[2],
        "period": row[3],
        "sort_year": row[4],
        "sort_month": event_month,
        "note": row[6] or "",
        "photo_path": row[7],
        "photo_type": row[8],
        "crop_x": float(row[9]) if len(row) > 9 and row[9] is not None else 0,
        "crop_y": float(row[10]) if len(row) > 10 and row[10] is not None else 0,
        "crop_scale": float(row[11]) if len(row) > 11 and row[11] is not None else 1,
    }


def _honor_sort_key(item: dict):
    return (
        _CATEGORY_ORDER.get(item["category"], 99),
        -int(item["sort_year"]),
        -(int(item["sort_month"] or 0)),
        -int(item["id"]),
    )


def _public_event(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "title": row["title"],
        "event_date": row["event_date"] if isinstance(row["event_date"], str) else row["event_date"].isoformat(),
        "event_time": row.get("event_time") or None,
        "location": row.get("location") or None,
        "description": row.get("description") or "",
    }


def _event_from_row(row) -> dict:
    return {
        "id": row[0],
        "title": row[1],
        "event_date": row[2],
        "event_time": row[3],
        "location": row[4],
        "description": row[5] or "",
    }


def _seed_honor_rows() -> list[dict]:
    rows = []
    for index, item in enumerate(HONOR_SEED, start=1):
        rows.append(
            {
                "id": index,
                "category": item["category"],
                "name": item["name"],
                "period": item["period"],
                "sort_year": item["sort_year"],
                "sort_month": item["sort_month"],
                "note": item["note"],
                "photo_path": item.get("photo_path"),
                "photo_type": item.get("photo_type"),
                "crop_x": float(item.get("crop_x") or 0),
                "crop_y": float(item.get("crop_y") or 0),
                "crop_scale": float(item.get("crop_scale") or 1),
            }
        )
    return rows


_DOCUMENT_SELECT = """
SELECT id, library, title, description, file_path, original_name, content_type, uploaded_by, uploaded_at
FROM documents
"""


def _seed_document_rows() -> list[dict]:
    rows = []
    for index, item in enumerate(SEED_DOCUMENTS, start=1):
        rows.append(
            {
                "id": index,
                "library": item["library"],
                "title": item["title"],
                "description": item["description"],
                "file_path": item["file_path"],
                "original_name": item["original_name"],
                "content_type": item["content_type"],
                "uploaded_by": item["uploaded_by"],
                "uploaded_at": item["uploaded_at"],
            }
        )
    return rows


def _document_moment(row: dict) -> datetime:
    value = row["uploaded_at"]
    if isinstance(value, datetime):
        moment = value
    else:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def _sorted_documents(rows: list[dict], library: str) -> list[dict]:
    chosen = [dict(item) for item in rows if item["library"] == library]
    chosen.sort(key=lambda item: (_document_moment(item), int(item["id"])), reverse=True)
    return chosen


def _document_from_row(row) -> dict:
    return {
        "id": row[0],
        "library": row[1],
        "title": row[2],
        "description": row[3] or "",
        "file_path": row[4],
        "original_name": row[5],
        "content_type": row[6],
        "uploaded_by": row[7],
        "uploaded_at": row[8],
    }


def _public_document(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "library": row["library"],
        "title": row["title"],
        "description": row.get("description") or "",
        "original_name": row["original_name"],
        "content_type": row["content_type"],
        "uploaded_on": uploaded_on(row["uploaded_at"]),
    }


_ANNOUNCEMENT_SELECT = """
SELECT id, title, summary, body, created_by, created_at, updated_at
FROM announcements
"""


def _announcement_value(cleaner, value: str) -> str:
    try:
        return cleaner(value)
    except ValueError as exc:
        raise StoreError(str(exc), 400) from exc


def _seed_announcement_rows() -> list[dict]:
    rows = []
    for index, item in enumerate(ANNOUNCEMENT_SEED, start=1):
        created = datetime.fromisoformat(item["created_at"])
        updated = datetime.fromisoformat(item["updated_at"])
        rows.append(
            {
                "id": index,
                "title": item["title"],
                "summary": item["summary"],
                "body": sanitize_html(item["body"]),
                "created_by": item["created_by"],
                "created_at": created,
                "updated_at": updated,
            }
        )
    return rows


def _announcement_moment(row: dict) -> datetime:
    value = row["created_at"]
    if isinstance(value, datetime):
        moment = value
    else:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def _sorted_announcements(rows: list[dict]) -> list[dict]:
    chosen = [dict(item) for item in rows]
    chosen.sort(key=lambda item: (_announcement_moment(item), int(item["id"])), reverse=True)
    return chosen


def _announcement_from_row(row) -> dict:
    return {
        "id": row[0],
        "title": row[1],
        "summary": row[2] or "",
        "body": row[3] or "",
        "created_by": row[4],
        "created_at": row[5],
        "updated_at": row[6],
    }


def _public_announcement(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "title": row["title"],
        "summary": row.get("summary") or "",
        "body": sanitize_html(row.get("body") or ""),
        "posted_on": uploaded_on(row["created_at"]),
    }


_PRAYER_SELECT = """
SELECT p.id, p.title, p.body, p.member_id, p.created_at, p.updated_at,
       COALESCE(NULLIF(btrim(m.display_name), ''), 'Member')
FROM prayer_requests p
LEFT JOIN members m ON m.membership_id = p.member_id
"""


def _prayer_value(cleaner, value: str) -> str:
    try:
        return cleaner(value)
    except ValueError as exc:
        raise StoreError(str(exc), 400) from exc


def _seed_prayer_rows() -> list[dict]:
    rows = []
    for index, item in enumerate(PRAYER_SEED, start=1):
        created = datetime.fromisoformat(item["created_at"])
        updated = datetime.fromisoformat(item["updated_at"])
        rows.append(
            {
                "id": index,
                "member_id": item["member_id"],
                "title": clean_prayer_title(item["title"]),
                "body": clean_prayer_body(item["body"]),
                "created_at": created,
                "updated_at": updated,
            }
        )
    return rows


def _prayer_moment(row: dict) -> datetime:
    value = row["created_at"]
    if isinstance(value, datetime):
        moment = value
    else:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def _sorted_prayers(rows: list[dict]) -> list[dict]:
    chosen = [dict(item) for item in rows]
    chosen.sort(key=lambda item: (_prayer_moment(item), int(item["id"])), reverse=True)
    return chosen


def _prayer_from_row(row) -> dict:
    return {
        "id": row[0],
        "title": row[1] or "",
        "body": row[2] or "",
        "member_id": row[3],
        "created_at": row[4],
        "updated_at": row[5],
    }


def _public_prayer(row: dict, viewer_id: str, author_name) -> dict:
    owner = str(row.get("member_id") or "").strip()
    viewer = str(viewer_id or "").strip()
    return {
        "id": int(row["id"]),
        "title": display_prayer_title(row.get("title") or ""),
        "body": display_prayer_body(row.get("body") or ""),
        "author_name": display_person_name(author_name),
        "submitted_on": uploaded_on(row["created_at"]),
        "mine": bool(owner and owner == viewer),
    }


def _prayer_cache_row(row: dict, author_name) -> dict:
    """Shared prayer fields plus the owner id. `mine` is applied per viewer on read."""
    shown = _public_prayer(row, "", author_name)
    shown.pop("mine", None)
    shown["member_id"] = str(row.get("member_id") or "").strip()
    return shown


def _prayers_for_viewer(rows, viewer: str) -> list[dict] | None:
    if not isinstance(rows, list):
        return None
    viewer = str(viewer or "").strip()
    visible = []
    try:
        for item in rows:
            if not isinstance(item, dict) or not isinstance(item.get("member_id"), str):
                return None
            if not isinstance(item.get("title"), str) or not isinstance(item.get("body"), str):
                return None
            if not isinstance(item.get("author_name"), str) or not isinstance(item.get("submitted_on"), str):
                return None
            owner = item["member_id"].strip()
            visible.append(
                {
                    "id": int(item["id"]),
                    "title": item.get("title") or "",
                    "body": item.get("body") or "",
                    "author_name": item.get("author_name") or "Member",
                    "submitted_on": item.get("submitted_on") or "",
                    "mine": bool(owner and owner == viewer),
                }
            )
    except (TypeError, ValueError, KeyError):
        return None
    return visible


def _author_name(cur, member_id: str) -> str:
    cur.execute("SELECT display_name FROM members WHERE membership_id = %s", (member_id,))
    found = cur.fetchone()
    if found is None:
        return "Member"
    return display_person_name(found[0])


_NOMINATION_SELECT = """
SELECT id, member_id, category, nominee_member_id, nominee_name, reason, period, created_at
FROM nominations
"""


def _nomination_order(category) -> int:
    try:
        return CATEGORY_ORDER.index(category)
    except ValueError:
        return len(CATEGORY_ORDER)


def _seed_nomination_rows() -> list[dict]:
    rows = []
    for index, item in enumerate(NOMINATION_SEED, start=1):
        rows.append(
            {
                "id": index,
                "member_id": item["member_id"],
                "category": item["category"],
                "nominee_member_id": item.get("nominee_member_id") or "",
                "nominee_name": clean_nomination_name(item["nominee_name"]),
                "reason": clean_nomination_reason(item.get("reason") or ""),
                "period": item["period"],
                "created_at": datetime.fromisoformat(item["created_at"]),
            }
        )
    return rows


def _nomination_from_row(row) -> dict:
    return {
        "id": row[0],
        "member_id": row[1],
        "category": row[2],
        "nominee_member_id": row[3] or "",
        "nominee_name": row[4] or "",
        "reason": row[5] or "",
        "period": row[6],
        "created_at": row[7],
    }


def _public_nomination(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "category": row["category"],
        "nominee_name": display_nomination_name(row.get("nominee_name") or ""),
        "nominee_member_id": str(row.get("nominee_member_id") or ""),
        "reason": display_nomination_reason(row.get("reason") or ""),
        "period": str(row.get("period") or ""),
        "submitted_on": uploaded_on(row["created_at"]),
    }


def _nomination_bundle(rows: list[dict], month_period: str, year_period: str) -> dict:
    return {
        "month_period": month_period,
        "year_period": year_period,
        "nominations": [_public_nomination(item) for item in rows],
    }


def _seed_event_rows() -> list[dict]:
    rows = []
    for index, item in enumerate(EVENT_SEED, start=1):
        rows.append(
            {
                "id": index,
                "title": item["title"],
                "event_date": item["event_date"],
                "event_time": item["event_time"],
                "location": item["location"],
                "description": item["description"],
            }
        )
    return rows


def _table_exists(cur, name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"public.{name}",))
    return cur.fetchone()[0] is not None


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def _backfill_directory_seed(cur) -> None:
    """Fill example contact fields once, when those columns are first added."""
    for membership_id in DIRECTORY_SEED:
        honorary, phone, email = directory_fields(membership_id)
        cur.execute(
            """
            UPDATE members
            SET honorary_life = %s, phone = %s, email = %s
            WHERE membership_id = %s
            """,
            (honorary, phone, email, membership_id),
        )


def _ensure_honor_seed(cur) -> None:
    """Insert each past-honor example when that category, name, and period are missing."""
    for item in HONOR_SEED:
        cur.execute(
            """
            INSERT INTO honors (category, name, period, sort_year, sort_month, note, photo_path, photo_type)
            SELECT %s, %s, %s, %s, %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM honors
                WHERE category = %s AND name = %s AND period = %s
            )
            """,
            (
                item["category"],
                item["name"],
                item["period"],
                item["sort_year"],
                item["sort_month"],
                item["note"],
                item["photo_path"],
                item["photo_type"],
                item["category"],
                item["name"],
                item["period"],
            ),
        )


def _ensure_records(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS honors (
          id SERIAL PRIMARY KEY,
          category TEXT NOT NULL,
          name TEXT NOT NULL,
          period TEXT NOT NULL,
          sort_year INTEGER NOT NULL,
          sort_month INTEGER,
          note TEXT NOT NULL DEFAULT '',
          photo_path TEXT,
          photo_type TEXT,
          crop_x DOUBLE PRECISION NOT NULL DEFAULT 0,
          crop_y DOUBLE PRECISION NOT NULL DEFAULT 0,
          crop_scale DOUBLE PRECISION NOT NULL DEFAULT 1,
          CONSTRAINT honors_category_chk CHECK (
            category IN ('knight_month', 'family_month', 'knight_year', 'family_year', 'past_gk')
          ),
          CONSTRAINT honors_month_chk CHECK (
            (category IN ('knight_month', 'family_month') AND sort_month BETWEEN 1 AND 12)
            OR (category IN ('knight_year', 'family_year', 'past_gk') AND sort_month IS NULL)
          )
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS honors_category_idx
        ON honors (category, sort_year DESC, sort_month DESC)
        """
    )
    cur.execute("ALTER TABLE honors ADD COLUMN IF NOT EXISTS crop_x DOUBLE PRECISION NOT NULL DEFAULT 0")
    cur.execute("ALTER TABLE honors ADD COLUMN IF NOT EXISTS crop_y DOUBLE PRECISION NOT NULL DEFAULT 0")
    cur.execute(
        "ALTER TABLE honors ADD COLUMN IF NOT EXISTS crop_scale DOUBLE PRECISION NOT NULL DEFAULT 1"
    )
    _ensure_honor_seed(cur)
    events_new = not _table_exists(cur, "council_events")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS council_events (
          id SERIAL PRIMARY KEY,
          title TEXT NOT NULL,
          event_date DATE NOT NULL,
          event_time TEXT,
          location TEXT,
          description TEXT NOT NULL DEFAULT '',
          sort_order INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS council_events_date_idx
        ON council_events (event_date, id)
        """
    )
    if events_new:
        for item in EVENT_SEED:
            cur.execute(
                """
                INSERT INTO council_events
                  (title, event_date, event_time, location, description, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    item["title"],
                    date.fromisoformat(item["event_date"]),
                    item["event_time"],
                    item["location"],
                    item["description"],
                    item["sort_order"],
                ),
            )
    _ensure_documents(cur)
    _ensure_announcements(cur)
    _ensure_prayers(cur)
    _ensure_nominations(cur)


def _ensure_documents(cur) -> None:
    """Create the library table. Example rows are inserted only on first create."""
    documents_new = not _table_exists(cur, "documents")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
          id SERIAL PRIMARY KEY,
          library TEXT NOT NULL,
          title TEXT NOT NULL,
          description TEXT NOT NULL DEFAULT '',
          file_path TEXT NOT NULL,
          original_name TEXT NOT NULL,
          content_type TEXT NOT NULL,
          uploaded_by TEXT,
          uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CONSTRAINT documents_library_chk CHECK (
            library IN ('treasurer', 'financial_secretary')
          )
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS documents_library_idx
        ON documents (library, uploaded_at DESC, id DESC)
        """
    )
    if not documents_new:
        return
    for item in SEED_DOCUMENTS:
        cur.execute(
            """
            INSERT INTO documents (
              library, title, description, file_path, original_name,
              content_type, uploaded_by, uploaded_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                item["library"],
                item["title"],
                item["description"],
                item["file_path"],
                item["original_name"],
                item["content_type"],
                item["uploaded_by"],
                datetime.fromisoformat(item["uploaded_at"]),
            ),
        )


def _ensure_announcements(cur) -> None:
    """Create the announcements table. Example rows are inserted only on first create."""
    announcements_new = not _table_exists(cur, "announcements")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS announcements (
          id SERIAL PRIMARY KEY,
          title TEXT NOT NULL,
          summary TEXT NOT NULL DEFAULT '',
          body TEXT NOT NULL,
          created_by TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS announcements_created_idx
        ON announcements (created_at DESC, id DESC)
        """
    )
    if not announcements_new:
        return
    for item in ANNOUNCEMENT_SEED:
        cur.execute(
            """
            INSERT INTO announcements (
              title, summary, body, created_by, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                item["title"],
                item["summary"],
                sanitize_html(item["body"]),
                item["created_by"],
                datetime.fromisoformat(item["created_at"]),
                datetime.fromisoformat(item["updated_at"]),
            ),
        )


def _ensure_prayers(cur) -> None:
    """Create the prayer requests table. Example rows are inserted only on first create."""
    prayers_new = not _table_exists(cur, "prayer_requests")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS prayer_requests (
          id SERIAL PRIMARY KEY,
          member_id TEXT NOT NULL,
          title TEXT NOT NULL DEFAULT '',
          body TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS prayer_requests_created_idx
        ON prayer_requests (created_at DESC, id DESC)
        """
    )
    if not prayers_new:
        return
    for item in PRAYER_SEED:
        cur.execute(
            """
            INSERT INTO prayer_requests (
              member_id, title, body, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                item["member_id"],
                clean_prayer_title(item["title"]),
                clean_prayer_body(item["body"]),
                datetime.fromisoformat(item["created_at"]),
                datetime.fromisoformat(item["updated_at"]),
            ),
        )


def _ensure_nominations(cur) -> None:
    """Create the nominations table. Example rows are inserted only on first create."""
    nominations_new = not _table_exists(cur, "nominations")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS nominations (
          id SERIAL PRIMARY KEY,
          member_id TEXT NOT NULL,
          category TEXT NOT NULL,
          nominee_member_id TEXT,
          nominee_name TEXT NOT NULL,
          reason TEXT NOT NULL DEFAULT '',
          period TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CONSTRAINT nominations_category_chk CHECK (
            category IN ('knight_month', 'family_month', 'knight_year', 'family_year')
          ),
          CONSTRAINT nominations_one_per_period UNIQUE (member_id, category, period)
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS nominations_period_idx
        ON nominations (period, category)
        """
    )
    if not nominations_new:
        return
    for item in NOMINATION_SEED:
        cur.execute(
            """
            INSERT INTO nominations (
              member_id, category, nominee_member_id, nominee_name, reason, period, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                item["member_id"],
                item["category"],
                item.get("nominee_member_id") or None,
                clean_nomination_name(item["nominee_name"]),
                clean_nomination_reason(item.get("reason") or ""),
                item["period"],
                datetime.fromisoformat(item["created_at"]),
            ),
        )


def _pg_sqlstate(exc: Exception) -> str | None:
    state = getattr(exc, "sqlstate", None)
    return str(state) if state else None


def _member_id_fault(exc: Exception) -> bool:
    """True when members.id blocked the insert, not the membership id."""
    state = _pg_sqlstate(exc)
    diag = getattr(exc, "diag", None)
    column = getattr(diag, "column_name", None) if diag is not None else None
    constraint = getattr(diag, "constraint_name", None) if diag is not None else None
    if state == "23502":
        return column in (None, "id")
    if state == "23505":
        return bool(constraint) and str(constraint).endswith("_pkey")
    return False


def _birthday_fault(exc: Exception) -> bool:
    state = _pg_sqlstate(exc)
    if state != "23514":
        return False
    diag = getattr(exc, "diag", None)
    constraint = getattr(diag, "constraint_name", None) if diag is not None else None
    return constraint == "members_birthday_chk" or "birth" in str(exc).lower()


def _member_create_error(exc: Exception) -> StoreError:
    state = _pg_sqlstate(exc)
    diag = getattr(exc, "diag", None)
    column = getattr(diag, "column_name", None) if diag is not None else None
    if state == "23505" and not _member_id_fault(exc):
        return StoreError("That membership ID is already in use.", 409)
    if _birthday_fault(exc):
        return StoreError("Choose a valid birthday.", 400)
    if state == "23514" or (state == "23502" and column == "title"):
        return StoreError("Choose a title from the list.", 400)
    log.warning("Could not create the member: %s", exc)
    return StoreError("Could not create the member.", 503)


def _insert_member_row(cur, memberid: str, hashed: str, name: str, cleaned: str | None, month=None, day=None):
    cur.execute(
        "SELECT membership_id FROM members WHERE membership_id = %s",
        (memberid,),
    )
    if cur.fetchone() is not None:
        raise StoreError("That membership ID is already in use.", 409)
    if cleaned:
        cur.execute(
            "UPDATE members SET title = NULL WHERE title = %s",
            (cleaned,),
        )
    cur.execute(
        """
        INSERT INTO members (membership_id, password_hash, display_name, title, is_admin, birth_month, birth_day)
        VALUES (%s, %s, %s, %s, FALSE, %s, %s)
        RETURNING membership_id, display_name, title, is_admin
        """,
        (memberid, hashed, name, cleaned, month, day),
    )
    return cur.fetchone()


def _guard_member_ids(conn) -> None:
    """Repair members.id and optional title, then leave a usable transaction.

    Sequence statements are not always transactional. A failed one aborts the
    connection until rollback, which would turn a later insert into a 503.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SAVEPOINT member_title_null")
            try:
                cur.execute("ALTER TABLE members ALTER COLUMN title DROP NOT NULL")
                cur.execute("RELEASE SAVEPOINT member_title_null")
            except Exception as exc:
                log.warning("Could not make member title optional: %s", exc)
                cur.execute("ROLLBACK TO SAVEPOINT member_title_null")
            _ensure_member_id_default(cur)
            cur.execute("SAVEPOINT member_id_seq")
            try:
                _sync_member_id_sequence(cur)
                cur.execute("RELEASE SAVEPOINT member_id_seq")
            except Exception as exc:
                log.warning("Could not sync member ids: %s", exc)
                cur.execute("ROLLBACK TO SAVEPOINT member_id_seq")
        conn.commit()
    except Exception as exc:
        log.warning("Could not prepare member ids: %s", exc)
        try:
            conn.rollback()
        except Exception:
            pass


def _ensure_member_id_default(cur) -> None:
    """Give members.id a sequence when an older table has no default."""
    cur.execute(
        """
        SELECT column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'members' AND column_name = 'id'
        """
    )
    found = cur.fetchone()
    if found is None or found[0]:
        return
    cur.execute("CREATE SEQUENCE IF NOT EXISTS members_id_seq")
    cur.execute("ALTER SEQUENCE members_id_seq OWNED BY members.id")
    cur.execute("ALTER TABLE members ALTER COLUMN id SET DEFAULT nextval('members_id_seq')")


def _sync_member_id_sequence(cur) -> None:
    """Keep the members id sequence ahead of existing rows so INSERT can succeed."""
    cur.execute("SELECT pg_get_serial_sequence('members', 'id')")
    found = cur.fetchone()
    seq = found[0] if found else None
    if not seq:
        return
    cur.execute(
        """
        SELECT setval(
            %s::regclass,
            GREATEST(COALESCE((SELECT MAX(id) FROM members), 1), 1),
            TRUE
        )
        """,
        (seq,),
    )


def _title_constraint_sql() -> str:
    for abbrev in TITLE_ABBREVS:
        if not abbrev.isascii() or not abbrev.isalnum() or abbrev != abbrev.upper():
            raise RuntimeError(f"Unexpected title abbreviation: {abbrev}")
    choices = ", ".join(f"'{abbrev}'" for abbrev in TITLE_ABBREVS)
    return f"CHECK (title IS NULL OR title IN ({choices}))"


def _remove_retired_link_blocks(cur) -> None:
    """Drop member quick-link blocks that no longer have cards."""
    cur.execute("SAVEPOINT retired_link_blocks")
    try:
        cur.execute(
            """
            DELETE FROM content_blocks AS b
            USING pages AS p
            WHERE b.page_id = p.id
              AND p.slug = 'member'
              AND b."key" = ANY(%s)
            """,
            (list(_RETIRED_MEMBER_LINK_KEYS),),
        )
        cur.execute("RELEASE SAVEPOINT retired_link_blocks")
    except Exception as exc:
        log.warning("Could not remove retired member link blocks: %s", exc)
        cur.execute("ROLLBACK TO SAVEPOINT retired_link_blocks")


def _ensure_schema(cur) -> None:
    members_existed = _table_exists(cur, "members")
    phone_existed = members_existed and _column_exists(cur, "members", "phone")
    cur.execute(_MEMBER_COLUMNS)
    cur.execute("ALTER TABLE members ADD COLUMN IF NOT EXISTS title TEXT")
    cur.execute("SAVEPOINT member_title_null")
    try:
        cur.execute("ALTER TABLE members ALTER COLUMN title DROP NOT NULL")
        cur.execute("RELEASE SAVEPOINT member_title_null")
    except Exception as exc:
        log.warning("Could not make member title optional: %s", exc)
        cur.execute("ROLLBACK TO SAVEPOINT member_title_null")
    cur.execute(
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE"
    )
    webmaster_existed = members_existed and _column_exists(cur, "members", "is_webmaster")
    cur.execute(
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS is_webmaster BOOLEAN NOT NULL DEFAULT FALSE"
    )
    if members_existed and not webmaster_existed:
        cur.execute(
            "UPDATE members SET is_webmaster = TRUE WHERE membership_id = %s",
            (TEST_MEMBER_ID,),
        )
    cloudflare_existed = members_existed and _column_exists(cur, "members", "is_cloudflare")
    cur.execute(
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS is_cloudflare BOOLEAN NOT NULL DEFAULT FALSE"
    )
    if members_existed and not cloudflare_existed:
        cur.execute(
            "UPDATE members SET is_cloudflare = TRUE WHERE membership_id = %s",
            (TEST_MEMBER_ID,),
        )
    cur.execute("ALTER TABLE members ADD COLUMN IF NOT EXISTS birth_month SMALLINT")
    cur.execute("ALTER TABLE members ADD COLUMN IF NOT EXISTS birth_day SMALLINT")
    cur.execute(
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS honorary_life BOOLEAN NOT NULL DEFAULT FALSE"
    )
    cur.execute("ALTER TABLE members ADD COLUMN IF NOT EXISTS phone TEXT")
    cur.execute("ALTER TABLE members ADD COLUMN IF NOT EXISTS email TEXT")
    if members_existed and not phone_existed:
        _backfill_directory_seed(cur)
    cur.execute("SAVEPOINT member_birthday")
    try:
        cur.execute("ALTER TABLE members DROP CONSTRAINT IF EXISTS members_birthday_chk")
        cur.execute(f"ALTER TABLE members ADD CONSTRAINT members_birthday_chk {_BIRTHDAY_CHECK}")
        cur.execute("RELEASE SAVEPOINT member_birthday")
    except Exception as exc:
        log.warning("Could not check member birthdays: %s", exc)
        cur.execute("ROLLBACK TO SAVEPOINT member_birthday")
    cur.execute("ALTER TABLE members DROP CONSTRAINT IF EXISTS members_title_abbrev")
    cur.execute(f"ALTER TABLE members ADD CONSTRAINT members_title_abbrev {_title_constraint_sql()}")
    cur.execute("SAVEPOINT member_id_seq")
    try:
        _ensure_member_id_default(cur)
        _sync_member_id_sequence(cur)
        cur.execute("RELEASE SAVEPOINT member_id_seq")
    except Exception as exc:
        log.warning("Could not sync member ids: %s", exc)
        cur.execute("ROLLBACK TO SAVEPOINT member_id_seq")
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
        f"""
        CREATE TABLE IF NOT EXISTS images (
          id SERIAL PRIMARY KEY,
          path TEXT NOT NULL,
          original_name TEXT NOT NULL,
          content_type TEXT NOT NULL,
          purpose TEXT NOT NULL DEFAULT 'library',
          slot TEXT,
          owner_membership_id TEXT REFERENCES members (membership_id) ON DELETE SET NULL,
          crop_x DOUBLE PRECISION NOT NULL DEFAULT 0,
          crop_y DOUBLE PRECISION NOT NULL DEFAULT 0,
          crop_scale DOUBLE PRECISION NOT NULL DEFAULT 1,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CONSTRAINT images_purpose_chk CHECK (purpose IN ('library', 'profile')),
          CONSTRAINT images_slot_chk {slot_check_sql()}
        )
        """
    )
    cur.execute("ALTER TABLE images ADD COLUMN IF NOT EXISTS crop_x DOUBLE PRECISION NOT NULL DEFAULT 0")
    cur.execute("ALTER TABLE images ADD COLUMN IF NOT EXISTS crop_y DOUBLE PRECISION NOT NULL DEFAULT 0")
    cur.execute(
        "ALTER TABLE images ADD COLUMN IF NOT EXISTS crop_scale DOUBLE PRECISION NOT NULL DEFAULT 1"
    )
    cur.execute("ALTER TABLE images DROP CONSTRAINT IF EXISTS images_slot_chk")
    cur.execute(f"ALTER TABLE images ADD CONSTRAINT images_slot_chk {slot_check_sql()}")
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS images_slot_idx
        ON images (slot) WHERE slot IS NOT NULL
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS images_profile_idx
        ON images (owner_membership_id) WHERE purpose = 'profile'
        """
    )
    cur.execute("SAVEPOINT fraternal_year")
    try:
        cur.execute(
            """
            INSERT INTO content_blocks (page_id, "key", field_type, value, sort_order)
            SELECT p.id, 'year.fraternal', 'text', %s, 200
            FROM pages p
            WHERE p.slug = 'member'
            ON CONFLICT (page_id, "key") DO NOTHING
            """,
            ("2026\u201327",),
        )
        cur.execute("RELEASE SAVEPOINT fraternal_year")
    except Exception as exc:
        log.warning("Could not store the fraternal year: %s", exc)
        cur.execute("ROLLBACK TO SAVEPOINT fraternal_year")
    cur.execute("SAVEPOINT nomination_card_title")
    try:
        cur.execute(
            """
            UPDATE content_blocks AS b
            SET value = %s
            FROM pages AS p
            WHERE b.page_id = p.id
              AND p.slug = 'member'
              AND b."key" = 'links.11.title'
              AND b.value = %s
            """,
            ("Knight & Family Nominations", "Knight and Family of the Month"),
        )
        cur.execute("RELEASE SAVEPOINT nomination_card_title")
    except Exception as exc:
        log.warning("Could not rename the nominations card: %s", exc)
        cur.execute("ROLLBACK TO SAVEPOINT nomination_card_title")


def _seed_images(cur) -> None:
    cur.execute("SELECT COUNT(*) FROM images")
    if cur.fetchone()[0]:
        return
    for path, original, content_type, slot in SEED_IMAGES:
        cur.execute(
            """
            INSERT INTO images (path, original_name, content_type, purpose, slot)
            VALUES (%s, %s, %s, 'library', %s)
            """,
            (path, original, content_type, slot),
        )


def _upsert_test_member(cur, hashed: str) -> str:
    cur.execute(
        """
        INSERT INTO members (
          membership_id, password_hash, display_name, title, is_admin, is_webmaster,
          honorary_life, phone, email, is_cloudflare
        )
        VALUES (%s, %s, %s, %s, TRUE, TRUE, %s, %s, %s, TRUE)
        ON CONFLICT (membership_id) DO NOTHING
        RETURNING id
        """,
        (TEST_MEMBER_ID, hashed, TEST_MEMBER_NAME, TEST_MEMBER_TITLE, *directory_fields(TEST_MEMBER_ID)),
    )
    if cur.fetchone():
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
        return "created"
    if row and verify_password(TEST_MEMBER_PASSWORD, row[0]):
        return "present"
    return "different-password"


def _ensure_sample_member(cur, hashed: str) -> None:
    cur.execute(
        """
        INSERT INTO members (
          membership_id, password_hash, display_name, title, is_admin, is_webmaster, is_cloudflare
        )
        VALUES (%s, %s, %s, NULL, FALSE, FALSE, FALSE)
        ON CONFLICT (membership_id) DO NOTHING
        """,
        (SAMPLE_MEMBER_ID, hashed, SAMPLE_MEMBER_NAME),
    )


def _ensure_admin(cur) -> None:
    cur.execute("SELECT COUNT(*) FROM members WHERE is_admin")
    if cur.fetchone()[0]:
        return
    cur.execute(
        """
        UPDATE members
        SET is_admin = TRUE, title = COALESCE(title, %s)
        WHERE membership_id = %s
        """,
        (TEST_MEMBER_TITLE, TEST_MEMBER_ID),
    )


def _ensure_webmaster(cur) -> None:
    cur.execute("SELECT COUNT(*) FROM members WHERE is_webmaster")
    if cur.fetchone()[0]:
        return
    cur.execute(
        "UPDATE members SET is_webmaster = TRUE WHERE membership_id = %s",
        (TEST_MEMBER_ID,),
    )


def _ensure_cloudflare(cur) -> None:
    cur.execute("SELECT COUNT(*) FROM members WHERE is_cloudflare")
    if cur.fetchone()[0]:
        return
    cur.execute(
        "UPDATE members SET is_cloudflare = TRUE WHERE membership_id = %s",
        (TEST_MEMBER_ID,),
    )


def _rename_test_member(cur) -> None:
    cur.execute(
        """
        UPDATE members
        SET display_name = %s
        WHERE membership_id = %s AND display_name = 'Test Member'
        """,
        (TEST_MEMBER_NAME, TEST_MEMBER_ID),
    )


def _ensure_test_roster(cur, hashed: str) -> None:
    """Insert roster members that are missing, without taking a title already in use.

    A profile photo is attached only for a member row created on this pass.
    Clearing a photo stays cleared on the next startup.
    """
    for member in MEMBER_SEED:
        honorary, phone, email = directory_fields(member.membership_id)
        if member.title:
            cur.execute(
                """
                INSERT INTO members (
                    membership_id, password_hash, display_name, title, is_admin, birth_month, birth_day,
                    honorary_life, phone, email
                )
                SELECT %s, %s, %s,
                    CASE WHEN EXISTS (SELECT 1 FROM members WHERE title = %s) THEN NULL ELSE %s END,
                    %s, %s, %s, %s, %s, %s
                WHERE NOT EXISTS (SELECT 1 FROM members WHERE membership_id = %s)
                RETURNING membership_id
                """,
                (
                    member.membership_id,
                    hashed,
                    member.display_name,
                    member.title,
                    member.title,
                    member.is_admin,
                    member.birth_month,
                    member.birth_day,
                    honorary,
                    phone,
                    email,
                    member.membership_id,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO members (
                    membership_id, password_hash, display_name, title, is_admin, birth_month, birth_day,
                    honorary_life, phone, email
                )
                SELECT %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s
                WHERE NOT EXISTS (SELECT 1 FROM members WHERE membership_id = %s)
                RETURNING membership_id
                """,
                (
                    member.membership_id,
                    hashed,
                    member.display_name,
                    member.is_admin,
                    member.birth_month,
                    member.birth_day,
                    honorary,
                    phone,
                    email,
                    member.membership_id,
                ),
            )
        if cur.fetchone() is None:
            continue
        path = member_photo_path(member.membership_id)
        cur.execute(
            """
            INSERT INTO images (path, original_name, content_type, purpose, slot, owner_membership_id)
            SELECT %s, %s, 'image/png', 'profile', NULL, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM images
                WHERE purpose = 'profile' AND owner_membership_id = %s
            )
            """,
            (path, f"{member.membership_id}.png", member.membership_id, member.membership_id),
        )


def _role_plan(officer: list[dict], director: list[dict]) -> tuple[dict[str, str], set[str]]:
    groups = (
        (officer or [], OFFICER_ROLE_SET),
        (director or [], DIRECTOR_ROLE_SET),
    )
    desired: dict[str, str] = {}
    managed: set[str] = set()
    for rows, allowed in groups:
        seen_titles: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                raise StoreError("Unknown officer title.", 400)
            try:
                title = normalize_title(row.get("title"))
            except ValueError as exc:
                raise StoreError(str(exc), 400) from exc
            if title is None or title not in allowed:
                raise StoreError("Unknown officer title.", 400)
            if title in seen_titles:
                raise StoreError("Each title can be assigned once.", 400)
            seen_titles.add(title)
            managed.add(title)
            memberid = str(row.get("memberid") or "").strip()
            if not memberid:
                continue
            if memberid in desired:
                raise StoreError("A member can hold only one title.", 400)
            desired[memberid] = title
    return desired, managed


def _slot_payload(slot: str, image: dict | None) -> dict:
    if not image:
        return {"slot": slot, "url": None, "id": None}
    return {
        "slot": slot,
        "url": image["url"],
        "id": image["id"],
        "crop_x": float(image.get("crop_x") or 0),
        "crop_y": float(image.get("crop_y") or 0),
        "crop_scale": float(image.get("crop_scale") or 1),
    }


store = Store()
