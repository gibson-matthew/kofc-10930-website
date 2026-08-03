import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.services.auth_service import AuthService


async def main():
    async with AsyncSessionLocal() as db:
        user = await AuthService.create_user(
            db=db,
            membership_number="91300281",
            email="test@example.com",
            password="TestPassword123!",
            first_name="Test",
            last_name="User",
            phone="555-555-5555",
            address="123 Test Lane",
            role_names=["Member"]  # or ["Admin"], etc.
        )

        print("Created user:", user.id, user.membership_number, user.email)


if __name__ == "__main__":
    asyncio.run(main())
