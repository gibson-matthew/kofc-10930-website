from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.rbac import get_current_user, get_current_admin
from app.services.base_crud_service import BaseCRUDService


def create_crud_router(
    *,
    model,
    schema_read,
    schema_create,
    schema_update,
    service: BaseCRUDService,
    prefix: str,
    tags: list[str],
    require_admin: bool = False,
):
    """
    Generate a CRUD router for any model using BaseCRUDService.
    """

    router = APIRouter(prefix=prefix, tags=tags)

    # ============================================================
    #  LIST
    # ============================================================

    @router.get("/", response_model=list[schema_read])
    async def list_items(
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_admin if require_admin else get_current_user),
    ):
        return await service.list(db)

    # ============================================================
    #  GET BY ID
    # ============================================================

    @router.get("/{item_id}", response_model=schema_read)
    async def get_item(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_admin if require_admin else get_current_user),
    ):
        item = await service.get(db, item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found",
            )
        return item

    # ============================================================
    #  CREATE
    # ============================================================

    @router.post("/", response_model=schema_read)
    async def create_item(
        payload: schema_create,
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_admin if require_admin else get_current_user),
    ):
        item = await service.create(db, payload.dict())
        return item

    # ============================================================
    #  UPDATE
    # ============================================================

    @router.put("/{item_id}", response_model=schema_read)
    async def update_item(
        item_id: int,
        payload: schema_update,
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_admin if require_admin else get_current_user),
    ):
        updated = await service.update(db, item_id, payload.dict())
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found",
            )
        return updated

    # ============================================================
    #  DELETE
    # ============================================================

    @router.delete("/{item_id}")
    async def delete_item(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_admin if require_admin else get_current_user),
    ):
        await service.delete(db, item_id)
        return {"message": "Item deleted"}

    return router
