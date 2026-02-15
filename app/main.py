"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, update

from app.config import settings
from app.utils.logger import get_logger
from app.middleware.error_handler import error_handler_middleware
from app.middleware.request_logging import request_logging_middleware
from app.api.health import router as health_router
from app.api.data import router as data_router
from app.api.webhooks.livechat import router as livechat_webhook_router
from app.api.webhooks.ringcentral import router as ringcentral_webhook_router
from app.db.session import AsyncSessionLocal
from app.db.models import Agent, AgentState, Conversation

logger = get_logger(__name__)


async def reset_demo_state() -> None:
    """
    Reset demo state on startup.

    - Ends all active conversations
    - Sets all agents to available state
    """
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now()

            # End all active conversations
            result = await db.execute(
                update(Conversation)
                .where(Conversation.status == "active")
                .values(
                    status="ended",
                    ended_at=now,
                )
            )
            ended_count = result.rowcount

            if ended_count > 0:
                logger.info("ended_active_conversations", count=ended_count)

            # Get all agents
            result = await db.execute(select(Agent))
            agents = result.scalars().all()

            # Set all agents to available state
            agent_count = 0
            for agent in agents:
                agent_state = AgentState(
                    agent_id=agent.id,
                    livechat_status="accepting_chats",
                    ringcentral_presence="Available",
                    reason="available",
                    state_changed_at=now,
                    created_at=now,
                )
                db.add(agent_state)
                agent_count += 1

            await db.commit()

            logger.info(
                "demo_state_reset_complete",
                ended_conversations=ended_count,
                available_agents=agent_count,
            )

        except Exception as e:
            logger.error("demo_state_reset_failed", error=str(e))
            await db.rollback()
            # Don't fail app startup if reset fails
            pass


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

    # Reset demo state (end active conversations, set agents to available)
    await reset_demo_state()

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

# Data API routers
app.include_router(data_router, prefix="/api", tags=["data"])

# Webhook routers
app.include_router(livechat_webhook_router, prefix="/webhooks/livechat")
app.include_router(ringcentral_webhook_router, prefix="/webhooks/ringcentral")

# Mount static files for frontend demo
app.mount("/demo", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "message": "LiveChat-RingCentral Sync API",
        "version": "0.1.0",
        "status": "running",
    }
