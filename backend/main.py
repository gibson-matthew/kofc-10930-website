"""Council 10930 API. Run from the repo root:

..\\.venv\\Scripts\\uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

from db import StoreError, store
from media import (
    MAX_IMAGE_BYTES,
    MediaError,
    absolute_path,
    delete_stored_file,
    normalize_slot,
    safe_original_name,
    validate_image,
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


class TitleIn(BaseModel):
    title: str | None = None


class AdminIn(BaseModel):
    is_admin: bool


class ImageOut(BaseModel):
    id: int
    url: str
    original_name: str
    content_type: str
    purpose: str
    slot: str | None = None
    owner_membership_id: str | None = None


class SlotIn(BaseModel):
    slot: str | None = None


class SlideOut(BaseModel):
    slot: str
    url: str | None = None


class SlotsOut(BaseModel):
    logo: str | None = None
    slides: list[SlideOut]


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


def require_admin(member: dict = Depends(get_current_member)) -> dict:
    if not member.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required",
        )
    return member


@api.post("/auth/login", response_model=MemberOut)
def login(body: LoginIn) -> JSONResponse:
    member = store.authenticate(body.memberid, body.password)
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid membership ID or password",
        )
    return _session_response(member)


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
def save_member_page(body: SaveIn, member: dict = Depends(require_admin)) -> PageOut:
    del member
    payload = [block.model_dump() for block in body.blocks]
    return PageOut(**store.save_member(payload))


@api.patch("/members/me", response_model=MemberOut)
def update_me(body: TitleIn, member: dict = Depends(get_current_member)) -> MemberOut:
    try:
        updated = store.set_title(member["memberid"], body.title)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    return MemberOut(**updated)


@api.post("/members/me/photo", response_model=MemberOut)
async def upload_my_photo(
    file: UploadFile = File(...),
    member: dict = Depends(get_current_member),
) -> MemberOut:
    data, content_type, ext, original = await _read_upload(file)
    path = write_upload(data, ext)
    try:
        updated = store.set_profile_image(member["memberid"], path, original, content_type)
    except (StoreError, MediaError) as exc:
        delete_stored_file(path)
        _raise_store(exc)
    return MemberOut(**updated)


@api.delete("/members/me/photo", response_model=MemberOut)
def delete_my_photo(member: dict = Depends(get_current_member)) -> MemberOut:
    try:
        updated = store.clear_profile_image(member["memberid"])
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    return MemberOut(**updated)


@api.get("/members", response_model=list[MemberOut])
def list_members(member: dict = Depends(require_admin)) -> list[MemberOut]:
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
    member: dict = Depends(require_admin),
) -> MemberOut:
    del member
    try:
        updated = store.set_admin(memberid, body.is_admin)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    return MemberOut(**updated)


@api.get("/media/slots", response_model=SlotsOut)
def media_slots() -> SlotsOut:
    try:
        payload = store.public_slots()
    except StoreError:
        payload = {
            "logo": None,
            "slides": [
                {"slot": "carousel.1", "url": None},
                {"slot": "carousel.2", "url": None},
                {"slot": "carousel.3", "url": None},
                {"slot": "carousel.4", "url": None},
            ],
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
    file: UploadFile = File(...),
    member: dict = Depends(require_admin),
) -> ImageOut:
    data, content_type, ext, original = await _read_upload(file)
    path = write_upload(data, ext)
    try:
        image = store.add_library_image(path, original, content_type, member["memberid"])
    except (StoreError, MediaError) as exc:
        delete_stored_file(path)
        _raise_store(exc)
    return ImageOut(**image)


@api.post("/media/{image_id}/replace", response_model=ImageOut)
async def replace_media(
    image_id: int,
    file: UploadFile = File(...),
    member: dict = Depends(require_admin),
) -> ImageOut:
    del member
    data, content_type, ext, original = await _read_upload(file)
    path = write_upload(data, ext)
    try:
        image = store.replace_image(image_id, path, original, content_type)
    except (StoreError, MediaError) as exc:
        delete_stored_file(path)
        _raise_store(exc)
    return ImageOut(**image)


@api.patch("/media/{image_id}", response_model=ImageOut)
def assign_media(
    image_id: int,
    body: SlotIn,
    member: dict = Depends(require_admin),
) -> ImageOut:
    del member
    try:
        slot = normalize_slot(body.slot)
        image = store.assign_slot(image_id, slot)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
    return ImageOut(**image)


@api.delete("/media/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(image_id: int, member: dict = Depends(require_admin)) -> Response:
    del member
    try:
        store.delete_image(image_id)
    except (StoreError, MediaError) as exc:
        _raise_store(exc)
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image was not found.")
    try:
        path = absolute_path(image["path"])
    except MediaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image was not found.") from exc
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image was not found.")
    return FileResponse(path, media_type=image["content_type"], headers={"Cache-Control": "no-cache"})


app.include_router(api)
