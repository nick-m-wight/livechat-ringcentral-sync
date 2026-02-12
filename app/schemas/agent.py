"""Shared agent schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class AgentBase(BaseModel):
    """Base agent schema."""
    livechat_agent_id: str
    ringcentral_extension_id: str
    email: Optional[EmailStr] = None
    name: Optional[str] = None


class AgentCreate(AgentBase):
    """Schema for creating an agent."""
    pass


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""
    email: Optional[EmailStr] = None
    name: Optional[str] = None


class Agent(AgentBase):
    """Agent schema with database fields."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentStateBase(BaseModel):
    """Base agent state schema."""
    livechat_status: str
    ringcentral_presence: str
    reason: Optional[str] = None


class AgentState(AgentStateBase):
    """Agent state schema with database fields."""
    id: int
    agent_id: int
    state_changed_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
