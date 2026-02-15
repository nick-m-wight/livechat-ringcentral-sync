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


async def log_sync_operation(
    operation_type: str,
    source_platform: str,
    status: str,
    agent_id: int = None,
    conversation_id: int = None,
    error_message: str = None,
) -> None:
    """
    Log a sync operation to the database (async version).

    Args:
        operation_type: Type of operation
        source_platform: Source platform
        status: Operation status
        agent_id: Optional agent ID
        conversation_id: Optional conversation ID
        error_message: Optional error message
    """
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

    SIMPLIFIED FOR DEMO: Just creates the conversation and sets agent to chatting.
    Skips complex sync operations that cause event loop issues.

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
        # Create a fresh session for this task
        async with AsyncSessionLocal() as db:
            try:
                from sqlalchemy import select
                from app.db.models import Agent, AgentState, Conversation, Customer
                from datetime import datetime

                # Get agent by LiveChat ID
                stmt = select(Agent).where(Agent.livechat_agent_id == agent_id)
                result = await db.execute(stmt)
                agent = result.scalar_one_or_none()

                if not agent:
                    logger.error("agent_not_found_for_livechat_id", livechat_agent_id=agent_id)
                    return {"status": "error", "message": "Agent not found"}

                # Get or create customer
                customer = None
                if livechat_customer_id:
                    stmt = select(Customer).where(Customer.livechat_customer_id == livechat_customer_id)
                    result = await db.execute(stmt)
                    customer = result.scalar_one_or_none()

                if not customer and (customer_email or customer_name):
                    customer = Customer(
                        livechat_customer_id=livechat_customer_id,
                        email=customer_email,
                        name=customer_name,
                    )
                    db.add(customer)
                    await db.flush()

                # Create conversation
                now = datetime.now()
                conversation = Conversation(
                    conversation_type="chat",
                    platform="livechat",
                    livechat_chat_id=chat_id,
                    agent_id=agent.id,
                    customer_id=customer.id if customer else None,
                    started_at=now,
                    status="active",
                )
                db.add(conversation)

                # Set agent to chatting (busy on both platforms)
                agent_state = AgentState(
                    agent_id=agent.id,
                    livechat_status="not_accepting_chats",
                    ringcentral_presence="Busy",
                    reason="chatting",
                    state_changed_at=now,
                    created_at=now,
                )
                db.add(agent_state)

                await db.commit()
                await db.refresh(conversation)

                logger.info("livechat_chat_started_processed", chat_id=chat_id, conversation_id=conversation.id)
                return {"status": "success", "conversation_id": conversation.id}

            except Exception as e:
                await db.rollback()
                logger.error("failed_to_process_chat_started", error=str(e))
                import traceback
                traceback.print_exc()
                return {"status": "error", "message": str(e)}

    # Create new event loop for this Celery worker thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_process())
    finally:
        loop.close()


