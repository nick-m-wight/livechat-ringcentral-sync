"""SQLAlchemy ORM models for the application."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Boolean,
    Text,
    Float,
    ForeignKey,
    Index,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Agent(Base):
    """Agent information and ID mappings between LiveChat and RingCentral."""

    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    livechat_agent_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    ringcentral_extension_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    agent_states = relationship("AgentState", back_populates="agent", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="agent")

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name}, email={self.email})>"


class AgentState(Base):
    """Agent availability state tracking."""

    __tablename__ = "agent_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)

    # State information
    livechat_status: Mapped[str] = mapped_column(String(50), nullable=False)  # accepting_chats, not_accepting_chats
    ringcentral_presence: Mapped[str] = mapped_column(String(50), nullable=False)  # Available, Busy, Offline

    # Reason for state change
    reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # on_livechat, on_call, manual, available

    # Timestamps
    state_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    agent = relationship("Agent", back_populates="agent_states")

    __table_args__ = (
        Index("idx_agent_state_changed", "agent_id", "state_changed_at"),
    )

    def __repr__(self) -> str:
        return f"<AgentState(agent_id={self.agent_id}, livechat={self.livechat_status}, rc={self.ringcentral_presence})>"


class Customer(Base):
    """Unified customer/contact records."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    livechat_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    ringcentral_contact_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Contact information
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Additional info
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    conversations = relationship("Conversation", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, email={self.email}, phone={self.phone})>"


class Conversation(Base):
    """Unified storage for both LiveChat chats and RingCentral calls."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Type and source
    conversation_type: Mapped[str] = mapped_column(String(20), nullable=False)  # chat, call
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # livechat, ringcentral

    # External IDs
    livechat_chat_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    ringcentral_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Participants
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id"), nullable=False)
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("customers.id"), nullable=True)

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # active, ended, failed

    # Metadata
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    agent = relationship("Agent", back_populates="conversations")
    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    call_records = relationship("CallRecord", back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_conversation_agent_status", "agent_id", "status"),
        Index("idx_conversation_started", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, type={self.conversation_type}, status={self.status})>"


class Message(Base):
    """Individual messages in conversations."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False
    )

    # Message details
    external_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)  # agent, customer, system
    sender_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Content
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), default="text")  # text, file, system

    # Sync status
    synced_to_livechat: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_to_ringcentral: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("idx_message_conversation_sent", "conversation_id", "sent_at"),
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, sender_type={self.sender_type})>"


class CallRecord(Base):
    """RingCentral telephony session details."""

    __tablename__ = "call_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False
    )

    # Call details
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # inbound, outbound
    from_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Status
    call_status: Mapped[str] = mapped_column(String(50), nullable=False)  # Ringing, Connected, Disconnected

    # Recording
    recording_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    recording_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metadata
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="call_records")

    def __repr__(self) -> str:
        return f"<CallRecord(id={self.id}, session_id={self.session_id}, status={self.call_status})>"


class WebhookEvent(Base):
    """Webhook deduplication and replay."""

    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Webhook identification
    webhook_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # livechat, ringcentral
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Processing status
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Payload
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Timestamps
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # TTL for cleanup (30 days)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )

    __table_args__ = (
        Index("idx_webhook_platform_type", "platform", "event_type"),
    )

    def __repr__(self) -> str:
        return f"<WebhookEvent(id={self.id}, webhook_id={self.webhook_id}, processed={self.processed})>"


class SyncLog(Base):
    """Operation tracking and debugging."""

    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Operation details
    operation_type: Mapped[str] = mapped_column(String(100), nullable=False)  # agent_state_sync, message_sync, etc.
    source_platform: Mapped[str] = mapped_column(String(20), nullable=False)
    target_platform: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success, failed, pending
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Related entities
    agent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    conversation_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    # Metadata
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("idx_sync_log_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<SyncLog(id={self.id}, operation={self.operation_type}, status={self.status})>"
