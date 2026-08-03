from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.auth_service import AuthService
from app.core.rbac import get_current_user
from app.models.user import User

from app.schemas.auth_schemas import (
    LoginRequest,
    LoginResponse,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    MeResponse,
    RolesResponse,
)


router = APIRouter()


# ============================================================
#  LOGIN
# ============================================================

@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login using membership_number + password.
    """

    user = await AuthService.authenticate_user(
        db=db,
        membership_number=payload.membership_number,
        password=payload.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid membership number or password",
        )

    token = await AuthService.create_login_token(user)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
    )


# ============================================================
#  LOGOUT (client-side only)
# ============================================================

@router.post("/logout")
async def logout():
    """
    Logout is handled client-side by deleting the token.
    """
    return {"message": "Logged out"}


# ============================================================
#  PASSWORD RESET (REQUEST)
# ============================================================

@router.post("/reset-password")
async def request_password_reset(
    payload: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a password reset token and send email.
    """

    # Lookup user by email
    result = await db.execute(
        User.__table__.select().where(User.email == payload.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found with that email",
        )

    token = await AuthService.generate_password_reset_token(user.id)

    # Here you would send the email via Celery task
    # email_tasks.send_password_reset_email(user.email, token)

    return {"message": "Password reset email sent"}


# ============================================================
#  PASSWORD RESET (CONFIRM)
# ============================================================

@router.post("/reset-password/confirm")
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate reset token and update password.
    """

    success = await AuthService.reset_password(
        db=db,
        token=payload.token,
        new_password=payload.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    return {"message": "Password updated successfully"}


# ============================================================
#  CURRENT USER
# ============================================================

@router.get("/me", response_model=MeResponse)
async def get_me(
    user: User = Depends(get_current_user),
):
    """
    Return current user profile.
    """

    return MeResponse(
        id=user.id,
        membership_number=user.membership_number,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        address=user.address,
        is_active=user.is_active,
        # roles=[role.name for role in user.roles],
        # roles=[ur.role.name for ur in user.user_roles],
    )


# ============================================================
#  ROLES
# ============================================================

@router.get("/roles", response_model=RolesResponse)
async def get_roles(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return list of role names for the current user.
    """

    roles = await AuthService.get_user_roles(db, user.id)
    return RolesResponse(roles=roles)
