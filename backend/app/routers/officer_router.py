from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.rbac import require_roles
from app.routers.base_crud_router import create_crud_router

from app.models.officers import Officer
from app.schemas.officers_schemas import OfficerRead, OfficerCreate, OfficerUpdate
from app.services.officers_service import officers_service


# Admin/Webmaster CRUD
router = create_crud_router(
    model=Officer,
    schema_read=OfficerRead,
    schema_create=OfficerCreate,
    schema_update=OfficerUpdate,
    service=officers_service,
    prefix="/admin/officers",
    tags=["Admin - Officers"],
    require_admin=True,  # admin OR webmaster
)


# Public endpoint
public_router = APIRouter(tags=["Officers"])

@public_router.get("/status")
async def public_status():
    return {"status": "ok", "message": "Officer API is running"}

@public_router.get("/current", response_model=list[OfficerRead])
async def get_current_officers(
    db: AsyncSession = Depends(get_db),
):
    return await officers_service.get_current_officers(db)
