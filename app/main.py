"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.logger import get_logger
from app.middleware.error_handler import error_handler_middleware
from app.middleware.request_logging import request_logging_middleware
from app.api.health import router as health_router
from app.api.webhooks.livechat import router as livechat_webhook_router
from app.api.webhooks.ringcentral import router as ringcentral_webhook_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan events.

    Handles startup and shutdown operations.
    """
    # Startup
    logger.info(
        "application_starting",
        env=settings.APP_ENV,
        debug=settings.APP_DEBUG,
    )

    yield

    # Shutdown
    logger.info("application_shutting_down")


# Create FastAPI application
app = FastAPI(
    title="LiveChat-RingCentral Sync",
    description="Bidirectional synchronization system between LiveChat and RingCentral",
    version="0.1.0",
    debug=settings.APP_DEBUG,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.middleware("http")(request_logging_middleware)
app.middleware("http")(error_handler_middleware)

# Include routers
app.include_router(health_router)

# Webhook routers
app.include_router(livechat_webhook_router, prefix="/webhooks/livechat")
app.include_router(ringcentral_webhook_router, prefix="/webhooks/ringcentral")


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "message": "LiveChat-RingCentral Sync API",
        "version": "0.1.0",
        "status": "running",
    }
