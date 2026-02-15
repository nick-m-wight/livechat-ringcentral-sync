"""Shared sync operation schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SyncLogBase(BaseModel):
    """Base sync log schema."""
    operation_type: str
    source_platform: str
    target_platform: Optional[str] = None
    status: str  # success, failed, pending


class SyncLogCreate(SyncLogBase):
    """Schema for creating a sync log."""
    agent_id: Optional[int] = None
    conversation_id: Optional[int] = None
    error_message: Optional[str] = None


class SyncLog(SyncLogBase):
    """Sync log schema with database fields."""
    id: int
    agent_id: Optional[int] = None
    conversation_id: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookEventBase(BaseModel):
    """Base webhook event schema."""
    webhook_id: str
    platform: str
    event_type: str


class WebhookEvent(WebhookEventBase):
    """Webhook event schema with database fields."""
    id: int
    processed: bool
    retry_count: int
    received_at: datetime
    processed_at: Optional[datetime] = None
    expires_at: datetime

    class Config:
        from_attributes = True
