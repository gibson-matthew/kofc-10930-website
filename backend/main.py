"""Council 10930 API. Run from the repo root:

..\\venv\\Scripts\\uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db import store

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

app = FastAPI(title="Council 10930")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):517\d",
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


class LoginIn(BaseModel):
    membership_id: str = ""
    password: str = ""


class LoginOut(BaseModel):
    success: bool
    token: str
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


@api.post("/auth/login")
def login(body: LoginIn) -> LoginOut:
    result = store.login(body.membership_id, body.password)
    return LoginOut(**result)


@api.get("/pages/public")
def get_public_page() -> PageOut:
    return PageOut(**store.get_page("public"))


@api.get("/pages/member")
def get_member_page() -> PageOut:
    return PageOut(**store.get_page("member"))


@api.put("/pages/member")
def save_member_page(body: SaveIn) -> PageOut:
    payload = [block.model_dump() for block in body.blocks]
    return PageOut(**store.save_member(payload))


app.include_router(api)
