"""Celery background tasks."""

from typing import Dict, Any
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.agent_state import AgentStateManager
from app.core.conversation_sync import ConversationSync
from app.db.session import AsyncSessionLocal
from app.db.models import SyncLog
from app.utils.logger import get_logger

logger = get_logger(__name__)


def log_sync_operation(
    db: AsyncSession,
    operation_type: str,
    source_platform: str,
    status: str,
    agent_id: int = None,
    conversation_id: int = None,
    error_message: str = None,
) -> None:
    """
    Log a sync operation to the database.

    Args:
        db: Database session
        operation_type: Type of operation
        source_platform: Source platform
        status: Operation status
        agent_id: Optional agent ID
        conversation_id: Optional conversation ID
        error_message: Optional error message
    """
    async def _log():
        async with AsyncSessionLocal() as session:
            sync_log = SyncLog(
                operation_type=operation_type,
                source_platform=source_platform,
                target_platform="ringcentral" if source_platform == "livechat" else "livechat",
                status=status,
                agent_id=agent_id,
                conversation_id=conversation_id,
                error_message=error_message,
            )
            session.add(sync_log)
            await session.commit()

    asyncio.run(_log())


@celery_app.task(name="process_livechat_chat_started")
def process_livechat_chat_started(
    chat_id: str,
    agent_id: str,
    customer_email: str = None,
    customer_name: str = None,
    livechat_customer_id: str = None,
) -> Dict[str, Any]:
    """
    Process LiveChat chat_started webhook in background.

    Args:
        chat_id: LiveChat chat ID
        agent_id: LiveChat agent ID
        customer_email: Customer email
        customer_name: Customer name
        livechat_customer_id: LiveChat customer ID

    Returns:
        Result dictionary
    """
    logger.info("processing_livechat_chat_started", chat_id=chat_id, agent_id=agent_id)

    async def _process():
        async with AsyncSessionLocal() as db:
            try:
                # Initialize managers
                agent_manager = AgentStateManager(db)
                conversation_sync = ConversationSync(db)

                # Get agent by LiveChat ID
                agent = await agent_manager.get_agent_by_livechat_id(agent_id)
                if not agent:
                    logger.error("agent_not_found_for_livechat_id", livechat_agent_id=agent_id)
                    log_sync_operation(
                        db, "chat_started", "livechat", "failed",
                        error_message=f"Agent not found: {agent_id}"
                    )
                    return {"status": "error", "message": "Agent not found"}

                # Set agent busy in RingCentral
                await agent_manager.set_agent_busy_on_chat(agent_id)

                # Create conversation record
                conversation = await conversation_sync.create_chat_conversation(
                    chat_id=chat_id,
                    agent_id=agent.id,
                    customer_email=customer_email,
                    customer_name=customer_name,
                    livechat_customer_id=livechat_customer_id,
                )

                # Send notification to RingCentral (as note)
                customer_info = customer_name or customer_email or "Unknown customer"
                await agent_manager.ringcentral_client.create_note(
                    title=f"LiveChat Started - {chat_id}",
                    body=f"Agent {agent.name} is handling a LiveChat from {customer_info}",
                )

                # Log success
                log_sync_operation(
                    db, "chat_started", "livechat", "success",
                    agent_id=agent.id, conversation_id=conversation.id
                )

                # Close clients
                await agent_manager.close()
                await conversation_sync.close()

                logger.info("livechat_chat_started_processed", chat_id=chat_id)
                return {"status": "success", "conversation_id": conversation.id}

            except Exception as e:
                logger.error("failed_to_process_chat_started", error=str(e))
                log_sync_operation(
                    db, "chat_started", "livechat", "failed",
                    error_message=str(e)
                )
                return {"status": "error", "message": str(e)}

    return asyncio.run(_process())


@celery_app.task(name="process_livechat_chat_ended")
def process_livechat_chat_ended(chat_id: str, agent_id: str) -> Dict[str, Any]:
    """
    Process LiveChat chat_deactivated webhook in background.

    Args:
        chat_id: LiveChat chat ID
        agent_id: LiveChat agent ID

    Returns:
        Result dictionary
    """
    logger.info("processing_livechat_chat_ended", chat_id=chat_id)

    async def _process():
        async with AsyncSessionLocal() as db:
            try:
                # Initialize managers
                agent_manager = AgentStateManager(db)
                conversation_sync = ConversationSync(db)

                # Get agent
                agent = await agent_manager.get_agent_by_livechat_id(agent_id)
                if not agent:
                    logger.error("agent_not_found", livechat_agent_id=agent_id)
                    return {"status": "error", "message": "Agent not found"}

                # Find conversation
                from sqlalchemy import select
                from app.db.models import Conversation
                stmt = select(Conversation).where(
                    Conversation.livechat_chat_id == chat_id,
                    Conversation.status == "active"
                )
                result = await db.execute(stmt)
                conversation = result.scalar_one_or_none()

                if conversation:
                    # Finalize conversation
                    await conversation_sync.finalize_conversation(conversation.id)

                    # Sync final transcript to RingCentral
                    await conversation_sync.sync_final_transcript_to_ringcentral(conversation.id)

                    # Set agent available if no other active conversations
                    await agent_manager.set_agent_available(agent.id)

                    log_sync_operation(
                        db, "chat_ended", "livechat", "success",
                        agent_id=agent.id, conversation_id=conversation.id
                    )
                else:
                    logger.warning("conversation_not_found_for_chat", chat_id=chat_id)

                # Close clients
                await agent_manager.close()
                await conversation_sync.close()

                logger.info("livechat_chat_ended_processed", chat_id=chat_id)
                return {"status": "success"}

            except Exception as e:
                logger.error("failed_to_process_chat_ended", error=str(e))
                log_sync_operation(
                    db, "chat_ended", "livechat", "failed",
                    error_message=str(e)
                )
                return {"status": "error", "message": str(e)}

    return asyncio.run(_process())


