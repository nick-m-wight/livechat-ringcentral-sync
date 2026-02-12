"""FastAPI dependency injection functions."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Yields:
        AsyncSession: Database session
    """
    async for session in get_db():
        yield session
