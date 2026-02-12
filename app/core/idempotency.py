"""Webhook idempotency handling."""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WebhookEvent
from app.utils.logger import get_logger

logger = get_logger(__name__)


class IdempotencyManager:
    """Manage webhook idempotency using database tracking."""

    def __init__(self, db: AsyncSession):
        """
        Initialize idempotency manager.

        Args:
            db: Database session
        """
        self.db = db

    async def check_and_record_webhook(
        self,
        webhook_id: str,
        platform: str,
        event_type: str,
        payload: dict,
    ) -> tuple[bool, Optional[WebhookEvent]]:
        """
        Check if webhook has been processed and record it if not.

        Args:
            webhook_id: Unique webhook identifier
            platform: Platform name (livechat, ringcentral)
            event_type: Event type
            payload: Webhook payload

        Returns:
            Tuple of (is_duplicate, webhook_event)
            - is_duplicate: True if webhook already exists
            - webhook_event: The webhook event record
        """
        # Check if webhook already exists
        stmt = select(WebhookEvent).where(WebhookEvent.webhook_id == webhook_id)
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(
                "webhook_duplicate_detected",
                webhook_id=webhook_id,
                platform=platform,
                processed=existing.processed,
            )
            return True, existing

        # Create new webhook event record
        import json
        webhook_event = WebhookEvent(
            webhook_id=webhook_id,
            platform=platform,
            event_type=event_type,
            payload_json=json.dumps(payload),
            processed=False,
            received_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )

        self.db.add(webhook_event)
        await self.db.commit()
        await self.db.refresh(webhook_event)

        logger.info(
            "webhook_recorded",
            webhook_id=webhook_id,
            platform=platform,
            event_type=event_type,
        )

        return False, webhook_event

    async def mark_webhook_processed(self, webhook_id: str) -> None:
        """
        Mark webhook as processed.

        Args:
            webhook_id: Unique webhook identifier
        """
        stmt = select(WebhookEvent).where(WebhookEvent.webhook_id == webhook_id)
        result = await self.db.execute(stmt)
        webhook_event = result.scalar_one_or_none()

        if webhook_event:
            webhook_event.processed = True
            webhook_event.processed_at = datetime.utcnow()
            await self.db.commit()

            logger.info("webhook_marked_processed", webhook_id=webhook_id)

    async def increment_retry_count(self, webhook_id: str) -> None:
        """
        Increment retry count for a webhook.

        Args:
            webhook_id: Unique webhook identifier
        """
        stmt = select(WebhookEvent).where(WebhookEvent.webhook_id == webhook_id)
        result = await self.db.execute(stmt)
        webhook_event = result.scalar_one_or_none()

        if webhook_event:
            webhook_event.retry_count += 1
            await self.db.commit()

            logger.info(
                "webhook_retry_incremented",
                webhook_id=webhook_id,
                retry_count=webhook_event.retry_count,
            )
