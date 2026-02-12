"""Pydantic models for RingCentral data."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RingCentralExtension(BaseModel):
    """RingCentral extension information."""
    id: str
    extension_number: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None


class RingCentralPresence(BaseModel):
    """RingCentral presence information."""
    presence_status: str  # Available, Busy, Offline
    user_status: Optional[str] = None
    dnd_status: Optional[str] = None


class RingCentralParty(BaseModel):
    """Party in a telephony session."""
    id: str
    extension_id: Optional[str] = None
    direction: Optional[str] = None  # Inbound, Outbound
    from_number: Optional[str] = Field(None, alias="from")
    to_number: Optional[str] = Field(None, alias="to")
    status: Optional[str] = None


class RingCentralTelephonySession(BaseModel):
    """RingCentral telephony session."""
    id: str
    session_id: str
    parties: List[RingCentralParty] = []
    origin: Optional[Dict[str, Any]] = None
    creation_time: Optional[datetime] = None


class RingCentralWebhookBody(BaseModel):
    """RingCentral webhook body."""
    uuid: str
    event: str
    timestamp: datetime
    subscription_id: str
    owner_id: Optional[str] = None
    body: Optional[Dict[str, Any]] = None


class RingCentralTelephonyWebhook(BaseModel):
    """RingCentral telephony session webhook."""
    uuid: str
    event: str
    timestamp: datetime
    subscription_id: str
    body: Optional[RingCentralTelephonySession] = None


class SetPresenceRequest(BaseModel):
    """Request to set user presence."""
    presence_status: str  # Available, Busy, Offline
    user_status: Optional[str] = None


class SendTeamMessageRequest(BaseModel):
    """Request to send a team message."""
    chat_id: str
    text: str


class CreateNoteRequest(BaseModel):
    """Request to create a note."""
    title: str
    body: str
    contact_id: Optional[str] = None


class ValidationTokenResponse(BaseModel):
    """Response for webhook validation token."""
    validation_token: str
