import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.main import app
from httpx import AsyncClient


TEST_DATABASE_URL = "postgresql+asyncpg://postgres@localhost/postgres"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return engine


@pytest.fixture
async def db_session(test_engine):
    async_session = sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session, monkeypatch):
    async def override_get_db():
        yield db_session

    app.dependency_overrides = {}
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
