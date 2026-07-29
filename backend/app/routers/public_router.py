from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
# from app.services.news_service import news_service
# from app.services.events_service import events_service
from app.services.officers_service import officers_service
# from app.services.media_service import media_service


router = APIRouter()


# ============================================================
#  PUBLIC STATUS CHECK
# ============================================================

@router.get("/status")
async def public_status():
    return {"status": "ok", "message": "Public API is running"}


# ============================================================
#  PUBLIC NEWS
# ============================================================

@router.get("/news")
async def get_public_news(db: AsyncSession = Depends(get_db)):
    """
    Returns all published news items.
    """
    return await news_service.list(db, filters={"is_published": True})


@router.get("/news/{news_id}")
async def get_public_news_item(news_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns a single published news item.
    """
    item = await news_service.get(db, news_id)
    if not item or not item.is_published:
        return {"error": "News item not found"}
    return item


# ============================================================
#  PUBLIC EVENTS
# ============================================================

@router.get("/events")
async def get_public_events(db: AsyncSession = Depends(get_db)):
    """
    Returns all public events.
    """
    return await events_service.list(db, filters={"is_public": True})


@router.get("/events/{event_id}")
async def get_public_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns a single public event.
    """
    event = await events_service.get(db, event_id)
    if not event or not event.is_public:
        return {"error": "Event not found"}
    return event

# ============================================================
#  CURRENT OFFICERS & PAST GRAND KNIGHTS
# ============================================================
# │   ├── GET /public/officers
# │   ├── GET /public/officers/past-grand-knights

@router.get("/officers")
async def get_public_officer(db: AsyncSession = Depends(get_db)):
    """
    Returns all public officers.
    """
    return await officers_service.list(db)
    # return await officers_service.list(db, filters={"is_public": True})


# @router.get("/events/{event_id}")
# async def get_public_event(event_id: int, db: AsyncSession = Depends(get_db)):
#     """
#     Returns a single public event.
#     """
#     event = await events_service.get(db, event_id)
#     if not event or not event.is_public:
#         return {"error": "Event not found"}
#     return event


# ============================================================
#  PUBLIC MEDIA (Albums + Items)
# ============================================================

@router.get("/media/albums")
async def get_public_media_albums(db: AsyncSession = Depends(get_db)):
    """
    Returns all public media albums.
    """
    return await media_service.list_albums(db)


@router.get("/media/albums/{album_id}")
async def get_public_media_album(album_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns a single public media album with items.
    """
    return await media_service.get_album_with_items(db, album_id)
