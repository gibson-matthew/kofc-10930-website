from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.auth.jwt import decode_access_token


# ============================================================
#  OAUTH2 SCHEME
# ============================================================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.LOGIN_ENDPOINT)


# ============================================================
#  GET CURRENT USER (ASYNC)
# ============================================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract JWT from Authorization header, decode it,
    validate it, and return the corresponding User object.
    """

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # AsyncSession requires select() instead of db.query()
    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


# ============================================================
#  ROLE CHECKING DEPENDENCY
# ============================================================

def require_roles(required_roles: list[str]):
    """
    Dependency factory that ensures the current user has
    at least one of the required roles.
    """

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ):
        # current_user.roles is now a proper many-to-many list of Role objects
        user_roles = [role.name for role in current_user.roles]

        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return role_checker
