from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.base_crud_service import BaseCRUDService
from app.models.officers import Officer
from app.models.user import User


class OfficersService(BaseCRUDService):
    async def get_current_officers(self, db: AsyncSession):
        """
        Return officers with name + photo for public display.
        """

        result = await db.execute(
            select(Officer).join(Officer.user)
        )
        officers = result.scalars().all()

        output = []
        for officer in officers:
            output.append({
                "id": officer.id,
                "position": officer.position,
                "name": f"{officer.user.first_name} {officer.user.last_name}",
                "photo": officer.user.profile_photo,
            })

        return output


officers_service = OfficersService(Officer)
