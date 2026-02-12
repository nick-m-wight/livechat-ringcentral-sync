"""Shared conversation schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ConversationBase(BaseModel):
    """Base conversation schema."""
    conversation_type: str  # chat, call
    platform: str  # livechat, ringcentral


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation."""
    agent_id: int
    customer_id: Optional[int] = None
    livechat_chat_id: Optional[str] = None
    ringcentral_session_id: Optional[str] = None


class Conversation(ConversationBase):
    """Conversation schema with database fields."""
    id: int
    agent_id: int
    customer_id: Optional[int] = None
    livechat_chat_id: Optional[str] = None
    ringcentral_session_id: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    """Base message schema."""
    sender_type: str  # agent, customer, system
    message_text: str
    message_type: str = "text"


class MessageCreate(MessageBase):
    """Schema for creating a message."""
    conversation_id: int
    external_message_id: Optional[str] = None
    sender_id: Optional[str] = None
    sent_at: datetime


class Message(MessageBase):
    """Message schema with database fields."""
    id: int
    conversation_id: int
    external_message_id: Optional[str] = None
    sender_id: Optional[str] = None
    synced_to_livechat: bool
    synced_to_ringcentral: bool
    sent_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerBase(BaseModel):
    """Base customer schema."""
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None


class CustomerCreate(CustomerBase):
    """Schema for creating a customer."""
    livechat_customer_id: Optional[str] = None
    ringcentral_contact_id: Optional[str] = None


class Customer(CustomerBase):
    """Customer schema with database fields."""
    id: int
    livechat_customer_id: Optional[str] = None
    ringcentral_contact_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
