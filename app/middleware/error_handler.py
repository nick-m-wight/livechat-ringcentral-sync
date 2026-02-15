"""Global error handling middleware."""

import traceback
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

from app.utils.logger import get_logger

logger = get_logger(__name__)


async def error_handler_middleware(request: Request, call_next: Callable) -> Response:
    """
    Global error handling middleware.

    Catches all unhandled exceptions and returns appropriate JSON responses.

    Args:
        request: The incoming request
        call_next: The next middleware or endpoint handler

    Returns:
        Response object
    """
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            traceback=traceback.format_exc(),
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "error": str(exc) if request.app.debug else "An unexpected error occurred",
            },
        )
