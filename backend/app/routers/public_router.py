from http.client import HTTPException

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db

# Services
from app.services import (
    news_service,
    events_service,
    officers_service,
    directors_service,
    programs_service,
    prayer_service,
    recognition_service,
    memoriam_service,
    media_album_service,
    media_item_service,
    links_service,
    newsletter_service,
    market_service,
    jobs_service,
    degree_schedule_service,
)

from app.schemas.media_schemas import (
    PhotoResponse,
    AlbumResponse,
    AlbumWithPhotosResponse,
)

router = APIRouter()


# ============================================================
#  PUBLIC STATUS CHECK
# ============================================================

@router.get("/status")
async def public_status():
    return {"status": "ok", "message": "Public API is running"}


# ============================================================
#  NEWS
# ============================================================
@router.get("/news")
async def get_public_news(db: AsyncSession = Depends(get_db)):
    """
    Returns all published news items.
    """
    return await news_service.list(db)


@router.get("/news/{news_id}")
async def get_public_news_item(news_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns a single published news item.
    """
    item = await news_service.get(db, news_id)
    if not item or not getattr(item):
        return {"error": "News item not found"}
    return item

# ============================================================
#  RECOGNITION
# ============================================================
@router.get("/recognition")
async def get_public_recognition(db: AsyncSession = Depends(get_db)):
    """
    Returns all public recognition entries.
    """
    return await recognition_service.list(db)

# ============================================================
#  MEMORIAM
# ============================================================
@router.get("/memoriam")
async def get_public_memoriam(db: AsyncSession = Depends(get_db)):
    """
    Returns all memoriam entries.
    """
    return await memoriam_service.list(db)

# ============================================================
#  LINKS
# ============================================================
@router.get("/links")
async def get_public_links(db: AsyncSession = Depends(get_db)):
    """
    Returns all public links.
    """
    return await links_service.list(db)

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
    if not event or not getattr(event, "is_public", False):
        return {"error": "Event not found"}
    return event


# ============================================================
#  CURRENT OFFICERS
# ============================================================
@router.get("/officers")
async def get_public_officers(db: AsyncSession = Depends(get_db)):
    """
    Returns all officers.
    """
    return await officers_service.list(db)

@router.get("/officers/past-grand-knights")
async def get_public_past_grand_knights(db: AsyncSession = Depends(get_db)):
    """
    Returns all past Grand Knights.
    """
    return await officers_service.list(db, filters={"position": "Past Grand Knight"})

# ============================================================
#  DIRECTORS
# ============================================================
@router.get("/directors")
async def get_public_directors(db: AsyncSession = Depends(get_db)):
    """
    Returns all directors.
    """
    return await directors_service.list(db)

@router.get("/directors/{director_id}")
async def get_public_director(director_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns a single director.
    """
    director = await directors_service.get(db, director_id)
    if not director:
        return {"error": "Director not found"}
    return director

# ============================================================
#  PROGRAMS
# ============================================================
@router.get("/programs")
async def get_public_programs(db: AsyncSession = Depends(get_db)):
    """
    Returns all programs.
    """
    return await programs_service.list(db)

@router.get("/programs/{category}")
async def get_public_programs_by_category(category: str, db: AsyncSession = Depends(get_db)):
    """
    Returns programs filtered by category.
    """
    return await programs_service.list(db, filters={"category": category})

# ============================================================
#  PRAYERS
# ============================================================
@router.get("/prayers")
async def get_public_prayers(db: AsyncSession = Depends(get_db)):
    """
    Returns all public prayer requests marked as shareable.
    """
    return await prayer_service.list(db)

# ============================================================
#  NEWSLETTERS
# ============================================================
@router.get("/newsletters")
async def get_public_newsletters(db: AsyncSession = Depends(get_db)):
    """
    Returns all public newsletters.
    """
    return await newsletter_service.list(db)

# ============================================================
#  PHOTOS || MEDIA SERVICE & MEDIA SERVICE MODEL REMOVED.
# ============================================================
# @router.get("/photos")
# async def get_public_photos(db: AsyncSession = Depends(get_db)):
#     """
#     Returns all public photos (flat list).
#     """
#     return await media_service.list_items(db)

# @router.get("/photos/{album_id}")
# async def get_public_photos_by_album(album_id: int, db: AsyncSession = Depends(get_db)):
#     """
#     Returns all photos for a given album.
#     """
#     album_data = await media_service.get_album_with_items(db, album_id)
#     if not album_data:
#         return {"error": "Album not found"}
#     return album_data

# ============================================================
#  PUBLIC PHOTOS (all photos)
# ============================================================

@router.get("/photos")
async def get_public_photos(db: AsyncSession = Depends(get_db)):
    """
    Returns all public photos.
    """
    photos = await media_item_service.list(db)
    return photos


# ============================================================
#  PUBLIC PHOTOS BY ALBUM
# ============================================================

@router.get("/photos/{album_id}")
async def get_public_photos_by_album(album_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns all photos belonging to a specific album.
    """
    photos = await media_item_service.list(db, filters={"album_id": album_id})
    return photos


# ============================================================
#  PUBLIC ALBUM LIST
# ============================================================

@router.get("/albums")
async def get_public_albums(db: AsyncSession = Depends(get_db)):
    """
    Returns all public photo albums.
    """
    albums = await media_album_service.list(db)
    return albums


# ============================================================
#  PUBLIC ALBUM DETAIL (album + photos)
# ============================================================

@router.get("/albums/{album_id}")
async def get_public_album_detail(album_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns a single album and its associated photos.
    """
    album = await media_album_service.get(db, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    photos = await media_item_service.list(db, filters={"album_id": album_id})

    return {
        "album": album,
        "photos": photos,
    }

# ============================================================
#  MARKET
# ============================================================
@router.get("/market")
async def get_public_market(db: AsyncSession = Depends(get_db)):
    """
    Returns all market items.
    """
    return await market_service.list(db)

@router.get("/market/category/{category_id}")
async def get_public_market_category(category_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns market items filtered by category.
    """
    return await market_service.list(db, filters={"category_id": category_id})

# ============================================================
#  JOBS
# ============================================================
@router.get("/jobs")
async def get_public_jobs(db: AsyncSession = Depends(get_db)):
    """
    Returns all public job postings.
    """
    return await jobs_service.list(db)

# ============================================================
#  DEGREE SCHEDULE
# ============================================================
@router.get("/degree-schedule")
async def get_public_degree_schedule(db: AsyncSession = Depends(get_db)):
    """
    Returns all degree schedule entries.
    """
    return await degree_schedule_service.list(db)
