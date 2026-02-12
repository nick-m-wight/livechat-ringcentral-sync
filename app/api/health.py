"""Health check endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.dependencies import get_database_session
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_database_session)) -> dict:
    """
    Health check endpoint.

    Verifies that the application is running and the database is accessible.

    Returns:
        dict: Health status information
    """
    health_status = {
        "status": "healthy",
        "database": "unknown",
    }

    # Check database connectivity
    try:
        result = await db.execute(text("SELECT 1"))
        if result:
            health_status["database"] = "connected"
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"

    return health_status


@router.get("/ping", status_code=status.HTTP_200_OK)
async def ping() -> dict:
    """
    Simple ping endpoint that doesn't check dependencies.

    Returns:
        dict: Pong response
    """
    return {"message": "pong"}
