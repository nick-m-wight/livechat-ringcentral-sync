"""Agent state management across platforms."""

from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Agent, AgentState, Conversation
from app.integrations.livechat.client import LiveChatClient
from app.integrations.ringcentral.client import RingCentralClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AgentStateManager:
    """Manage agent availability state across LiveChat and RingCentral."""

    def __init__(self, db: AsyncSession):
        """
        Initialize agent state manager.

        Args:
            db: Database session
        """
        self.db = db
        self.livechat_client = LiveChatClient()
        self.ringcentral_client = RingCentralClient()

    async def get_agent_by_livechat_id(self, livechat_agent_id: str) -> Optional[Agent]:
        """
        Get agent by LiveChat ID.

        Args:
            livechat_agent_id: LiveChat agent ID

        Returns:
            Agent record or None
        """
        stmt = select(Agent).where(Agent.livechat_agent_id == livechat_agent_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_agent_by_ringcentral_id(self, ringcentral_extension_id: str) -> Optional[Agent]:
        """
        Get agent by RingCentral extension ID.

        Args:
            ringcentral_extension_id: RingCentral extension ID

        Returns:
            Agent record or None
        """
        stmt = select(Agent).where(Agent.ringcentral_extension_id == ringcentral_extension_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def check_active_conversations(self, agent_id: int) -> bool:
        """
        Check if agent has any active conversations.

        Args:
            agent_id: Agent database ID

        Returns:
            True if agent has active conversations
        """
        stmt = select(Conversation).where(
            Conversation.agent_id == agent_id,
            Conversation.status == "active"
        )
        result = await self.db.execute(stmt)
        active_conversations = result.scalars().all()

        has_active = len(active_conversations) > 0

        logger.debug(
            "checked_active_conversations",
            agent_id=agent_id,
            count=len(active_conversations),
            has_active=has_active,
        )

        return has_active

    async def record_agent_state(
        self,
        agent_id: int,
        livechat_status: str,
        ringcentral_presence: str,
        reason: str,
    ) -> AgentState:
        """
        Record agent state change in database.

        Args:
            agent_id: Agent database ID
            livechat_status: LiveChat status
            ringcentral_presence: RingCentral presence
            reason: Reason for state change

        Returns:
            Created AgentState record
        """
        agent_state = AgentState(
            agent_id=agent_id,
            livechat_status=livechat_status,
            ringcentral_presence=ringcentral_presence,
            reason=reason,
            state_changed_at=datetime.utcnow(),
        )

        self.db.add(agent_state)
        await self.db.commit()
        await self.db.refresh(agent_state)

        logger.info(
            "agent_state_recorded",
            agent_id=agent_id,
            livechat_status=livechat_status,
            ringcentral_presence=ringcentral_presence,
            reason=reason,
        )

        return agent_state

    async def set_agent_busy_on_chat(self, livechat_agent_id: str) -> None:
        """
        Set agent as busy when they start a LiveChat conversation.

        Updates both platforms:
        - LiveChat status to "not_accepting_chats" (busy with chat)
        - RingCentral presence to "Busy" (can't take calls)

        Args:
            livechat_agent_id: LiveChat agent ID
        """
        logger.info("setting_agent_busy_on_chat", livechat_agent_id=livechat_agent_id)

        # Get agent record
        agent = await self.get_agent_by_livechat_id(livechat_agent_id)
        if not agent:
            logger.warning("agent_not_found", livechat_agent_id=livechat_agent_id)
            return

        # Try to set LiveChat status to not accepting (may fail if no credentials)
        try:
            await self.livechat_client.set_agent_status(
                agent_id=agent.livechat_agent_id,
                status="not_accepting_chats",
            )
        except Exception as api_error:
            logger.warning(
                "livechat_api_call_failed_continuing",
                error=str(api_error),
                agent_id=agent.livechat_agent_id,
            )

        # Try to set RingCentral presence to Busy (may fail if no credentials)
        try:
            await self.ringcentral_client.set_user_presence(
                extension_id=agent.ringcentral_extension_id,
                presence_status="Busy",
            )
        except Exception as api_error:
            logger.warning(
                "ringcentral_api_call_failed_continuing",
                error=str(api_error),
                extension_id=agent.ringcentral_extension_id,
            )

        # Always record state change locally - BOTH platforms busy
        await self.record_agent_state(
            agent_id=agent.id,
            livechat_status="not_accepting_chats",  # Can't accept more chats
            ringcentral_presence="Busy",  # Can't accept calls either
            reason="chatting",  # Descriptive reason
        )

        logger.info(
            "agent_set_busy_on_chat",
            agent_id=agent.id,
            livechat_agent_id=livechat_agent_id,
        )

    async def set_agent_busy_on_call(self, ringcentral_extension_id: str) -> None:
        """
        Set agent as busy when they start a RingCentral call.

        Updates both platforms:
        - LiveChat status to "not_accepting_chats" (can't take chats)
        - RingCentral presence to "Busy" (on a call)

        Args:
            ringcentral_extension_id: RingCentral extension ID
        """
        logger.info("setting_agent_busy_on_call", ringcentral_extension_id=ringcentral_extension_id)

        # Get agent record
        agent = await self.get_agent_by_ringcentral_id(ringcentral_extension_id)
        if not agent:
            logger.warning("agent_not_found", ringcentral_extension_id=ringcentral_extension_id)
            return

        # Try to set LiveChat status to not accepting (may fail if no credentials)
        try:
            await self.livechat_client.set_agent_status(
                agent_id=agent.livechat_agent_id,
                status="not_accepting_chats",
            )
        except Exception as api_error:
            logger.warning(
                "livechat_api_call_failed_continuing",
                error=str(api_error),
                agent_id=agent.livechat_agent_id,
            )

        # Try to set RingCentral presence to Busy (may fail if no credentials)
        try:
            await self.ringcentral_client.set_user_presence(
                extension_id=agent.ringcentral_extension_id,
                presence_status="Busy",
            )
        except Exception as api_error:
            logger.warning(
                "ringcentral_api_call_failed_continuing",
                error=str(api_error),
                extension_id=agent.ringcentral_extension_id,
            )

        # Always record state change locally - BOTH platforms busy
        await self.record_agent_state(
            agent_id=agent.id,
            livechat_status="not_accepting_chats",  # Can't accept chats
            ringcentral_presence="Busy",  # Can't accept calls either
            reason="on_call",  # Descriptive reason
        )

        logger.info(
            "agent_set_busy_on_call",
            agent_id=agent.id,
            ringcentral_extension_id=ringcentral_extension_id,
        )

    async def set_agent_available(self, agent_id: int) -> None:
        """
        Set agent as available after conversation/call ends.

        Only sets available if agent has NO other active conversations.

        Updates:
        - LiveChat status to "accepting_chats"
        - RingCentral presence to "Available"

        Args:
            agent_id: Agent database ID
        """
        logger.info("setting_agent_available", agent_id=agent_id)

        # Check if agent has other active conversations
        has_active = await self.check_active_conversations(agent_id)

        if has_active:
            logger.info(
                "agent_has_active_conversations",
                agent_id=agent_id,
                message="Not setting available - agent has other active conversations",
            )
            return

        # Get agent record
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await self.db.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            logger.warning("agent_not_found_by_id", agent_id=agent_id)
            return

        # Try to set both platforms to available (may fail if no credentials)
        try:
            await self.livechat_client.set_agent_status(
                agent_id=agent.livechat_agent_id,
                status="accepting_chats",
            )
        except Exception as api_error:
            logger.warning(
                "livechat_api_call_failed_continuing",
                error=str(api_error),
                agent_id=agent.livechat_agent_id,
            )

        try:
            await self.ringcentral_client.set_user_presence(
                extension_id=agent.ringcentral_extension_id,
                presence_status="Available",
            )
        except Exception as api_error:
            logger.warning(
                "ringcentral_api_call_failed_continuing",
                error=str(api_error),
                extension_id=agent.ringcentral_extension_id,
            )

        # Always record state change locally (even if API calls failed)
        await self.record_agent_state(
            agent_id=agent.id,
            livechat_status="accepting_chats",
            ringcentral_presence="Available",
            reason="available",
        )

        logger.info("agent_set_available", agent_id=agent_id)

    async def close(self) -> None:
        """Close API clients."""
        await self.livechat_client.close()
        await self.ringcentral_client.close()
