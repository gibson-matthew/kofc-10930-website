"""Council 10930 API. Run from the repo root:

..\\.venv\\Scripts\\uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from db import store
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
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
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
def save_member_page(body: SaveIn, member: dict = Depends(get_current_member)) -> PageOut:
    del member
    payload = [block.model_dump() for block in body.blocks]
    return PageOut(**store.save_member(payload))


app.include_router(api)
