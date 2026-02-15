"""Pydantic models for LiveChat data."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class LiveChatUser(BaseModel):
    """LiveChat user information."""
    id: str
    name: Optional[str] = None
    email: Optional[str] = None
    type: str = "customer"  # customer, agent


class LiveChatMessage(BaseModel):
    """LiveChat message."""
    id: str
    author_id: str
    text: str
    timestamp: datetime
    type: str = "message"


class LiveChatCustomer(BaseModel):
    """LiveChat customer information."""
    id: str
    name: Optional[str] = None
    email: Optional[str] = None
    session_fields: Optional[List[Dict[str, Any]]] = None


class LiveChatThread(BaseModel):
    """LiveChat thread/conversation."""
    id: str
    active: bool
    user_ids: List[str]
    created_at: datetime


class LiveChatWebhook(BaseModel):
    """Base LiveChat webhook payload."""
    webhook_id: str
    secret_key: Optional[str] = None
    action: str
    organization_id: Optional[str] = None


class ChatStartedWebhook(LiveChatWebhook):
    """LiveChat chat_started webhook."""
    payload: Dict[str, Any]
    chat_id: Optional[str] = None
    thread_id: Optional[str] = None
    agent: Optional[LiveChatUser] = None
    customer: Optional[LiveChatCustomer] = None


class ChatMessageWebhook(LiveChatWebhook):
    """LiveChat incoming_message webhook."""
    payload: Dict[str, Any]
    chat_id: Optional[str] = None
    message: Optional[LiveChatMessage] = None


class ChatDeactivatedWebhook(LiveChatWebhook):
    """LiveChat chat_deactivated webhook."""
    payload: Dict[str, Any]
    chat_id: Optional[str] = None
    thread_id: Optional[str] = None


class AgentStatus(BaseModel):
    """LiveChat agent status."""
    status: str  # accepting_chats, not_accepting_chats, offline
    routing_status: Optional[str] = None


class SendMessageRequest(BaseModel):
    """Request to send a message to LiveChat."""
    chat_id: str
    text: str
    author_id: Optional[str] = None


class CustomerNote(BaseModel):
    """Customer note in LiveChat."""
    title: str
    text: str
