from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, insert

from app.core.security import hash_password, verify_password
from app.auth.jwt import (
    create_access_token,
    create_password_reset_token,
    verify_password_reset_token,
)
from app.models.user import User
from app.models.role import Role
from app.models.user_roles import UserRole


MAX_PASSWORD_LENGTH = 72


class AuthService:

    # ============================================================
    #  LOGIN
    # ============================================================

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        membership_number: str,
        password: str,
    ) -> Optional[User]:
        """
        Validate membership_number + password.
        """

        # Enforce bcrypt max length
        if len(password) > MAX_PASSWORD_LENGTH:
            return None

        # result = await db.execute(
        #     select(User).where(User.membership_number == membership_number)
        # )
        # user = result.unique().scalar_one_or_none()

        result = await db.execute(
            select(User)
                .options(selectinload(User.roles))
                .where(User.membership_number == membership_number)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user

    @staticmethod
    async def create_login_token(user: User) -> str:
        """
        Create JWT access token for a user.
        """

        role_names = [role.name for role in user.roles]

        return create_access_token(
            user_id=user.id,
            membership_number=user.membership_number,
            email=user.email,
            roles=role_names,
        )

    # ============================================================
    #  PASSWORD RESET
    # ============================================================

    @staticmethod
    async def generate_password_reset_token(user_id: int) -> str:
        return create_password_reset_token(user_id)

    @staticmethod
    async def reset_password(
        db: AsyncSession,
        token: str,
        new_password: str,
    ) -> bool:
        """
        Validate reset token and update password.
        """

        # Enforce bcrypt max length
        if len(new_password) > MAX_PASSWORD_LENGTH:
            return False

        user_id = verify_password_reset_token(token)
        if not user_id:
            return False

        hashed = hash_password(new_password)

        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(password_hash=hashed)
        )
        await db.commit()

        return True

    # ============================================================
    #  ROLE LOOKUP
    # ============================================================

    @staticmethod
    async def get_user_roles(db: AsyncSession, user_id: int) -> List[str]:
        result = await db.execute(
            select(Role.name)
            .join(Role.users)
            .where(User.id == user_id)
        )
        return result.scalars().all()

    # ============================================================
    #  CREATE USER
    # ============================================================

    @staticmethod
    async def create_user(
        db: AsyncSession,
        membership_number: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        role_names: Optional[List[str]] = None,
    ) -> User:
        """
        Create a new user with optional roles.
        """

        # Enforce bcrypt max length
        if len(password) > MAX_PASSWORD_LENGTH:
            raise ValueError("Password cannot exceed 72 characters.")

        hashed = hash_password(password)

        user = User(
            membership_number=membership_number,
            email=email,
            password_hash=hashed,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            address=address,
        )

        db.add(user)
        await db.flush()  # get user.id

        if role_names:
            result = await db.execute(
                select(Role).where(Role.name.in_(role_names))
            )
            roles = result.scalars().all()

            for role in roles:
                await db.execute(
                    insert(UserRole).values(
                        user_id=user.id,
                        role_id=role.id
                    )
                )

        await db.commit()
        await db.refresh(user)

        return user
