from http.client import HTTPException

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.homepage_hero_image_service import homepage_hero_image_service
from app.schemas.homepage_hero_schemas import (
    HomepageHeroImageCreate,
    HomepageHeroImageUpdate,
    HomepageHeroImageResponse,
)

from app.db.session import get_db

router = APIRouter()


@router.post("/homepage/hero-images", response_model=HomepageHeroImageResponse)
async def create_hero_image(
    payload: HomepageHeroImageCreate,
    db: AsyncSession = Depends(get_db),
):
    return await homepage_hero_image_service.create(db, payload.dict())


@router.put("/homepage/hero-images/{id}", response_model=HomepageHeroImageResponse)
async def update_hero_image(
    id: int,
    payload: HomepageHeroImageUpdate,
    db: AsyncSession = Depends(get_db),
):
    updated = await homepage_hero_image_service.update(db, id, payload.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Hero image not found")
    return updated


@router.delete("/homepage/hero-images/{id}")
async def delete_hero_image(id: int, db: AsyncSession = Depends(get_db)):
    deleted = await homepage_hero_image_service.delete(db, id)
    return {"success": deleted}
