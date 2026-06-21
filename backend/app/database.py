from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from backend.app.config import settings

class Base(DeclarativeBase):
    pass

from sqlalchemy.pool import NullPool
import os

is_testing = os.getenv("TESTING") == "True"

# Create async engine and session factory
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True to log SQL statements for easy debugging during local setup
    future=True,
    poolclass=NullPool if is_testing else None
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
    pass
