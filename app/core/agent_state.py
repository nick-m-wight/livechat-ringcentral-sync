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

        Updates:
        - RingCentral presence to "Busy"

        Args:
            livechat_agent_id: LiveChat agent ID
        """
        logger.info("setting_agent_busy_on_chat", livechat_agent_id=livechat_agent_id)

        # Get agent record
        agent = await self.get_agent_by_livechat_id(livechat_agent_id)
        if not agent:
            logger.warning("agent_not_found", livechat_agent_id=livechat_agent_id)
            return

        try:
            # Set RingCentral presence to Busy
            await self.ringcentral_client.set_user_presence(
                extension_id=agent.ringcentral_extension_id,
                presence_status="Busy",
            )

            # Record state change
            await self.record_agent_state(
                agent_id=agent.id,
                livechat_status="accepting_chats",  # Agent is handling chat
                ringcentral_presence="Busy",
                reason="on_livechat",
            )

            logger.info(
                "agent_set_busy_on_chat",
                agent_id=agent.id,
                livechat_agent_id=livechat_agent_id,
            )

        except Exception as e:
            logger.error(
                "failed_to_set_agent_busy_on_chat",
                livechat_agent_id=livechat_agent_id,
                error=str(e),
            )
            raise

    async def set_agent_busy_on_call(self, ringcentral_extension_id: str) -> None:
        """
        Set agent as busy when they start a RingCentral call.

        Updates:
        - LiveChat status to "not_accepting_chats"

        Args:
            ringcentral_extension_id: RingCentral extension ID
        """
        logger.info("setting_agent_busy_on_call", ringcentral_extension_id=ringcentral_extension_id)

        # Get agent record
        agent = await self.get_agent_by_ringcentral_id(ringcentral_extension_id)
        if not agent:
            logger.warning("agent_not_found", ringcentral_extension_id=ringcentral_extension_id)
            return

        try:
            # Set LiveChat status to not accepting chats
            await self.livechat_client.set_agent_status(
                agent_id=agent.livechat_agent_id,
                status="not_accepting_chats",
            )

            # Record state change
            await self.record_agent_state(
                agent_id=agent.id,
                livechat_status="not_accepting_chats",
                ringcentral_presence="Busy",  # Agent is on call
                reason="on_call",
            )

            logger.info(
                "agent_set_busy_on_call",
                agent_id=agent.id,
                ringcentral_extension_id=ringcentral_extension_id,
            )

        except Exception as e:
            logger.error(
                "failed_to_set_agent_busy_on_call",
                ringcentral_extension_id=ringcentral_extension_id,
                error=str(e),
            )
            raise

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

        try:
            # Set both platforms to available
            await self.livechat_client.set_agent_status(
                agent_id=agent.livechat_agent_id,
                status="accepting_chats",
            )

            await self.ringcentral_client.set_user_presence(
                extension_id=agent.ringcentral_extension_id,
                presence_status="Available",
            )

            # Record state change
            await self.record_agent_state(
                agent_id=agent.id,
                livechat_status="accepting_chats",
                ringcentral_presence="Available",
                reason="available",
            )

            logger.info("agent_set_available", agent_id=agent_id)

        except Exception as e:
            logger.error(
                "failed_to_set_agent_available",
                agent_id=agent_id,
                error=str(e),
            )
            raise

    async def close(self) -> None:
        """Close API clients."""
        await self.livechat_client.close()
        await self.ringcentral_client.close()