@celery_app.task(name="process_ringcentral_call_started")
def process_ringcentral_call_started(
    session_id: str,
    extension_id: str,
    direction: str,
    from_number: str = None,
    to_number: str = None,
) -> Dict[str, Any]:
    """
    Process RingCentral call started webhook in background.

    Args:
        session_id: RingCentral session ID
        extension_id: RingCentral extension ID
        direction: Call direction
        from_number: Caller number
        to_number: Recipient number

    Returns:
        Result dictionary
    """
    logger.info("processing_ringcentral_call_started", session_id=session_id)

    async def _process():
        async with AsyncSessionLocal() as db:
            try:
                # Initialize managers
                agent_manager = AgentStateManager(db)
                conversation_sync = ConversationSync(db)

                # Get agent
                agent = await agent_manager.get_agent_by_ringcentral_id(extension_id)
                if not agent:
                    logger.error("agent_not_found", ringcentral_extension_id=extension_id)
                    return {"status": "error", "message": "Agent not found"}

                # Set agent busy in LiveChat
                await agent_manager.set_agent_busy_on_call(extension_id)

                # Create call record
                conversation, call_record = await conversation_sync.create_call_record(
                    session_id=session_id,
                    agent_id=agent.id,
                    direction=direction,
                    from_number=from_number,
                    to_number=to_number,
                    call_status="Connected",
                )

                log_sync_operation(
                    db, "call_started", "ringcentral", "success",
                    agent_id=agent.id, conversation_id=conversation.id
                )

                # Close clients
                await agent_manager.close()
                await conversation_sync.close()

                logger.info("ringcentral_call_started_processed", session_id=session_id)
                return {"status": "success", "conversation_id": conversation.id}

            except Exception as e:
                logger.error("failed_to_process_call_started", error=str(e))
                log_sync_operation(
                    db, "call_started", "ringcentral", "failed",
                    error_message=str(e)
                )
                return {"status": "error", "message": str(e)}

    return asyncio.run(_process())


@celery_app.task(name="process_ringcentral_call_ended")
def process_ringcentral_call_ended(session_id: str, extension_id: str) -> Dict[str, Any]:
    """
    Process RingCentral call ended webhook in background.

    Args:
        session_id: RingCentral session ID
        extension_id: RingCentral extension ID

    Returns:
        Result dictionary
    """
    logger.info("processing_ringcentral_call_ended", session_id=session_id)

    async def _process():
        async with AsyncSessionLocal() as db:
            try:
                # Initialize managers
                agent_manager = AgentStateManager(db)
                conversation_sync = ConversationSync(db)

                # Get agent
                agent = await agent_manager.get_agent_by_ringcentral_id(extension_id)
                if not agent:
                    logger.error("agent_not_found", ringcentral_extension_id=extension_id)
                    return {"status": "error", "message": "Agent not found"}

                # Find conversation
                from sqlalchemy import select
                from app.db.models import Conversation
                stmt = select(Conversation).where(
                    Conversation.ringcentral_session_id == session_id,
                    Conversation.status == "active"
                )
                result = await db.execute(stmt)
                conversation = result.scalar_one_or_none()

                if conversation:
                    # Finalize conversation
                    await conversation_sync.finalize_conversation(conversation.id)

                    # Sync call summary to LiveChat
                    await conversation_sync.sync_call_summary_to_livechat(conversation.id)

                    # Set agent available if no other active conversations
                    await agent_manager.set_agent_available(agent.id)

                    log_sync_operation(
                        db, "call_ended", "ringcentral", "success",
                        agent_id=agent.id, conversation_id=conversation.id
                    )
                else:
                    logger.warning("conversation_not_found_for_session", session_id=session_id)

                # Close clients
                await agent_manager.close()
                await conversation_sync.close()

                logger.info("ringcentral_call_ended_processed", session_id=session_id)
                return {"status": "success"}

            except Exception as e:
                logger.error("failed_to_process_call_ended", error=str(e))
                log_sync_operation(
                    db, "call_ended", "ringcentral", "failed",
                    error_message=str(e)
                )
                return {"status": "error", "message": str(e)}

    return asyncio.run(_process())
