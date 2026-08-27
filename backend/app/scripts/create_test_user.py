import sys
import os
from dotenv import load_dotenv
import asyncio

# Ensure project root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

load_dotenv()

from app.db.session import AsyncSessionLocal
from app.services.auth_service import AuthService
from app.models.role import Role
from sqlalchemy import select, insert


ROLES = [
    "Member",
    "Admin",
    "Grand Knight",
    "Deputy Grand Knight",
    "Chancellor",
    "Recorder",
    "Treasurer",
    "Advocate",
    "Warden",
    "Inside Guard",
    "Outside Guard",
    "Trustee",
    "Financial Secretary",
    "Program Director",
    "Faith Director",
    "Family Director",
    "Community Director",
    "Life Director",
    "Membership Director",
    "Webmaster",
    "Content Manager",
    "Media Coordinator"
]

FIRST_NAMES = [
    "John", "David", "Michael", "Paul", "Luke",
    "Mark", "James", "Andrew", "Peter", "Thomas",
    "Robert", "Anthony", "Joseph", "Stephen", "Daniel"
]

LAST_NAMES = [
    "Knight", "Strong", "Faith", "Helper", "Miller",
    "Johnson", "Garcia", "Martinez", "Lopez", "Davis",
    "Clark", "Bennett", "Reeves", "Foster", "Hayes"
]


async def ensure_roles_exist(db):
    """
    Ensure all roles in ROLES[] exist in the database.
    """
    for role_name in ROLES:
        result = await db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()

        if not role:
            await db.execute(insert(Role).values(name=role_name))
            print(f"Created role: {role_name}")

    await db.commit()


async def main():
    async with AsyncSessionLocal() as db:

        # 1. Ensure roles exist and commit BEFORE creating users
        await ensure_roles_exist(db)

        # 2. Create users and assign roles
        for i, role in enumerate(ROLES, start=1):
            first = FIRST_NAMES[i % len(FIRST_NAMES)]
            last = LAST_NAMES[i % len(LAST_NAMES)]

            membership_number = f"91000{i:03d}"
            email = f"{role.lower().replace(' ', '_')}@example.com"
            password = "TestPassword123!"
            phone = f"555-100-{1000+i}"
            address = f"{100+i} Council Drive"

            user = await AuthService.create_user(
                db=db,
                membership_number=membership_number,
                email=email,
                password=password,
                first_name=first,
                last_name=last,
                phone=phone,
                address=address,
                role_names=[role]
            )

            print(f"Created user for role '{role}': {user.id} {email}")


if __name__ == "__main__":
    asyncio.run(main())
