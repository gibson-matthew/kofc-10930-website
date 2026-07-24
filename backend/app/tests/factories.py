from app.models.user import User
from app.models.role import Role
from app.models.officers import Officer, OfficerPosition
from app.core.security import hash_password


async def create_role(db, name):
    role = Role(name=name)
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


async def create_user(db, membership_number="12345", role=None):
    user = User(
        membership_number=membership_number,
        email=f"{membership_number}@example.com",
        password_hash=hash_password("password"),
        first_name="John",
        last_name="Doe",
        profile_photo="/photos/john.jpg",
    )
    db.add(user)
    await db.flush()

    if role:
        user.roles.append(role)

    await db.commit()
    await db.refresh(user)
    return user


async def create_officer(db, user, position=OfficerPosition.grand_knight):
    officer = Officer(
        user_id=user.id,
        position=position,
    )
    db.add(officer)
    await db.commit()
    await db.refresh(officer)
    return officer
