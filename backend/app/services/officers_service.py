from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.base_crud_service import BaseCRUDService
from app.models.officers import Officer
from app.models.user import User


class OfficersService(BaseCRUDService):
    def __init__(self):
        super().__init__(Officer)

    async def get_current_officers(self, db: AsyncSession):
        """
        Return officers with name + photo for public display.
        """
        result = await db.execute(
            select(Officer).join(Officer.user)
        )
        officers = result.scalars().all()

        return [
            {
                "id": officer.id,
                "position": officer.position,
                "name": f"{officer.user.first_name} {officer.user.last_name}",
                "photo": officer.user.profile_photo,
            }
            for officer in officers
        ]


officers_service = OfficersService()
