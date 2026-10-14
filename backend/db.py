"""Page and member store. Uses Postgres when it answers, otherwise memory."""

from __future__ import annotations

import logging
import os
import re
import threading
from copy import deepcopy
from datetime import date, datetime, timezone

from media import RECOG_SLOTS, SEED_IMAGES, delete_stored_file, public_url, slot_check_sql
from security import hash_password, verify_password, verify_password_dummy
from seed import EVENT_SEED, HONOR_SEED, PAGES
from titles import (
    DIRECTOR_ROLE_SET,
    OFFICER_ROLE_SET,
    TITLE_ABBREVS,
    normalize_title,
)

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/koc10930"
# Documented local account. Created only when this membership id is missing.
TEST_MEMBER_ID = "1000000"
TEST_MEMBER_PASSWORD = "Password123!"
TEST_MEMBER_NAME = "David Hernandez"
TEST_MEMBER_TITLE = "GK"
# Second local account so the webmaster can grant admin access to someone else.
SAMPLE_MEMBER_ID = "1000001"
SAMPLE_MEMBER_NAME = "Sample Brother"

log = logging.getLogger("koc10930")


class StoreError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


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
        self._images: list[dict] = []
        self._image_seq = 1
        self._honors = _seed_honor_rows()
        self._events = _seed_event_rows()
        self._honor_seq = len(self._honors) + 1
        self._event_seq = len(self._events) + 1
        self._refresh: dict[str, dict] = {}
        self._prefer_memory = False

    def prepare(self) -> str:
        """Create auth tables, the webmaster, and example images. Returns a short status."""
        hashed = hash_password(TEST_MEMBER_PASSWORD)
        with self._lock:
            self._prefer_memory = False
            self._members = [
                {
                    "membership_id": TEST_MEMBER_ID,
                    "password_hash": hashed,
                    "display_name": TEST_MEMBER_NAME,
                    "title": TEST_MEMBER_TITLE,
                    "is_admin": True,
                    "birth_month": None,
                    "birth_day": None,
                },
                {
                    "membership_id": SAMPLE_MEMBER_ID,
                    "password_hash": hashed,
                    "display_name": SAMPLE_MEMBER_NAME,
                    "title": None,
                    "is_admin": False,
                    "birth_month": None,
                    "birth_day": None,
                },
            ]
            self._images = _seed_image_rows()
            self._image_seq = len(self._images) + 1
            self._honors = _seed_honor_rows()
            self._events = _seed_event_rows()
            self._honor_seq = len(self._honors) + 1
            self._event_seq = len(self._events) + 1
        conn = _connect()
        if conn is None:
            with self._lock:
                self._prefer_memory = True
            return "memory"
        try:
            with conn.cursor() as cur:
                _ensure_schema(cur)
                _seed_images(cur)
                _ensure_records(cur)
                status = _upsert_test_member(cur, hashed)
                _ensure_sample_member(cur, hashed)
                _ensure_admin(cur)
                _rename_test_member(cur)
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
                cur.execute(
                    """
                    SELECT m.membership_id, m.password_hash, m.display_name, m.title, m.is_admin,
                           i.id, i.path, i.crop_x, i.crop_y, i.crop_scale,
                           m.birth_month, m.birth_day
                    FROM members m
                    LEFT JOIN images i
                      ON i.owner_membership_id = m.membership_id AND i.purpose = 'profile'
                    WHERE m.membership_id = %s
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
            "photo_url": photo_url,
            "crop_x": float(record.get("crop_x") or 0),
            "crop_y": float(record.get("crop_y") or 0),
            "crop_scale": float(record.get("crop_scale") or 1),
            "birth_month": _birthday_number(record.get("birth_month")),
            "birth_day": _birthday_number(record.get("birth_day")),
        }

    def list_members(self) -> list[dict]:
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
                    rows.append(self._public_member(record))
            rows.sort(key=lambda item: (item["display_name"].lower(), item["memberid"]))
            return rows
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT m.membership_id, m.password_hash, m.display_name, m.title, m.is_admin,
                           i.id, i.path, i.crop_x, i.crop_y, i.crop_scale,
                           m.birth_month, m.birth_day
                    FROM members m
                    LEFT JOIN images i
                      ON i.owner_membership_id = m.membership_id AND i.purpose = 'profile'
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
        return [self._public_member(_record_from_row(row)) for row in fetched]

    def set_title(self, memberid: str, title: str | None) -> dict:
        try:
            cleaned = normalize_title(title)
        except ValueError as exc:
            raise StoreError(str(exc), 400) from exc
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
                    "birth_month": birth_month,
                    "birth_day": birth_day,
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
    ) -> dict:
        memberid, name, cleaned = _member_create_fields(memberid, password, display_name, title)
        month, day = _clean_birthday(birth_month, birth_day)
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
                        "birth_month": month,
                        "birth_day": day,
                    }
                )
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
            "photo_url": None,
            "crop_x": 0.0,
            "crop_y": 0.0,
            "crop_scale": 1.0,
            "birth_month": month,
            "birth_day": day,
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

    def list_honors(self) -> list[dict]:
        conn = self._open()
        if conn is None:
            with self._lock:
                rows = [dict(item) for item in self._honors]
            rows.sort(key=_honor_sort_key)
            return [_public_honor(item) for item in rows]
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, category, name, period, sort_year, sort_month, note, photo_path, photo_type
                    FROM honors
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
        return [_public_honor(_honor_from_row(row)) for row in fetched]

    def honor_file(self, honor_id: int) -> tuple[str, str] | None:
        row = self._honor_record(honor_id)
        if row is None or not row.get("photo_path"):
            return None
        path = str(row["photo_path"]).replace("\\", "/")
        if not path.startswith("backend/uploads/"):
            return None
        return path, row.get("photo_type") or "application/octet-stream"

    def create_honor(self, fields: dict, photo: tuple[str, str] | None) -> dict:
        payload = _honor_fields(fields)
        conn = self._open()
        if conn is None:
            with self._lock:
                honor_id = self._honor_seq
                self._honor_seq += 1
                self._honors.append(_memory_honor(honor_id, payload, photo))
            row = self._honor_record(honor_id)
            if row is None:
                raise StoreError("Could not save the honor.", 503)
            return _public_honor(row)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO honors
                      (category, name, period, sort_year, sort_month, note, photo_path, photo_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    _honor_params(payload, photo),
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
    ) -> dict:
        payload = _honor_fields(fields)
        previous = self._honor_record(honor_id)
        if previous is None:
            raise StoreError("Honor was not found.", 404)
        conn = self._open()
        if conn is None:
            with self._lock:
                target = next((item for item in self._honors if item["id"] == honor_id), None)
                if target is None:
                    raise StoreError("Honor was not found.", 404)
                old_path = target.get("photo_path")
                target.update(payload)
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
                        sort_month = %s, note = %s, photo_path = %s, photo_type = %s
                    WHERE id = %s
                    """,
                    (*_honor_params(payload, (next_path, next_type) if next_path else None), honor_id),
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
        return [_public_event(_event_from_row(row)) for row in fetched]

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
                cur.execute(
                    """
                    SELECT id, category, name, period, sort_year, sort_month, note, photo_path, photo_type
                    FROM honors
                    WHERE id = %s
                    """,
                    (honor_id,),
                )
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

    def add_library_image(self, path: str, original_name: str, content_type: str, owner: str | None) -> dict:
        return self._insert_image(path, original_name, content_type, "library", None, owner)

    def replace_image(self, image_id: int, path: str, original_name: str, content_type: str) -> dict:
        current = self.get_image(image_id)
        if current is None:
            delete_stored_file(path)
            raise StoreError("Image was not found.", 404)
        if current["purpose"] == "profile":
            delete_stored_file(path)
            raise StoreError("Profile photos are replaced from Settings.", 400)
        conn = self._open()
        if conn is None:
            with self._lock:
                for image in self._images:
                    if image["id"] == image_id:
                        old = image["path"]
                        image["path"] = path
                        image["original_name"] = original_name
                        image["content_type"] = content_type
                        delete_stored_file(old)
                        return _public_image(image)
            delete_stored_file(path)
            raise StoreError("Image was not found.", 404)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE images
                    SET path = %s, original_name = %s, content_type = %s
                    WHERE id = %s AND purpose <> 'profile'
                    """,
                    (path, original_name, content_type, image_id),
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
    ) -> dict:
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
                    "crop_x": 0,
                    "crop_y": 0,
                    "crop_scale": 1,
                }
                self._image_seq += 1
                self._images.append(image)
                return _public_image(image)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO images
                      (path, original_name, content_type, purpose, slot, owner_membership_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (path, original_name, content_type, purpose, slot, owner),
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


_IMAGE_SELECT = """
SELECT id, path, original_name, content_type, purpose, slot, owner_membership_id
FROM images
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
  birth_month SMALLINT,
  birth_day SMALLINT
)
"""


def _rollback(conn) -> None:
    try:
        conn.rollback()
        conn.close()
    except Exception:
        pass


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


def _honor_params(payload: dict, photo: tuple[str, str] | None):
    path, content_type = photo if photo else (None, None)
    return (
        payload["category"],
        payload["name"],
        payload["period"],
        payload["sort_year"],
        payload["sort_month"],
        payload["note"],
        path,
        content_type,
    )


def _memory_honor(honor_id: int, payload: dict, photo: tuple[str, str] | None) -> dict:
    path, content_type = photo if photo else (None, None)
    return {"id": honor_id, **payload, "photo_path": path, "photo_type": content_type}


def _public_honor(row: dict) -> dict:
    photo_url = f"/api/honors/{row['id']}/photo" if row.get("photo_path") else None
    return {
        "id": int(row["id"]),
        "category": row["category"],
        "name": row["name"],
        "period": row["period"],
        "note": row.get("note") or "",
        "photo_url": photo_url,
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
                "photo_path": None,
                "photo_type": None,
            }
        )
    return rows


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


def _ensure_records(cur) -> None:
    honors_new = not _table_exists(cur, "honors")
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
    if honors_new:
        for item in HONOR_SEED:
            cur.execute(
                """
                INSERT INTO honors (category, name, period, sort_year, sort_month, note)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    item["category"],
                    item["name"],
                    item["period"],
                    item["sort_year"],
                    item["sort_month"],
                    item["note"],
                ),
            )
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


def _ensure_schema(cur) -> None:
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
    cur.execute("ALTER TABLE members ADD COLUMN IF NOT EXISTS birth_month SMALLINT")
    cur.execute("ALTER TABLE members ADD COLUMN IF NOT EXISTS birth_day SMALLINT")
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
        INSERT INTO members (membership_id, password_hash, display_name, title, is_admin)
        VALUES (%s, %s, %s, %s, TRUE)
        ON CONFLICT (membership_id) DO NOTHING
        RETURNING id
        """,
        (TEST_MEMBER_ID, hashed, TEST_MEMBER_NAME, TEST_MEMBER_TITLE),
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
        INSERT INTO members (membership_id, password_hash, display_name, title, is_admin)
        VALUES (%s, %s, %s, NULL, FALSE)
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


def _rename_test_member(cur) -> None:
    cur.execute(
        """
        UPDATE members
        SET display_name = %s
        WHERE membership_id = %s AND display_name = 'Test Member'
        """,
        (TEST_MEMBER_NAME, TEST_MEMBER_ID),
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
    return {"slot": slot, "url": image["url"], "id": image["id"]}


store = Store()
