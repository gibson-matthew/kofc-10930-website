"""Council 10930 API. Run from the repo root:

..\\.venv\\Scripts\\uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field, field_validator

from db import StoreError, store
import tracking
from media import (
    MAX_DOCUMENT_BYTES,
    MAX_IMAGE_BYTES,
    RECOG_SLOTS,
    MediaError,
    absolute_path,
    clean_document_description,
    clean_document_title,
    delete_stored_file,
    normalize_crop,
    normalize_library,
    normalize_slot,
    safe_document_name,
    safe_original_name,
    validate_document,
    validate_image,
    write_library_file,
    write_upload,
)
from security import (
    ACCESS_COOKIE,
    ACCESS_MINUTES,
    REFRESH_COOKIE,
    REFRESH_DAYS,
    TokenError,
    access_from_request,
    cookie_secure,
    create_access_token,
    create_refresh_token,
    decode_token,
    using_dev_secret,
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

log = logging.getLogger("koc10930")


@asynccontextmanager
async def lifespan(app: FastAPI):
    status_text = store.prepare()
    if using_dev_secret():
        log.warning("JWT_SECRET is not set. Using the development secret.")
    if status_text == "memory":
        log.warning("PostgreSQL is unavailable. Sign-in is using the in-memory test member.")
    elif status_text == "different-password":
        log.warning("Member 1000000 already exists with a different password.")
    else:
        log.info("Test member 1000000 is ready (%s).", status_text)
    yield


app = FastAPI(title="Council 10930", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):517\d",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


class LoginIn(BaseModel):
    memberid: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("memberid")
    @classmethod
    def normalize_memberid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Membership ID is required")
        if not cleaned.isdigit():
            raise ValueError("Membership ID must contain only digits")
        return cleaned

    @field_validator("password")
    @classmethod
    def password_within_bcrypt_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password is too long")
        return value


class MemberOut(BaseModel):
    memberid: str
    display_name: str
    title: str | None = None
    is_admin: bool = False
    photo_url: str | None = None
    crop_x: float = 0
    crop_y: float = 0
    crop_scale: float = 1
    birth_month: int | None = None
    birth_day: int | None = None


class TitleIn(BaseModel):
    title: str | None = None


class CropIn(BaseModel):
    crop_x: float = 0
    crop_y: float = 0
    crop_scale: float = 1


class RoleAssignIn(BaseModel):
    title: str
    memberid: str | None = None


class AssignmentsIn(BaseModel):
    officer: list[RoleAssignIn] = Field(default_factory=list)
    director: list[RoleAssignIn] = Field(default_factory=list)


class AdminIn(BaseModel):
    is_admin: bool


class BirthdayIn(BaseModel):
    birth_month: int | None = None
    birth_day: int | None = None


class MemberCreateIn(BaseModel):
    memberid: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)
    title: str | None = None
    birth_month: int | None = None
    birth_day: int | None = None

    @field_validator("memberid")
    @classmethod
    def normalize_memberid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.isdigit():
            raise ValueError("Membership ID must contain only digits")
        return cleaned

    @field_validator("password")
    @classmethod
    def password_within_bcrypt_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password is too long")
        return value


class EventIn(BaseModel):
    title: str = ""
    event_date: str = ""
    event_time: str | None = None
    location: str | None = None
    description: str = ""


class HonorOut(BaseModel):
    id: int
    category: str
    name: str
    period: str
    note: str = ""
    photo_url: str | None = None
    crop_x: float = 0
    crop_y: float = 0
    crop_scale: float = 1


class DocumentOut(BaseModel):
    id: int
    library: str
    title: str
    description: str = ""
    original_name: str
    content_type: str
    uploaded_on: str


class EventOut(BaseModel):
    id: int
    title: str
    event_date: str
    event_time: str | None = None
    location: str | None = None
    description: str = ""


class ImageOut(BaseModel):
    id: int
    url: str
    original_name: str
    content_type: str
    purpose: str
    slot: str | None = None
    owner_membership_id: str | None = None
    crop_x: float = 0
    crop_y: float = 0
    crop_scale: float = 1


class SlotIn(BaseModel):
    slot: str | None = None


class SlideOut(BaseModel):
    slot: str
    url: str | None = None
    id: int | None = None
    crop_x: float = 0
    crop_y: float = 0
    crop_scale: float = 1


class SlotsOut(BaseModel):
    logo: str | None = None
    slides: list[SlideOut]
    recognition: list[SlideOut] = Field(default_factory=list)


class BlockOut(BaseModel):
    key: str
    field_type: str
    value: str
    sort_order: int


class PageOut(BaseModel):
    slug: str
    blocks: list[BlockOut]


class BlockIn(BaseModel):
    key: str
    field_type: str = "text"
    value: str = ""
    sort_order: int = 0


class SaveIn(BaseModel):
    blocks: list[BlockIn] = Field(default_factory=list)


class ConsentIn(BaseModel):
    choice: str

    @field_validator("choice")
    @classmethod
    def normalize_choice(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"accepted", "declined"}:
            raise ValueError("Choose accept or decline.")
        return cleaned


class AuditEventIn(BaseModel):
    type: str = Field(default="", max_length=40)
    details: dict = Field(default_factory=dict)


class AuditBatchIn(BaseModel):
    timezone: str = Field(default="", max_length=64)
    language: str = Field(default="", max_length=40)
    events: list[AuditEventIn] = Field(default_factory=list)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    secure = cookie_secure()
    response.set_cookie(
        ACCESS_COOKIE,
        access,
        max_age=ACCESS_MINUTES * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=REFRESH_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api/auth",
    )
    response.headers["Cache-Control"] = "no-store"


def _clear_auth_cookies(response: Response) -> None:
    secure = cookie_secure()
    response.delete_cookie(ACCESS_COOKIE, path="/", secure=secure, httponly=True, samesite="lax")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth", secure=secure, httponly=True, samesite="lax")


def _session_response(member: dict) -> JSONResponse:
    access = create_access_token(member["memberid"])
    refresh, token_id, expires = create_refresh_token(member["memberid"])
    try:
        store.store_refresh(token_id, member["memberid"], expires)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not start a session",
        ) from exc
    response = JSONResponse(MemberOut(**member).model_dump())
    _set_auth_cookies(response, access, refresh)
    return response


def _raise_store(exc: Exception) -> None:
    if isinstance(exc, StoreError):
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if isinstance(exc, MediaError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


def optional_member(request: Request) -> dict | None:
    token = access_from_request(request)
    if not token:
        return None
    try:
        payload = decode_token(token)
    except TokenError:
        return None
    if payload.get("type") != "access" or not payload.get("sub"):
        return None
    return store.get_member(str(payload["sub"]))


async def _read_upload(upload: UploadFile) -> tuple[bytes, str, str, str]:
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    try:
        content_type, ext = validate_image(upload.filename or "", upload.content_type, data)
    except MediaError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return data, content_type, ext, safe_original_name(upload.filename or "", ext)


async def _read_document(upload: UploadFile) -> tuple[bytes, str, str, str]:
    data = await upload.read(MAX_DOCUMENT_BYTES + 1)
    try:
        content_type, ext = validate_document(upload.filename or "", upload.content_type, data)
    except MediaError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return data, content_type, ext, safe_document_name(upload.filename or "", ext)


def get_current_member(request: Request) -> dict:
    token = access_from_request(request)
    if not token:
        raise _unauthorized()
    try:
        payload = decode_token(token)
    except TokenError:
        raise _unauthorized() from None
    if payload.get("type") != "access" or not payload.get("sub"):
        raise _unauthorized()
    member = store.get_member(str(payload["sub"]))
    if member is None:
        raise _unauthorized()
    return member


def require_admin(request: Request, member: dict = Depends(get_current_member)) -> dict:
    if not member.get("is_admin"):
        tracking.admin_denied(request, member.get("memberid"))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required",
        )
    return member


def _actor_id(request: Request) -> str | None:
    member = optional_member(request)
    if member:
        return member.get("memberid")
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        return None
    try:
        payload = decode_token(token)
    except TokenError:
        return None
    if payload.get("sub"):
        return str(payload["sub"])
    return None


@api.post("/auth/login", response_model=MemberOut)
def login(body: LoginIn, request: Request) -> JSONResponse:
    member = store.authenticate(body.memberid, body.password)
    if member is None:
        tracking.login_failure(request, body.memberid)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid membership ID or password",
        )
    response = _session_response(member)
    tracking.login_success(request, member)
    return response


@api.post("/auth/refresh", response_model=MemberOut)
def refresh(request: Request) -> JSONResponse:
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise _unauthorized()
    try:
        payload = decode_token(token)
    except TokenError:
        response = JSONResponse({"detail": "Not authenticated"}, status_code=401)
        _clear_auth_cookies(response)
        return response
    memberid = str(payload.get("sub") or "")
    token_id = str(payload.get("jti") or "")
    if payload.get("type") != "refresh" or not memberid or not token_id:
        response = JSONResponse({"detail": "Not authenticated"}, status_code=401)
        _clear_auth_cookies(response)
        return response
    if not store.rotate_refresh(token_id, memberid):
        response = JSONResponse({"detail": "Not authenticated"}, status_code=401)
        _clear_auth_cookies(response)
        return response
    member = store.get_member(memberid)
    if member is None:
        response = JSONResponse({"detail": "Not authenticated"}, status_code=401)
        _clear_auth_cookies(response)
        return response
    return _session_response(member)


@api.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    member_id = _actor_id(request)
    tracking.logout(request, member_id)
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        try:
            payload = decode_token(token)
        except TokenError:
            payload = None
        if payload and payload.get("jti"):
            store.revoke_refresh(str(payload["jti"]))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_auth_cookies(response)
    return response


@api.get("/auth/me", response_model=MemberOut)
def me(member: dict = Depends(get_current_member)) -> MemberOut:
    return MemberOut(**member)


@api.get("/pages/public")
def get_public_page() -> PageOut:
    return PageOut(**store.get_page("public"))


@api.get("/pages/member")
def get_member_page(member: dict = Depends(get_current_member)) -> PageOut:
    del member
    return PageOut(**store.get_page("member"))


@api.put("/pages/member")
def save_member_page(body: SaveIn, request: Request, member: dict = Depends(require_admin)) -> PageOut:
    payload = [block.model_dump() for block in body.blocks]
    before = None
    try:
        before = {block["key"]: block.get("value", "") for block in store.get_page("member")["blocks"]}
    except Exception:
        before = None
    saved = store.save_member(payload)
    tracking.content_diff(request, member.get("memberid"), before, payload)
    return PageOut(**saved)


@api.patch("/members/me", response_model=MemberOut)
def update_me(member: dict = Depends(get_current_member)) -> MemberOut:
    del member
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="An admin assigns officer titles.",
    )


@api.post("/members/me/photo", response_model=MemberOut)
async def upload_my_photo(
    request: Request,
    member: dict = Depends(get_current_member),
    file: UploadFile = File(...),
    crop_x: float = Form(0),
    crop_y: float = Form(0),
    crop_scale: float = Form(1),
) -> MemberOut:
    member_id = member["memberid"]
    try:
        data, content_type, ext, original = await _read_upload(file)
    except HTTPException:
        tracking.file_result(request, member_id, "profile", "failure")
        raise
    size = len(data)
    try:
        crop = normalize_crop(crop_x, crop_y, crop_scale)
    except MediaError as exc:
        tracking.file_result(request, member_id, "profile", "failure", content_type=content_type, size=size)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    path = write_upload(data, ext)
    try:
        updated = store.set_profile_image(member_id, path, original, content_type, crop)
    except (StoreError, MediaError) as exc:
        delete_stored_file(path)
        tracking.file_result(request, member_id, "profile", "failure", content_type=content_type, size=size)
        _raise_store(exc)
    tracking.file_result(
        request, member_id, "profile", "success", content_type=content_type, size=size, record_id=member_id
    )
    tracking.feature_use(request, member_id, "photo_change", {"action": "upload"})
    return MemberOut(**updated)


@api.patch("/members/me/photo", response_model=MemberOut)
def update_my_crop(body: CropIn, request: Request, member: dict = Depends(get_current_member)) -> MemberOut:
    try:
        crop = normalize_crop(body.crop_x, body.crop_y, body.crop_scale)
        updated = store.update_profile_crop(member["memberid"], crop)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    tracking.feature_use(request, member["memberid"], "photo_change", {"action": "crop"})
    return MemberOut(**updated)


@api.delete("/members/me/photo", response_model=MemberOut)
def delete_my_photo(request: Request, member: dict = Depends(get_current_member)) -> MemberOut:
    try:
        updated = store.clear_profile_image(member["memberid"])
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    tracking.file_result(request, member["memberid"], "profile", "removed", record_id=member["memberid"])
    tracking.feature_use(request, member["memberid"], "photo_change", {"action": "remove"})
    return MemberOut(**updated)


@api.post("/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def create_member(body: MemberCreateIn, request: Request, member: dict = Depends(require_admin)) -> MemberOut:
    try:
        created = store.create_member(
            body.memberid,
            body.password,
            body.display_name,
            body.title,
            body.birth_month,
            body.birth_day,
        )
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    extra = {"title": created["title"]} if created.get("title") else {}
    tracking.admin_event(request, member.get("memberid"), "create", "member", created["memberid"], **extra)
    return MemberOut(**created)


@api.get("/members", response_model=list[MemberOut])
def list_members(member: dict = Depends(require_admin)) -> list[MemberOut]:
    del member
    try:
        rows = store.list_members()
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    return [MemberOut(**row) for row in rows]


@api.get("/members/roster", response_model=list[MemberOut])
def member_roster(member: dict = Depends(get_current_member)) -> list[MemberOut]:
    del member
    try:
        rows = store.list_members()
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    return [MemberOut(**row) for row in rows]


@api.patch("/members/{memberid}", response_model=MemberOut)
def update_member_admin(
    memberid: str,
    body: AdminIn,
    request: Request,
    member: dict = Depends(require_admin),
) -> MemberOut:
    before = None
    try:
        before = store.get_member(memberid)
    except Exception:
        before = None
    try:
        updated = store.set_admin(memberid, body.is_admin)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    tracking.flag_change(request, member.get("memberid"), memberid, before, updated)
    return MemberOut(**updated)


@api.patch("/members/{memberid}/birthday", response_model=MemberOut)
def update_member_birthday(
    memberid: str,
    body: BirthdayIn,
    request: Request,
    member: dict = Depends(require_admin),
) -> MemberOut:
    try:
        updated = store.set_birthday(memberid, body.birth_month, body.birth_day)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    tracking.admin_event(request, member.get("memberid"), "update", "member_birthday", memberid)
    return MemberOut(**updated)


@api.patch("/members/{memberid}/title", response_model=MemberOut)
def update_member_title(
    memberid: str,
    body: TitleIn,
    request: Request,
    member: dict = Depends(require_admin),
) -> MemberOut:
    before = None
    try:
        before = store.list_members()
    except Exception:
        before = None
    try:
        updated = store.set_title(memberid, body.title)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    after = None
    try:
        after = store.list_members()
    except Exception:
        after = [updated]
    tracking.title_changes(request, member.get("memberid"), before, after)
    return MemberOut(**updated)


@api.post("/members/assignments", response_model=list[MemberOut])
def save_assignments(body: AssignmentsIn, request: Request, member: dict = Depends(require_admin)) -> list[MemberOut]:
    before = None
    try:
        before = store.list_members()
    except Exception:
        before = None
    try:
        rows = store.assign_roles(
            [row.model_dump() for row in body.officer],
            [row.model_dump() for row in body.director],
        )
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    tracking.title_changes(request, member.get("memberid"), before, rows)
    return [MemberOut(**row) for row in rows]


def _optional_crop(crop_x: str | None, crop_y: str | None, crop_scale: str | None):
    raw = (crop_x, crop_y, crop_scale)
    if all(value is None or not str(value).strip() for value in raw):
        return None

    def number(value, default: float) -> float:
        if value is None or not str(value).strip():
            return default
        return float(str(value).strip())

    try:
        return normalize_crop(number(crop_x, 0), number(crop_y, 0), number(crop_scale, 1))
    except MediaError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Viewing angle is not valid.") from exc


def _honor_fields(category: str, name: str, note: str, year: str, month: str, period: str) -> dict:
    return {
        "category": category,
        "name": name,
        "note": note,
        "year": year,
        "month": month,
        "period": period,
    }


def _file_size(path: str) -> int | None:
    try:
        return absolute_path(path).stat().st_size
    except Exception:
        return None


async def _optional_image(upload: UploadFile | None) -> tuple[str, str] | None:
    if upload is None or not (upload.filename or "").strip():
        return None
    data, content_type, ext, _original = await _read_upload(upload)
    return write_upload(data, ext), content_type


@api.get("/honors", response_model=list[HonorOut])
def list_honors(member: dict = Depends(get_current_member)) -> list[HonorOut]:
    del member
    try:
        rows = store.list_honors()
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    return [HonorOut(**row) for row in rows]


@api.post("/honors", response_model=HonorOut, status_code=status.HTTP_201_CREATED)
async def create_honor(
    request: Request,
    member: dict = Depends(require_admin),
    category: str = Form(...),
    name: str = Form(...),
    note: str = Form(""),
    year: str = Form(""),
    month: str = Form(""),
    period: str = Form(""),
    crop_x: str | None = Form(None),
    crop_y: str | None = Form(None),
    crop_scale: str | None = Form(None),
    file: UploadFile | None = File(None),
) -> HonorOut:
    crop = _optional_crop(crop_x, crop_y, crop_scale)
    try:
        photo = await _optional_image(file)
    except HTTPException:
        if file is not None and (file.filename or "").strip():
            tracking.file_result(request, member.get("memberid"), "honor", "failure")
        raise
    try:
        created = store.create_honor(_honor_fields(category, name, note, year, month, period), photo, crop)
    except (StoreError, MediaError) as exc:
        if photo:
            delete_stored_file(photo[0])
            tracking.file_result(request, member.get("memberid"), "honor", "failure", content_type=photo[1])
        _raise_store(exc)
    if photo:
        tracking.file_result(
            request,
            member.get("memberid"),
            "honor",
            "success",
            content_type=photo[1],
            size=_file_size(photo[0]),
            record_id=created.get("id"),
        )
    tracking.admin_event(
        request, member.get("memberid"), "create", "honor", created.get("id"), category=category
    )
    return HonorOut(**created)


@api.get("/honors/{honor_id}/photo")
def honor_photo(honor_id: int, member: dict = Depends(get_current_member)) -> FileResponse:
    del member
    found = store.honor_file(honor_id)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo was not found.")
    path, content_type = found
    try:
        full = absolute_path(path)
    except MediaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo was not found.") from exc
    if not full.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo was not found.")
    return FileResponse(full, media_type=content_type)


@api.patch("/honors/{honor_id}", response_model=HonorOut)
async def update_honor(
    honor_id: int,
    request: Request,
    member: dict = Depends(require_admin),
    category: str = Form(...),
    name: str = Form(...),
    note: str = Form(""),
    year: str = Form(""),
    month: str = Form(""),
    period: str = Form(""),
    clear_photo: str = Form("false"),
    crop_x: str | None = Form(None),
    crop_y: str | None = Form(None),
    crop_scale: str | None = Form(None),
    file: UploadFile | None = File(None),
) -> HonorOut:
    crop = _optional_crop(crop_x, crop_y, crop_scale)
    clearing = clear_photo.strip().lower() in {"1", "true", "yes", "on"}
    try:
        photo = await _optional_image(file)
    except HTTPException:
        if file is not None and (file.filename or "").strip():
            tracking.file_result(request, member.get("memberid"), "honor", "failure", record_id=honor_id)
        raise
    try:
        updated = store.update_honor(
            honor_id,
            _honor_fields(category, name, note, year, month, period),
            photo,
            clearing,
            crop,
        )
    except (StoreError, MediaError) as exc:
        if photo:
            delete_stored_file(photo[0])
            tracking.file_result(
                request, member.get("memberid"), "honor", "failure", content_type=photo[1], record_id=honor_id
            )
        _raise_store(exc)
    if photo:
        tracking.file_result(
            request,
            member.get("memberid"),
            "honor",
            "success",
            content_type=photo[1],
            size=_file_size(photo[0]),
            record_id=honor_id,
        )
    elif clearing:
        tracking.file_result(request, member.get("memberid"), "honor", "removed", record_id=honor_id)
    tracking.admin_event(request, member.get("memberid"), "update", "honor", honor_id, category=category)
    return HonorOut(**updated)


@api.delete("/honors/{honor_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_honor(honor_id: int, request: Request, member: dict = Depends(require_admin)) -> Response:
    try:
        store.delete_honor(honor_id)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    tracking.admin_event(request, member.get("memberid"), "delete", "honor", honor_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@api.get("/events", response_model=list[EventOut])
def list_events(member: dict = Depends(get_current_member)) -> list[EventOut]:
    del member
    try:
        rows = store.list_events()
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    return [EventOut(**row) for row in rows]


@api.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(body: EventIn, request: Request, member: dict = Depends(require_admin)) -> EventOut:
    try:
        created = store.create_event(body.model_dump())
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    tracking.admin_event(request, member.get("memberid"), "create", "event", created.get("id"))
    return EventOut(**created)


@api.patch("/events/{event_id}", response_model=EventOut)
def update_event(event_id: int, body: EventIn, request: Request, member: dict = Depends(require_admin)) -> EventOut:
    try:
        updated = store.update_event(event_id, body.model_dump())
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    tracking.admin_event(request, member.get("memberid"), "update", "event", event_id)
    return EventOut(**updated)


@api.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_event(event_id: int, request: Request, member: dict = Depends(require_admin)) -> Response:
    try:
        store.delete_event(event_id)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    tracking.admin_event(request, member.get("memberid"), "delete", "event", event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@api.get("/media/slots", response_model=SlotsOut)
def media_slots() -> SlotsOut:
    try:
        payload = store.public_slots()
    except StoreError:
        payload = {
            "logo": None,
            "slides": [
                {"slot": "carousel.1", "url": None, "id": None},
                {"slot": "carousel.2", "url": None, "id": None},
                {"slot": "carousel.3", "url": None, "id": None},
                {"slot": "carousel.4", "url": None, "id": None},
            ],
            "recognition": [{"slot": slot, "url": None, "id": None} for slot in RECOG_SLOTS],
        }
    return SlotsOut(**payload)


@api.get("/media", response_model=list[ImageOut])
def list_media(member: dict = Depends(require_admin)) -> list[ImageOut]:
    del member
    try:
        rows = store.list_images("library")
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    return [ImageOut(**row) for row in rows]


@api.post("/media", response_model=ImageOut)
async def upload_media(
    request: Request,
    file: UploadFile = File(...),
    member: dict = Depends(require_admin),
    crop_x: str | None = Form(None),
    crop_y: str | None = Form(None),
    crop_scale: str | None = Form(None),
) -> ImageOut:
    try:
        data, content_type, ext, original = await _read_upload(file)
    except HTTPException:
        tracking.file_result(request, member.get("memberid"), "library_image", "failure")
        raise
    size = len(data)
    crop = _optional_crop(crop_x, crop_y, crop_scale)
    path = write_upload(data, ext)
    try:
        image = store.add_library_image(path, original, content_type, member["memberid"], crop)
    except (StoreError, MediaError) as exc:
        delete_stored_file(path)
        tracking.file_result(
            request, member.get("memberid"), "library_image", "failure", content_type=content_type, size=size
        )
        _raise_store(exc)
    tracking.file_result(
        request,
        member.get("memberid"),
        "library_image",
        "success",
        content_type=content_type,
        size=size,
        record_id=image.get("id"),
    )
    tracking.admin_event(request, member.get("memberid"), "create", "library_image", image.get("id"))
    return ImageOut(**image)


@api.post("/media/{image_id}/replace", response_model=ImageOut)
async def replace_media(
    image_id: int,
    request: Request,
    file: UploadFile = File(...),
    member: dict = Depends(require_admin),
    crop_x: str | None = Form(None),
    crop_y: str | None = Form(None),
    crop_scale: str | None = Form(None),
) -> ImageOut:
    try:
        data, content_type, ext, original = await _read_upload(file)
    except HTTPException:
        tracking.file_result(request, member.get("memberid"), "library_image", "failure", record_id=image_id)
        raise
    size = len(data)
    crop = _optional_crop(crop_x, crop_y, crop_scale)
    path = write_upload(data, ext)
    try:
        image = store.replace_image(image_id, path, original, content_type, crop)
    except (StoreError, MediaError) as exc:
        delete_stored_file(path)
        tracking.file_result(
            request,
            member.get("memberid"),
            "library_image",
            "failure",
            content_type=content_type,
            size=size,
            record_id=image_id,
        )
        _raise_store(exc)
    tracking.file_result(
        request,
        member.get("memberid"),
        "library_image",
        "success",
        content_type=content_type,
        size=size,
        record_id=image_id,
    )
    tracking.admin_event(request, member.get("memberid"), "update", "library_image", image_id)
    return ImageOut(**image)


@api.patch("/media/{image_id}/crop", response_model=ImageOut)
def update_media_crop(
    image_id: int,
    body: CropIn,
    request: Request,
    member: dict = Depends(require_admin),
) -> ImageOut:
    try:
        crop = normalize_crop(body.crop_x, body.crop_y, body.crop_scale)
        image = store.update_library_crop(image_id, crop)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    tracking.admin_event(request, member.get("memberid"), "update", "library_image", image_id)
    return ImageOut(**image)


@api.patch("/media/{image_id}", response_model=ImageOut)
def assign_media(
    image_id: int,
    body: SlotIn,
    request: Request,
    member: dict = Depends(require_admin),
) -> ImageOut:
    try:
        slot = normalize_slot(body.slot)
        image = store.assign_slot(image_id, slot)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    tracking.admin_event(request, member.get("memberid"), "update", "library_image", image_id, slot=slot or "")
    return ImageOut(**image)


@api.delete("/media/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(image_id: int, request: Request, member: dict = Depends(require_admin)) -> Response:
    try:
        store.delete_image(image_id)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    tracking.file_result(request, member.get("memberid"), "library_image", "removed", record_id=image_id)
    tracking.admin_event(request, member.get("memberid"), "delete", "library_image", image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@api.get("/documents", response_model=list[DocumentOut])
def list_documents(library: str, member: dict = Depends(get_current_member)) -> list[DocumentOut]:
    del member
    try:
        rows = store.list_documents(library)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    return [DocumentOut(**row) for row in rows]


@api.get("/documents/{document_id}/file")
def document_file(document_id: int, request: Request, member: dict = Depends(get_current_member)) -> FileResponse:
    try:
        found = store.document_file(document_id)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document was not found.")
    path, content_type, original_name = found
    try:
        full = absolute_path(path)
    except MediaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document was not found.") from exc
    if not full.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document was not found.")
    disposition = "inline" if content_type == "application/pdf" else "attachment"
    details = {
        "record_id": document_id,
        "library": tracking.library_name(path),
        "content_type": content_type,
    }
    try:
        details["size"] = full.stat().st_size
    except OSError:
        pass
    tracking.record_accept(
        request,
        "document.preview" if disposition == "inline" else "document.download",
        member_id=member.get("memberid"),
        details=details,
    )
    return FileResponse(
        full,
        media_type=content_type,
        filename=original_name,
        content_disposition_type=disposition,
    )


@api.post("/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_document(
    request: Request,
    member: dict = Depends(require_admin),
    library: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
) -> DocumentOut:
    try:
        cleaned_library = normalize_library(library)
        cleaned_title = clean_document_title(title)
        cleaned_description = clean_document_description(description)
    except MediaError as exc:
        tracking.file_result(request, member.get("memberid"), "document", "failure")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not (file.filename or "").strip():
        tracking.file_result(request, member.get("memberid"), "document", "failure", record_id=cleaned_library)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a document.")
    try:
        data, content_type, ext, original_name = await _read_document(file)
    except HTTPException:
        tracking.file_result(request, member.get("memberid"), "document", "failure", record_id=cleaned_library)
        raise
    size = len(data)
    stored = write_library_file(cleaned_library, data, ext)
    try:
        created = store.create_document(
            cleaned_library,
            cleaned_title,
            cleaned_description,
            stored,
            original_name,
            content_type,
            member.get("memberid"),
        )
    except (StoreError, MediaError) as exc:
        delete_stored_file(stored)
        tracking.file_result(
            request,
            member.get("memberid"),
            "document",
            "failure",
            content_type=content_type,
            size=size,
            record_id=cleaned_library,
        )
        _raise_store(exc)
    tracking.file_result(
        request,
        member.get("memberid"),
        "document",
        "success",
        content_type=content_type,
        size=size,
        record_id=created.get("id"),
    )
    tracking.admin_event(
        request,
        member.get("memberid"),
        "create",
        "document",
        created.get("id"),
        library=cleaned_library,
    )
    return DocumentOut(**created)


@api.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, request: Request, member: dict = Depends(require_admin)) -> Response:
    try:
        store.delete_document(document_id)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    tracking.file_result(request, member.get("memberid"), "document", "removed", record_id=document_id)
    tracking.admin_event(request, member.get("memberid"), "delete", "document", document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@api.get("/media/files/{image_id}")
def media_file(image_id: int, request: Request) -> FileResponse:
    image = store.get_image(image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image was not found.")
    visible = image["purpose"] == "profile" or bool(image.get("slot"))
    if not visible:
        member = optional_member(request)
        if not (member and member.get("is_admin")):
            tracking.admin_denied(request, member.get("memberid") if member else None)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image was not found.")
    try:
        path = absolute_path(image["path"])
    except MediaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image was not found.") from exc
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image was not found.")
    return FileResponse(path, media_type=image["content_type"], headers={"Cache-Control": "no-cache"})


@api.get("/consent")
def get_consent(request: Request) -> dict:
    return {"choice": tracking.consent_choice(request), "version": tracking.CONSENT_VERSION}


@api.post("/consent")
def post_consent(body: ConsentIn, request: Request) -> JSONResponse:
    if tracking.allow_client(tracking.client_ip(request), "consent", 30, 60 * 60) is False:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Try again in a little while.")
    member = optional_member(request)
    response = JSONResponse({"choice": body.choice, "version": tracking.CONSENT_VERSION})
    tracking.save_consent(request, response, body.choice, member.get("memberid") if member else None)
    return response


@api.post("/audit/events", status_code=status.HTTP_204_NO_CONTENT)
def audit_events(body: AuditBatchIn, request: Request) -> Response:
    if tracking.allow_client(tracking.client_ip(request), "audit", 120, 60) is False:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    member = optional_member(request)
    tracking.ingest_client_events(
        request,
        member.get("memberid") if member else None,
        [item.model_dump() for item in body.events],
        language=body.language,
        timezone_name=body.timezone,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.exception_handler(StarletteHTTPException)
async def http_exception(request: Request, exc: StarletteHTTPException):
    if exc.status_code >= 500:
        tracking.backend_error(request, str(exc.detail), exc.status_code)
    headers = getattr(exc, "headers", None) or None
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    if isinstance(exc, StarletteHTTPException):
        return await http_exception(request, exc)
    tracking.backend_error(request, exc.__class__.__name__, 500)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(api)
