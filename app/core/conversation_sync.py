"""Conversation synchronization between platforms."""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Message, CallRecord, Agent, Customer
from app.integrations.livechat.client import LiveChatClient
from app.integrations.ringcentral.client import RingCentralClient
from app.core.contact_matching import ContactMatcher
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConversationSync:
    """Synchronize conversations and messages between platforms."""

    def __init__(self, db: AsyncSession):
        """
        Initialize conversation sync.

        Args:
            db: Database session
        """
        self.db = db
        self.livechat_client = LiveChatClient()
        self.ringcentral_client = RingCentralClient()
        self.contact_matcher = ContactMatcher(db)

    async def create_chat_conversation(
        self,
        chat_id: str,
        agent_id: int,
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None,
        livechat_customer_id: Optional[str] = None,
    ) -> Conversation:
        """
        Create a conversation record from a LiveChat chat.

        Args:
            chat_id: LiveChat chat ID
            agent_id: Agent database ID
            customer_email: Customer email
            customer_name: Customer name
            livechat_customer_id: LiveChat customer ID

        Returns:
            Created Conversation record
        """
        logger.info("creating_chat_conversation", chat_id=chat_id, agent_id=agent_id)

        # Find or create customer
        customer = await self.contact_matcher.find_or_create_customer(
            livechat_customer_id=livechat_customer_id,
            email=customer_email,
            name=customer_name,
        )

        # Create conversation
        conversation = Conversation(
            conversation_type="chat",
            platform="livechat",
            livechat_chat_id=chat_id,
            agent_id=agent_id,
            customer_id=customer.id,
            started_at=datetime.utcnow(),
            status="active",
        )

        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)

        logger.info(
            "chat_conversation_created",
            conversation_id=conversation.id,
            chat_id=chat_id,
        )

        return conversation

    async def create_call_record(
        self,
        session_id: str,
        agent_id: int,
        direction: str,
        from_number: Optional[str] = None,
        to_number: Optional[str] = None,
        call_status: str = "Ringing",
    ) -> tuple[Conversation, CallRecord]:
        """
        Create a call record from a RingCentral call.

        Args:
            session_id: RingCentral session ID
            agent_id: Agent database ID
            direction: Call direction (inbound/outbound)
            from_number: Caller number
            to_number: Recipient number
            call_status: Call status

        Returns:
            Tuple of (Conversation, CallRecord)
        """
        logger.info(
            "creating_call_record",
            session_id=session_id,
            agent_id=agent_id,
            direction=direction,
        )

        # Find or create customer by phone
        phone = from_number if direction == "inbound" else to_number
        customer = await self.contact_matcher.find_or_create_customer(phone=phone)

        # Create conversation
        conversation = Conversation(
            conversation_type="call",
            platform="ringcentral",
            ringcentral_session_id=session_id,
            agent_id=agent_id,
            customer_id=customer.id,
            started_at=datetime.utcnow(),
            status="active",
        )

        self.db.add(conversation)
        await self.db.flush()

        # Create call record
        call_record = CallRecord(
            conversation_id=conversation.id,
            session_id=session_id,
            direction=direction,
            from_number=from_number,
            to_number=to_number,
            call_status=call_status,
        )

        self.db.add(call_record)
        await self.db.commit()
        await self.db.refresh(conversation)
        await self.db.refresh(call_record)

        logger.info(
            "call_record_created",
            conversation_id=conversation.id,
            session_id=session_id,
        )

        return conversation, call_record

    async def sync_message_to_ringcentral(
        self,
        conversation_id: int,
        message_text: str,
        sender_type: str,
        chat_id: Optional[str] = None,
    ) -> None:
        """
        Sync a LiveChat message to RingCentral (real-time).

        Args:
            conversation_id: Conversation database ID
            message_text: Message text
            sender_type: Sender type (agent/customer)
            chat_id: LiveChat chat ID
        """
        logger.info(
            "syncing_message_to_ringcentral",
            conversation_id=conversation_id,
            sender_type=sender_type,
        )

        # Get conversation with agent
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            logger.warning("conversation_not_found", conversation_id=conversation_id)
            return

        # Get agent
        stmt = select(Agent).where(Agent.id == conversation.agent_id)
        result = await self.db.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            logger.warning("agent_not_found", agent_id=conversation.agent_id)
            return

        # Note: This would send to a RingCentral team chat
        # For now, we'll create a note instead
        try:
            prefix = "Customer:" if sender_type == "customer" else "Agent:"
            await self.ringcentral_client.create_note(
                title=f"LiveChat Message - {chat_id}",
                body=f"{prefix} {message_text}",
            )

            logger.info("message_synced_to_ringcentral", conversation_id=conversation_id)

        except Exception as e:
            logger.error(
                "failed_to_sync_message_to_ringcentral",
                conversation_id=conversation_id,
                error=str(e),
            )

    async def sync_final_transcript_to_ringcentral(
        self,
        conversation_id: int,
    ) -> None:
        """
        Sync final chat transcript to RingCentral after chat ends.

        Args:
            conversation_id: Conversation database ID
        """
        logger.info("syncing_final_transcript", conversation_id=conversation_id)

        # Get conversation with messages
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            logger.warning("conversation_not_found", conversation_id=conversation_id)
            return

        # Get all messages
        stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.sent_at)
        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        # Build transcript
        transcript_lines = [
            f"LiveChat Transcript - Chat ID: {conversation.livechat_chat_id}",
            f"Started: {conversation.started_at}",
            f"Ended: {conversation.ended_at}",
            "",
        ]

        for msg in messages:
            sender = msg.sender_type.capitalize()
            transcript_lines.append(f"[{msg.sent_at}] {sender}: {msg.message_text}")

        transcript = "\n".join(transcript_lines)

        # Create note in RingCentral
        try:
            await self.ringcentral_client.create_note(
                title=f"LiveChat Transcript - {conversation.livechat_chat_id}",
                body=transcript,
            )

            logger.info("transcript_synced_to_ringcentral", conversation_id=conversation_id)

        except Exception as e:
            logger.error(
                "failed_to_sync_transcript",
                conversation_id=conversation_id,
                error=str(e),
            )

    async def sync_call_summary_to_livechat(
        self,
        conversation_id: int,
    ) -> None:
        """
        Sync call summary to LiveChat customer notes after call ends.

        Args:
            conversation_id: Conversation database ID
        """
        logger.info("syncing_call_summary", conversation_id=conversation_id)

        # Get conversation with call record
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            logger.warning("conversation_not_found", conversation_id=conversation_id)
            return

        # Get call record
        stmt = select(CallRecord).where(CallRecord.conversation_id == conversation_id)
        result = await self.db.execute(stmt)
        call_record = result.scalar_one_or_none()

        if not call_record:
            logger.warning("call_record_not_found", conversation_id=conversation_id)
            return

        # Get customer
        stmt = select(Customer).where(Customer.id == conversation.customer_id)
        result = await self.db.execute(stmt)
        customer = result.scalar_one_or_none()

        if not customer or not customer.livechat_customer_id:
            logger.warning("customer_not_found_or_no_livechat_id", conversation_id=conversation_id)
            return

        # Build call summary
        summary = (
            f"RingCentral Call Summary\n"
            f"Direction: {call_record.direction}\n"
            f"From: {call_record.from_number}\n"
            f"To: {call_record.to_number}\n"
            f"Duration: {conversation.duration_seconds}s\n"
            f"Started: {conversation.started_at}\n"
            f"Ended: {conversation.ended_at}\n"
        )

        # Create note in LiveChat
        try:
            await self.livechat_client.create_customer_note(
                customer_id=customer.livechat_customer_id,
                title=f"RingCentral Call - {call_record.session_id}",
                text=summary,
            )

            logger.info("call_summary_synced_to_livechat", conversation_id=conversation_id)

        except Exception as e:
            logger.error(
                "failed_to_sync_call_summary",
                conversation_id=conversation_id,
                error=str(e),
            )

    async def finalize_conversation(
        self,
        conversation_id: int,
    ) -> None:
        """
        Finalize a conversation (set end time, calculate duration).

        Args:
            conversation_id: Conversation database ID
        """
        logger.info("finalizing_conversation", conversation_id=conversation_id)

        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            logger.warning("conversation_not_found", conversation_id=conversation_id)
            return

        # Set end time and status
        conversation.ended_at = datetime.utcnow()
        conversation.status = "ended"

        # Calculate duration
        if conversation.started_at:
            duration = (conversation.ended_at - conversation.started_at).total_seconds()
            conversation.duration_seconds = int(duration)

        await self.db.commit()

        logger.info(
            "conversation_finalized",
            conversation_id=conversation_id,
            duration=conversation.duration_seconds,
        )

    async def close(self) -> None:
        """Close API clients."""
        await self.livechat_client.close()
        await self.ringcentral_client.close()
