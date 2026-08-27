import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import engine, AsyncSessionLocal
from app.models.role import Role
from app.models.user import User
from app.services.auth_service import AuthService


DEFAULT_ROLES = [
    "member",
    "admin",
    "grand_knight",
    "fs",
    "treasurer",
    "webmaster",
]


async def create_roles(db: AsyncSession):
    """
    Create default roles if they do not exist.
    """

    result = await db.execute(select(Role))
    existing = {role.name for role in result.scalars().all()}

    for role_name in DEFAULT_ROLES:
        if role_name not in existing:
            role = Role(name=role_name)
            db.add(role)

    await db.commit()


async def create_admin_user(db: AsyncSession):
    """
    Create an initial admin user if none exists.
    """

    result = await db.execute(
        select(User).join(User.roles).where(Role.name == "admin")
    )
    admin_exists = result.scalar_one_or_none()

    if admin_exists:
        return

    # Create admin user
    admin_user = await AuthService.create_user(
        db=db,
        membership_number="000001",
        email="admin@example.com",
        password="ChangeMe123!",
        first_name="System",
        last_name="Administrator",
        role_names=["admin"],
    )

    print(f"Created admin user: {admin_user.email}")


async def init_db():
    """
    Initialize database with roles and admin user.
    """

    async with AsyncSessionLocal() as db:
        await create_roles(db)
        await create_admin_user(db)


if __name__ == "__main__":
    asyncio.run(init_db())
