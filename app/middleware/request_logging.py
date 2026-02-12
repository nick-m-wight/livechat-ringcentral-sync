"""Request and response logging middleware."""

import time
from typing import Callable
from fastapi import Request, Response

from app.utils.logger import get_logger

logger = get_logger(__name__)


async def request_logging_middleware(request: Request, call_next: Callable) -> Response:
    """
    Log incoming requests and outgoing responses.

    Args:
        request: The incoming request
        call_next: The next middleware or endpoint handler

    Returns:
        Response object
    """
    start_time = time.time()

    # Log incoming request
    logger.info(
        "incoming_request",
        method=request.method,
        path=request.url.path,
        client_host=request.client.host if request.client else None,
    )

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response
    logger.info(
        "outgoing_response",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_seconds=round(duration, 3),
    )

    return response
