from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Config & Logging
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.logging import logging_middleware

# Models
import app.models
# from app.models import events
# from app.models import event_volunteers

# Public Routers
from app.routers.auth_router import router as auth_router
# from app.routers.officer_router import router as officer_router
from app.routers.public_router import router as public_router
from app.routers.prayer_router import router as prayer_router
from app.routers.member_router import router as member_router
# from app.routers.media_router import router as media_router

# Admin Routers
# from app.routers.admin.admin_router import router as admin_router
# from app.routers.admin.admin_content_router import router as admin_content_router
# from app.routers.admin.admin_events_router import router as admin_events_router
# from app.routers.admin.admin_leadership_router import router as admin_leadership_router
# from app.routers.admin.admin_programs_router import router as admin_programs_router
# from app.routers.admin.admin_media_router import router as admin_media_router
# from app.routers.admin.admin_members_router import router as admin_members_router
# from app.routers.admin.admin_documents_router import router as admin_documents_router
# from app.routers.admin.admin_communications_router import router as admin_communications_router
# from app.routers.admin.admin_market_router import router as admin_market_router
# from app.routers.admin.admin_webmaster_router import router as admin_webmaster_router
# from app.routers.admin.admin_governance_router import router as admin_governance_router

def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title="Council Management API",
        version="0.2.0",
        description="Backend API for public, member, and admin features."
    )

    # Logging middleware
    app.middleware("http")(logging_middleware)

    # Defined Origins
    # origins = [
    #     "http://localhost",
    #     "http://localhost:5173"
    # ]

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        # allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Public routes
    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    app.include_router(public_router, prefix="/api/public", tags=["Public"])
    # app.include_router(officer_router, prefix="/api/officer", tags=["Officer"])
    app.include_router(prayer_router, prefix="/api/prayer", tags=["Prayer"])
    app.include_router(member_router, prefix="/api/member", tags=["Member"])
    # app.include_router(media_router, prefix="/api/media", tags=["Media"])

    # Admin routes
    # app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
    # app.include_router(admin_content_router, prefix="/api/admin", tags=["Admin - Content"])
    # app.include_router(admin_events_router, prefix="/api/admin", tags=["Admin - Events"])
    # app.include_router(admin_leadership_router, prefix="/api/admin", tags=["Admin - Leadership"])
    # app.include_router(admin_programs_router, prefix="/api/admin", tags=["Admin - Programs"])
    # app.include_router(admin_media_router, prefix="/api/admin", tags=["Admin - Media"])
    # app.include_router(admin_members_router, prefix="/api/admin", tags=["Admin - Members"])
    # app.include_router(admin_documents_router, prefix="/api/admin", tags=["Admin - Documents"])
    # app.include_router(admin_communications_router, prefix="/api/admin", tags=["Admin - Communications"])
    # app.include_router(admin_market_router, prefix="/api/admin", tags=["Admin - Market"])
    # app.include_router(admin_webmaster_router, prefix="/api/admin", tags=["Admin - Webmaster"])
    # app.include_router(admin_governance_router, prefix="/api/admin", tags=["Admin - Governance"])

    return app

app = create_app()