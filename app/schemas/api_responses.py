"""API response schemas for frontend."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class AgentStateResponse(BaseModel):
    """Agent state information for API responses."""
    livechat_status: str
    ringcentral_presence: str
    reason: Optional[str] = None
    state_changed_at: datetime

    class Config:
        from_attributes = True


class AgentResponse(BaseModel):
    """Agent with current state for API responses."""
    id: int
    name: Optional[str] = None
    email: Optional[str] = None
    livechat_agent_id: str
    ringcentral_extension_id: str
    current_state: Optional[AgentStateResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    """List of agents response."""
    agents: List[AgentResponse]


class CustomerResponse(BaseModel):
    """Customer information for API responses."""
    id: int
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Conversation with related data for API responses."""
    id: int
    conversation_type: str  # chat, call
    platform: str  # livechat, ringcentral
    status: str  # active, ended, failed
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    agent: Optional[AgentResponse] = None
    customer: Optional[CustomerResponse] = None
    message_count: Optional[int] = 0

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """List of conversations response."""
    conversations: List[ConversationResponse]
    total: int
    limit: int
    offset: int


class MessageResponse(BaseModel):
    """Message information for API responses."""
    id: int
    sender_type: str  # agent, customer, system
    message_text: str
    message_type: str  # text, file, system
    sent_at: datetime
    synced_to_livechat: bool
    synced_to_ringcentral: bool

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    """Conversation with messages for API responses."""
    conversation: ConversationResponse
    messages: List[MessageResponse]


class SyncLogResponse(BaseModel):
    """Sync log information for API responses."""
    id: int
    operation_type: str
    source_platform: str
    target_platform: Optional[str] = None
    status: str  # success, failed, pending
    error_message: Optional[str] = None
    retry_count: int
    agent_id: Optional[int] = None
    conversation_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SyncLogListResponse(BaseModel):
    """List of sync logs response."""
    logs: List[SyncLogResponse]
    total: int
    limit: int
    offset: int


class StatsResponse(BaseModel):
    """Dashboard statistics response."""
    total_agents: int
    agents_available: int
    agents_busy: int
    agents_offline: int
    active_conversations: int
    total_conversations_today: int
    total_conversations_all_time: int
    sync_operations_today: int
    sync_success_rate: float
    last_sync_at: Optional[datetime] = None
