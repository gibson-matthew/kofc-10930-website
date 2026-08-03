from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    membership_number: str
    password: str = Field(..., max_length=72)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


class MeResponse(BaseModel):
    id: int
    membership_number: str
    email: str
    first_name: str
    last_name: str
    phone: str | None
    address: str | None
    is_active: bool
    # roles: list[str]


class RolesResponse(BaseModel):
    roles: list[str]
