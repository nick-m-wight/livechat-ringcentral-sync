"""Data API endpoints for frontend."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from app.dependencies import get_database_session
from app.db.models import Agent, AgentState, Conversation, Customer, Message, SyncLog
from app.schemas.api_responses import (
    AgentListResponse,
    AgentResponse,
    AgentStateResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationDetailResponse,
    CustomerResponse,
    MessageResponse,
    SyncLogListResponse,
    SyncLogResponse,
    StatsResponse,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["data"])


@router.get("/agents", response_model=AgentListResponse)
async def get_agents(db: AsyncSession = Depends(get_database_session)):
    """
    Get all agents with their current state.

    Returns:
        AgentListResponse: List of agents with current states
    """
    try:
        # Get all agents
        result = await db.execute(select(Agent))
        agents = result.scalars().all()

        agent_responses = []
        for agent in agents:
            # Get the latest state for each agent
            state_result = await db.execute(
                select(AgentState)
                .where(AgentState.agent_id == agent.id)
                .order_by(desc(AgentState.state_changed_at))
                .limit(1)
            )
            latest_state = state_result.scalar_one_or_none()

            # Build response
            agent_dict = {
                "id": agent.id,
                "name": agent.name,
                "email": agent.email,
                "livechat_agent_id": agent.livechat_agent_id,
                "ringcentral_extension_id": agent.ringcentral_extension_id,
                "created_at": agent.created_at,
                "updated_at": agent.updated_at,
                "current_state": None,
            }

            if latest_state:
                agent_dict["current_state"] = AgentStateResponse(
                    livechat_status=latest_state.livechat_status,
                    ringcentral_presence=latest_state.ringcentral_presence,
                    reason=latest_state.reason,
                    state_changed_at=latest_state.state_changed_at,
                )

            agent_responses.append(AgentResponse(**agent_dict))

        return AgentListResponse(agents=agent_responses)

    except Exception as e:
        logger.error("get_agents_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agents",
        )


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_database_session),
):
    """
    Get a single agent by ID with current state.

    Args:
        agent_id: Agent ID

    Returns:
        AgentResponse: Agent with current state
    """
    try:
        # Get agent
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )

        # Get latest state
        state_result = await db.execute(
            select(AgentState)
            .where(AgentState.agent_id == agent.id)
            .order_by(desc(AgentState.state_changed_at))
            .limit(1)
        )
        latest_state = state_result.scalar_one_or_none()

        # Build response
        agent_dict = {
            "id": agent.id,
            "name": agent.name,
            "email": agent.email,
            "livechat_agent_id": agent.livechat_agent_id,
            "ringcentral_extension_id": agent.ringcentral_extension_id,
            "created_at": agent.created_at,
            "updated_at": agent.updated_at,
            "current_state": None,
        }

        if latest_state:
            agent_dict["current_state"] = AgentStateResponse(
                livechat_status=latest_state.livechat_status,
                ringcentral_presence=latest_state.ringcentral_presence,
                reason=latest_state.reason,
                state_changed_at=latest_state.state_changed_at,
            )

        return AgentResponse(**agent_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_agent_failed", agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent",
        )


@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    status_filter: Optional[str] = Query(None, alias="status"),
    conversation_type: Optional[str] = Query(None, alias="type"),
    platform: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_database_session),
):
    """
    Get conversations with optional filtering and pagination.

    Args:
        status_filter: Filter by status (active, ended, failed)
        conversation_type: Filter by type (chat, call)
        platform: Filter by platform (livechat, ringcentral)
        limit: Maximum number of results (1-100)
        offset: Number of results to skip

    Returns:
        ConversationListResponse: List of conversations with pagination info
    """
    try:
        # Build query with filters
        query = select(Conversation)
        filters = []

        if status_filter:
            filters.append(Conversation.status == status_filter)
        if conversation_type:
            filters.append(Conversation.conversation_type == conversation_type)
        if platform:
            filters.append(Conversation.platform == platform)

        if filters:
            query = query.where(and_(*filters))

        # Get total count
        count_query = select(func.count()).select_from(Conversation)
        if filters:
            count_query = count_query.where(and_(*filters))
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Get conversations with pagination
        query = query.order_by(desc(Conversation.started_at)).limit(limit).offset(offset)
        result = await db.execute(query)
        conversations = result.scalars().all()

        # Build responses with related data
        conversation_responses = []
        for conv in conversations:
            # Get agent
            agent_result = await db.execute(select(Agent).where(Agent.id == conv.agent_id))
            agent = agent_result.scalar_one_or_none()

            # Get customer if exists
            customer = None
            if conv.customer_id:
                customer_result = await db.execute(
                    select(Customer).where(Customer.id == conv.customer_id)
                )
                customer = customer_result.scalar_one_or_none()

            # Get message count
            message_count_result = await db.execute(
                select(func.count()).where(Message.conversation_id == conv.id)
            )
            message_count = message_count_result.scalar()

            # Build response
            conv_dict = {
                "id": conv.id,
                "conversation_type": conv.conversation_type,
                "platform": conv.platform,
                "status": conv.status,
                "started_at": conv.started_at,
                "ended_at": conv.ended_at,
                "duration_seconds": conv.duration_seconds,
                "agent": None,
                "customer": None,
                "message_count": message_count or 0,
            }

            if agent:
                conv_dict["agent"] = AgentResponse(
                    id=agent.id,
                    name=agent.name,
                    email=agent.email,
                    livechat_agent_id=agent.livechat_agent_id,
                    ringcentral_extension_id=agent.ringcentral_extension_id,
                    created_at=agent.created_at,
                    updated_at=agent.updated_at,
                    current_state=None,
                )

            if customer:
                conv_dict["customer"] = CustomerResponse(
                    id=customer.id,
                    name=customer.name,
                    email=customer.email,
                    phone=customer.phone,
                )

            conversation_responses.append(ConversationResponse(**conv_dict))

        return ConversationListResponse(
            conversations=conversation_responses,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error("get_conversations_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations",
        )


@router.get("/conversations/{conversation_id}/messages", response_model=ConversationDetailResponse)
async def get_conversation_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_database_session),
):
    """
    Get a conversation with all its messages.

    Args:
        conversation_id: Conversation ID

    Returns:
        ConversationDetailResponse: Conversation with messages
    """
    try:
        # Get conversation
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()

        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found",
            )

        # Get agent
        agent_result = await db.execute(select(Agent).where(Agent.id == conv.agent_id))
        agent = agent_result.scalar_one_or_none()

        # Get customer if exists
        customer = None
        if conv.customer_id:
            customer_result = await db.execute(
                select(Customer).where(Customer.id == conv.customer_id)
            )
            customer = customer_result.scalar_one_or_none()

        # Get messages
        messages_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sent_at)
        )
        messages = messages_result.scalars().all()

        # Build conversation response
        conv_dict = {
            "id": conv.id,
            "conversation_type": conv.conversation_type,
            "platform": conv.platform,
            "status": conv.status,
            "started_at": conv.started_at,
            "ended_at": conv.ended_at,
            "duration_seconds": conv.duration_seconds,
            "agent": None,
            "customer": None,
            "message_count": len(messages),
        }

        if agent:
            conv_dict["agent"] = AgentResponse(
                id=agent.id,
                name=agent.name,
                email=agent.email,
                livechat_agent_id=agent.livechat_agent_id,
                ringcentral_extension_id=agent.ringcentral_extension_id,
                created_at=agent.created_at,
                updated_at=agent.updated_at,
                current_state=None,
            )

        if customer:
            conv_dict["customer"] = CustomerResponse(
                id=customer.id,
                name=customer.name,
                email=customer.email,
                phone=customer.phone,
            )

        # Build message responses
        message_responses = [
            MessageResponse(
                id=msg.id,
                sender_type=msg.sender_type,
                message_text=msg.message_text,
                message_type=msg.message_type,
                sent_at=msg.sent_at,
                synced_to_livechat=msg.synced_to_livechat,
                synced_to_ringcentral=msg.synced_to_ringcentral,
            )
            for msg in messages
        ]

        return ConversationDetailResponse(
            conversation=ConversationResponse(**conv_dict),
            messages=message_responses,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_conversation_messages_failed", conversation_id=conversation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation messages",
        )


@router.get("/sync-logs", response_model=SyncLogListResponse)
async def get_sync_logs(
    status_filter: Optional[str] = Query(None, alias="status"),
    operation_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_database_session),
):
    """
    Get sync operation logs with optional filtering and pagination.

    Args:
        status_filter: Filter by status (success, failed, pending)
        operation_type: Filter by operation type
        limit: Maximum number of results (1-500)
        offset: Number of results to skip

    Returns:
        SyncLogListResponse: List of sync logs with pagination info
    """
    try:
        # Build query with filters
        query = select(SyncLog)
        filters = []

        if status_filter:
            filters.append(SyncLog.status == status_filter)
        if operation_type:
            filters.append(SyncLog.operation_type == operation_type)

        if filters:
            query = query.where(and_(*filters))

        # Get total count
        count_query = select(func.count()).select_from(SyncLog)
        if filters:
            count_query = count_query.where(and_(*filters))
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Get logs with pagination
        query = query.order_by(desc(SyncLog.created_at)).limit(limit).offset(offset)
        result = await db.execute(query)
        logs = result.scalars().all()

        # Build responses
        log_responses = [
            SyncLogResponse(
                id=log.id,
                operation_type=log.operation_type,
                source_platform=log.source_platform,
                target_platform=log.target_platform,
                status=log.status,
                error_message=log.error_message,
                retry_count=log.retry_count,
                agent_id=log.agent_id,
                conversation_id=log.conversation_id,
                created_at=log.created_at,
            )
            for log in logs
        ]

        return SyncLogListResponse(
            logs=log_responses,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error("get_sync_logs_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sync logs",
        )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_database_session)):
    """
    Get dashboard statistics.

    Returns:
        StatsResponse: Dashboard statistics
    """
    try:
        # Total agents
        total_agents_result = await db.execute(select(func.count()).select_from(Agent))
        total_agents = total_agents_result.scalar()

        # Count agents by status
        # Get all agents with their latest state
        agents_result = await db.execute(select(Agent))
        agents = agents_result.scalars().all()

        agents_available = 0
        agents_busy = 0
        agents_offline = 0

        for agent in agents:
            state_result = await db.execute(
                select(AgentState)
                .where(AgentState.agent_id == agent.id)
                .order_by(desc(AgentState.state_changed_at))
                .limit(1)
            )
            latest_state = state_result.scalar_one_or_none()

            if latest_state:
                if (
                    latest_state.livechat_status == "accepting_chats"
                    and latest_state.ringcentral_presence == "Available"
                ):
                    agents_available += 1
                elif latest_state.ringcentral_presence == "Offline":
                    agents_offline += 1
                else:
                    agents_busy += 1
            else:
                agents_offline += 1

        # Active conversations
        active_convs_result = await db.execute(
            select(func.count()).where(Conversation.status == "active")
        )
        active_conversations = active_convs_result.scalar()

        # Total conversations today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_convs_result = await db.execute(
            select(func.count()).where(Conversation.started_at >= today_start)
        )
        total_conversations_today = today_convs_result.scalar()

        # Total conversations all time
        all_convs_result = await db.execute(select(func.count()).select_from(Conversation))
        total_conversations_all_time = all_convs_result.scalar()

        # Sync operations today
        sync_today_result = await db.execute(
            select(func.count()).where(SyncLog.created_at >= today_start)
        )
        sync_operations_today = sync_today_result.scalar()

        # Sync success rate
        total_syncs_result = await db.execute(select(func.count()).select_from(SyncLog))
        total_syncs = total_syncs_result.scalar()

        successful_syncs_result = await db.execute(
            select(func.count()).where(SyncLog.status == "success")
        )
        successful_syncs = successful_syncs_result.scalar()

        sync_success_rate = (
            (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0.0
        )

        # Last sync
        last_sync_result = await db.execute(
            select(SyncLog).order_by(desc(SyncLog.created_at)).limit(1)
        )
        last_sync = last_sync_result.scalar_one_or_none()
        last_sync_at = last_sync.created_at if last_sync else None

        return StatsResponse(
            total_agents=total_agents,
            agents_available=agents_available,
            agents_busy=agents_busy,
            agents_offline=agents_offline,
            active_conversations=active_conversations,
            total_conversations_today=total_conversations_today,
            total_conversations_all_time=total_conversations_all_time,
            sync_operations_today=sync_operations_today,
            sync_success_rate=round(sync_success_rate, 2),
            last_sync_at=last_sync_at,
        )

    except Exception as e:
        logger.error("get_stats_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics",
        )
