from typing import Type, TypeVar, List, Optional, Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.db.session import Base


ModelType = TypeVar("ModelType", bound=Base)


class BaseCRUDService:
    """
    Reusable async CRUD service for SQLAlchemy models.
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model

    # ============================================================
    #  GET BY ID
    # ============================================================

    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.unique().scalar_one_or_none()   # FIXED

    # ============================================================
    #  LIST (OPTIONAL FILTERS)
    # ============================================================

    async def list(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ModelType]:

        query = select(self.model)

        if filters:
            for field, value in filters.items():
                query = query.where(getattr(self.model, field) == value)

        if limit:
            query = query.limit(limit)

        if offset:
            query = query.offset(offset)

        result = await db.execute(query)
        return result.unique().scalars().all()        # FIXED

    # ============================================================
    #  CREATE
    # ============================================================

    async def create(self, db: AsyncSession, data: Dict[str, Any]) -> ModelType:
        obj = self.model(**data)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    # ============================================================
    #  UPDATE
    # ============================================================

    async def update(
        self,
        db: AsyncSession,
        id: int,
        data: Dict[str, Any],
    ) -> Optional[ModelType]:

        await db.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**data)
        )
        await db.commit()

        return await self.get(db, id)

    # ============================================================
    #  DELETE
    # ============================================================

    async def delete(self, db: AsyncSession, id: int) -> bool:
        await db.execute(
            delete(self.model).where(self.model.id == id)
        )
        await db.commit()
        return True