@celery_app.task(name="process_livechat_chat_ended")
def process_livechat_chat_ended(chat_id: str, agent_id: str) -> Dict[str, Any]:
    """
    Process LiveChat chat_deactivated webhook in background.

    SIMPLIFIED FOR DEMO: Just ends the conversation and sets agent available.
    Skips complex sync operations that cause event loop issues.

    Args:
        chat_id: LiveChat chat ID
        agent_id: LiveChat agent ID

    Returns:
        Result dictionary
    """
    logger.info("processing_livechat_chat_ended", chat_id=chat_id, agent_id=agent_id)

    async def _process():
        # Create a fresh session for this task
        async with AsyncSessionLocal() as db:
            try:
                from sqlalchemy import select, update
                from app.db.models import Agent, AgentState, Conversation
                from datetime import datetime

                # Get agent
                stmt = select(Agent).where(Agent.livechat_agent_id == agent_id)
                result = await db.execute(stmt)
                agent = result.scalar_one_or_none()

                if not agent:
                    logger.error("agent_not_found", livechat_agent_id=agent_id)
                    return {"status": "error", "message": "Agent not found"}

                # End the conversation
                now = datetime.now()
                stmt = (
                    update(Conversation)
                    .where(
                        Conversation.livechat_chat_id == chat_id,
                        Conversation.status == "active"
                    )
                    .values(
                        status="ended",
                        ended_at=now,
                    )
                )
                result = await db.execute(stmt)

                if result.rowcount > 0:
                    logger.info("conversation_ended", chat_id=chat_id)

                    # Check if agent has other active conversations
                    stmt = select(Conversation).where(
                        Conversation.agent_id == agent.id,
                        Conversation.status == "active"
                    )
                    result = await db.execute(stmt)
                    other_active = result.first()

                    if not other_active:
                        # No other active conversations - set agent available
                        agent_state = AgentState(
                            agent_id=agent.id,
                            livechat_status="accepting_chats",
                            ringcentral_presence="Available",
                            reason="available",
                            state_changed_at=now,
                            created_at=now,
                        )
                        db.add(agent_state)
                        logger.info("agent_set_available", agent_id=agent.id)
                    else:
                        logger.info("agent_has_other_active_conversations", agent_id=agent.id)

                    await db.commit()
                    logger.info("livechat_chat_ended_processed", chat_id=chat_id)
                    return {"status": "success"}
                else:
                    logger.warning("conversation_not_found_for_chat", chat_id=chat_id)
                    return {"status": "error", "message": "Conversation not found"}

            except Exception as e:
                await db.rollback()
                logger.error("failed_to_process_chat_ended", error=str(e))
                import traceback
                traceback.print_exc()
                return {"status": "error", "message": str(e)}

    # Create new event loop for this Celery worker thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_process())
    finally:
        loop.close()


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

    SIMPLIFIED FOR DEMO: Just creates the conversation and sets agent to on_call.
    Skips complex sync operations that cause event loop issues.

    Args:
        session_id: RingCentral session ID
        extension_id: RingCentral extension ID
        direction: Call direction
        from_number: Caller number
        to_number: Recipient number

    Returns:
        Result dictionary
    """
    logger.info("processing_ringcentral_call_started", session_id=session_id, extension_id=extension_id)

    async def _process():
        # Create a fresh session for this task
        async with AsyncSessionLocal() as db:
            try:
                from sqlalchemy import select
                from app.db.models import Agent, AgentState, Conversation, CallRecord
                from datetime import datetime

                # Get agent by RingCentral extension ID
                stmt = select(Agent).where(Agent.ringcentral_extension_id == extension_id)
                result = await db.execute(stmt)
                agent = result.scalar_one_or_none()

                if not agent:
                    logger.error("agent_not_found", ringcentral_extension_id=extension_id)
                    return {"status": "error", "message": "Agent not found"}

                # Create conversation
                now = datetime.now()
                conversation = Conversation(
                    conversation_type="call",
                    platform="ringcentral",
                    ringcentral_session_id=session_id,
                    agent_id=agent.id,
                    started_at=now,
                    status="active",
                )
                db.add(conversation)
                await db.flush()

                # Create call record
                call_record = CallRecord(
                    conversation_id=conversation.id,
                    session_id=session_id,
                    direction=direction,
                    from_number=from_number,
                    to_number=to_number,
                    call_status="Connected",
                )
                db.add(call_record)

                # Set agent to on_call (busy on both platforms)
                agent_state = AgentState(
                    agent_id=agent.id,
                    livechat_status="not_accepting_chats",
                    ringcentral_presence="Busy",
                    reason="on_call",
                    state_changed_at=now,
                    created_at=now,
                )
                db.add(agent_state)

                await db.commit()
                await db.refresh(conversation)

                logger.info("ringcentral_call_started_processed", session_id=session_id, conversation_id=conversation.id)
                return {"status": "success", "conversation_id": conversation.id}

            except Exception as e:
                await db.rollback()
                logger.error("failed_to_process_call_started", error=str(e))
                import traceback
                traceback.print_exc()
                return {"status": "error", "message": str(e)}

    # Create new event loop for this Celery worker thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_process())
    finally:
        loop.close()


@celery_app.task(name="process_ringcentral_call_ended")
def process_ringcentral_call_ended(session_id: str, extension_id: str) -> Dict[str, Any]:
    """
    Process RingCentral call ended webhook in background.

    SIMPLIFIED FOR DEMO: Just ends the conversation and sets agent available.
    Skips complex sync operations that cause event loop issues.

    Args:
        session_id: RingCentral session ID
        extension_id: RingCentral extension ID

    Returns:
        Result dictionary
    """
    logger.info("processing_ringcentral_call_ended", session_id=session_id, extension_id=extension_id)

    async def _process():
        # Create a fresh session for this task
        async with AsyncSessionLocal() as db:
            try:
                from sqlalchemy import select, update
                from app.db.models import Agent, AgentState, Conversation
                from datetime import datetime

                # Get agent
                stmt = select(Agent).where(Agent.ringcentral_extension_id == extension_id)
                result = await db.execute(stmt)
                agent = result.scalar_one_or_none()

                if not agent:
                    logger.error("agent_not_found", ringcentral_extension_id=extension_id)
                    return {"status": "error", "message": "Agent not found"}

                # End the conversation
                now = datetime.now()
                stmt = (
                    update(Conversation)
                    .where(
                        Conversation.ringcentral_session_id == session_id,
                        Conversation.status == "active"
                    )
                    .values(
                        status="ended",
                        ended_at=now,
                    )
                )
                result = await db.execute(stmt)

                if result.rowcount > 0:
                    logger.info("conversation_ended", session_id=session_id)

                    # Check if agent has other active conversations
                    stmt = select(Conversation).where(
                        Conversation.agent_id == agent.id,
                        Conversation.status == "active"
                    )
                    result = await db.execute(stmt)
                    other_active = result.first()

                    if not other_active:
                        # No other active conversations - set agent available
                        agent_state = AgentState(
                            agent_id=agent.id,
                            livechat_status="accepting_chats",
                            ringcentral_presence="Available",
                            reason="available",
                            state_changed_at=now,
                            created_at=now,
                        )
                        db.add(agent_state)
                        logger.info("agent_set_available", agent_id=agent.id)
                    else:
                        logger.info("agent_has_other_active_conversations", agent_id=agent.id)

                    await db.commit()
                    logger.info("ringcentral_call_ended_processed", session_id=session_id)
                    return {"status": "success"}
                else:
                    logger.warning("conversation_not_found_for_session", session_id=session_id)
                    return {"status": "error", "message": "Conversation not found"}

            except Exception as e:
                await db.rollback()
                logger.error("failed_to_process_call_ended", error=str(e))
                import traceback
                traceback.print_exc()
                return {"status": "error", "message": str(e)}

    # Create new event loop for this Celery worker thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_process())
    finally:
        loop.close()
