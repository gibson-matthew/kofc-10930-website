from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.jwt import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.models.role import Role


# OAuth2 scheme for Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ============================================================
#  GET CURRENT USER
# ============================================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract user from JWT token and load from database.
    """
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = int(payload.get("sub"))

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # You said inactive users *can* log in, so no check here.
    return user


# ============================================================
#  ROLE CHECKING
# ============================================================

async def require_roles(
    required_roles: list[str],
    user: User = Depends(get_current_user),
):
    """
    Ensure the user has at least one of the required roles.
    """
    user_role_names = [role.name for role in user.roles]

    if not any(role in user_role_names for role in required_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return user


# ============================================================
#  ADMIN SHORTCUT
# ============================================================

async def get_current_admin(
    user: User = Depends(get_current_user),
):
    """
    Shortcut dependency for admin-only routes.
    """
    user_role_names = [role.name for role in user.roles]

    if "admin" not in user_role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user
