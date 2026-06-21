import os
import asyncio

# Set TESTING environment variable and target test DB before importing app/database
os.environ["TESTING"] = "True"
os.environ["POSTGRES_DB"] = "fitness_os_test"

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.main import app
from backend.app.database import get_db, async_session_maker, engine, Base
from backend.app.config import settings

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Make sure tables exist once for the entire test session
    loop = asyncio.new_event_loop()
    
    async def _create_db():
        user = settings.POSTGRES_USER
        password = settings.POSTGRES_PASSWORD
        host = settings.POSTGRES_HOST
        port = settings.POSTGRES_PORT
        admin_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/postgres"
        
        # Use autocommit connection to allow CREATE DATABASE command
        admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
        async with admin_engine.connect() as conn:
            exists = await conn.scalar(text("SELECT 1 FROM pg_database WHERE datname='fitness_os_test'"))
            if not exists:
                await conn.execute(text("CREATE DATABASE fitness_os_test"))
        await admin_engine.dispose()

    async def _setup():
        # Ensure test database exists first
        await _create_db()
        # Drop and create tables in the isolated test DB
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            
    loop.run_until_complete(_setup())
    loop.close()
    
    yield
    
    # Re-seed the database after all tests complete so it is ready for dev use
    loop = asyncio.new_event_loop()
    async def _teardown_seed():
        from backend.app.seed.seed_data import seed_db
        async with async_session_maker() as session:
            # Clean database first
            await session.execute(text("DELETE FROM workout_aggregated_stats"))
            await session.execute(text("DELETE FROM daily_workout_log"))
            await session.execute(text("DELETE FROM daily_overrides"))
            await session.execute(text("DELETE FROM weekly_presets"))
            await session.execute(text("DELETE FROM exercise_master"))
            await session.execute(text("DELETE FROM exercise_pool"))
            await session.commit()
            
            # Seed default data
            await seed_db(session)
    loop.run_until_complete(_teardown_seed())
    loop.close()

@pytest.fixture(autouse=True)
async def clean_database():
    """
    Clean the database before each test by deleting rows from all tables.
    This avoids expensive schema alterations and locks.
    """
    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM workout_aggregated_stats"))
        await session.execute(text("DELETE FROM daily_workout_log"))
        await session.execute(text("DELETE FROM daily_overrides"))
        await session.execute(text("DELETE FROM weekly_presets"))
        await session.execute(text("DELETE FROM exercise_master"))
        await session.execute(text("DELETE FROM exercise_pool"))
        await session.commit()
    yield
    # Dispose engine pool to avoid event loop conflicts in asyncpg
    await engine.dispose()

@pytest.fixture
async def db_session() -> AsyncSession:
    """
    Provide a fresh database session for the test.
    """
    async with async_session_maker() as session:
        yield session

@pytest.fixture
async def client() -> AsyncClient:
    """
    Provide an AsyncClient for testing.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers.update({"X-API-Key": settings.FITNESS_OS_API_KEY})
        yield ac
