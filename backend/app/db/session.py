from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Base model class for all ORM models
Base = declarative_base()

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    future=True,
    echo=settings.DEBUG,
)

# Create session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Dependency for FastAPI routes
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
