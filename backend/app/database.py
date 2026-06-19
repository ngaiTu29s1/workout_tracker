from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from backend.app.config import settings

class Base(DeclarativeBase):
    pass

# Create async engine and session factory
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # Set to True to log SQL statements for easy debugging during local setup
    future=True
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency to get session in routers
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Database initialization function
async def init_db() -> None:
    # Import all models here so they register on Base.metadata
    from backend.app.models.exercise import ExerciseMaster
    from backend.app.models.preset import WeeklyPreset
    from backend.app.models.workout_log import DailyWorkoutLog
    from backend.app.models.stats import WorkoutAggregatedStats

    async with engine.begin() as conn:
        # Create all tables if they do not exist
        await conn.run_sync(Base.metadata.create_all)
