"""LiveChat webhook endpoints."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.dependencies import get_database_session
from app.integrations.livechat.webhooks import verify_livechat_signature, extract_livechat_webhook_id
from app.core.idempotency import IdempotencyManager
from app.core.tasks import (
    process_livechat_chat_started,
    process_livechat_chat_ended,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["livechat-webhooks"])


@router.post("/incoming_chat", status_code=status.HTTP_200_OK)
async def livechat_incoming_chat(
    request: Request,
    db: AsyncSession = Depends(get_database_session),
    x_livechat_signature: Optional[str] = Header(None),
) -> dict:
    """
    Handle LiveChat incoming_chat webhook (chat_started event).

    Triggered when a new chat is started with an agent.

    Args:
        request: FastAPI request
        db: Database session
        x_livechat_signature: Webhook signature header

    Returns:
        Success response
    """
    # Get raw body for signature verification
    body_bytes = await request.body()
    payload = await request.json()

    logger.info("livechat_incoming_chat_webhook_received", webhook_id=payload.get("webhook_id"))

    # Verify signature
    if x_livechat_signature:
        is_valid = verify_livechat_signature(body_bytes, x_livechat_signature)
        if not is_valid:
            logger.warning("livechat_signature_verification_failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

    # Extract webhook ID
    webhook_id = extract_livechat_webhook_id(payload)
    if not webhook_id:
        logger.warning("livechat_webhook_id_missing")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook ID missing",
        )

    # Check idempotency
    idempotency_manager = IdempotencyManager(db)
    is_duplicate, webhook_event = await idempotency_manager.check_and_record_webhook(
        webhook_id=webhook_id,
        platform="livechat",
        event_type="incoming_chat",
        payload=payload,
    )

    if is_duplicate and webhook_event.processed:
        logger.info("livechat_webhook_already_processed", webhook_id=webhook_id)
        return {"status": "ok", "message": "Webhook already processed"}

    # Extract data from payload
    chat_payload = payload.get("payload", {})
    chat_id = chat_payload.get("chat", {}).get("id")

    # Get agent info
    users = chat_payload.get("chat", {}).get("users", [])
    agent_id = None
    for user in users:
        if user.get("type") == "agent":
            agent_id = user.get("id")
            break

    # Get customer info
    customer = chat_payload.get("chat", {}).get("users", [{}])[0]  # First user is typically customer
    customer_email = None
    customer_name = None
    livechat_customer_id = None

    for user in users:
        if user.get("type") == "customer":
            customer_email = user.get("email")
            customer_name = user.get("name")
            livechat_customer_id = user.get("id")
            break

    # Return 200 OK immediately
    logger.info(
        "livechat_incoming_chat_accepted",
        webhook_id=webhook_id,
        chat_id=chat_id,
        agent_id=agent_id,
    )

    # Process in background
    process_livechat_chat_started.delay(
        chat_id=chat_id,
        agent_id=agent_id,
        customer_email=customer_email,
        customer_name=customer_name,
        livechat_customer_id=livechat_customer_id,
    )

    return {"status": "ok", "message": "Webhook received"}


@router.post("/chat_deactivated", status_code=status.HTTP_200_OK)
async def livechat_chat_deactivated(
    request: Request,
    db: AsyncSession = Depends(get_database_session),
    x_livechat_signature: Optional[str] = Header(None),
) -> dict:
    """
    Handle LiveChat chat_deactivated webhook.

    Triggered when a chat ends.

    Args:
        request: FastAPI request
        db: Database session
        x_livechat_signature: Webhook signature header

    Returns:
        Success response
    """
    # Get raw body for signature verification
    body_bytes = await request.body()
    payload = await request.json()

    logger.info("livechat_chat_deactivated_webhook_received", webhook_id=payload.get("webhook_id"))

    # Verify signature
    if x_livechat_signature:
        is_valid = verify_livechat_signature(body_bytes, x_livechat_signature)
        if not is_valid:
            logger.warning("livechat_signature_verification_failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

    # Extract webhook ID
    webhook_id = extract_livechat_webhook_id(payload)
    if not webhook_id:
        logger.warning("livechat_webhook_id_missing")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook ID missing",
        )

    # Check idempotency
    idempotency_manager = IdempotencyManager(db)
    is_duplicate, webhook_event = await idempotency_manager.check_and_record_webhook(
        webhook_id=webhook_id,
        platform="livechat",
        event_type="chat_deactivated",
        payload=payload,
    )

    if is_duplicate and webhook_event.processed:
        logger.info("livechat_webhook_already_processed", webhook_id=webhook_id)
        return {"status": "ok", "message": "Webhook already processed"}

    # Extract data
    chat_payload = payload.get("payload", {})
    chat_data = chat_payload.get("chat", {})
    chat_id = chat_data.get("id")  # Chat ID is nested under "chat"

    # Get agent ID from chat users
    users = chat_data.get("users", [])
    agent_id = None
    for user in users:
        if user.get("type") == "agent":
            agent_id = user.get("id")
            break

    # Return 200 OK immediately
    logger.info("livechat_chat_deactivated_accepted", webhook_id=webhook_id, chat_id=chat_id)

    # Process in background
    process_livechat_chat_ended.delay(
        chat_id=chat_id,
        agent_id=agent_id,
    )

    return {"status": "ok", "message": "Webhook received"}


@router.post("/chat_message", status_code=status.HTTP_200_OK)
async def livechat_chat_message(
    request: Request,
    db: AsyncSession = Depends(get_database_session),
    x_livechat_signature: Optional[str] = Header(None),
) -> dict:
    """
    Handle LiveChat incoming_message webhook.

    Triggered when a new message is sent in a chat.

    Args:
        request: FastAPI request
        db: Database session
        x_livechat_signature: Webhook signature header

    Returns:
        Success response
    """
    # Get raw body for signature verification
    body_bytes = await request.body()
    payload = await request.json()

    logger.info("livechat_chat_message_webhook_received", webhook_id=payload.get("webhook_id"))

    # Verify signature
    if x_livechat_signature:
        is_valid = verify_livechat_signature(body_bytes, x_livechat_signature)
        if not is_valid:
            logger.warning("livechat_signature_verification_failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

    # For now, just acknowledge the message
    # Real-time message sync can be implemented later if needed
    logger.info("livechat_message_received", chat_id=payload.get("payload", {}).get("chat_id"))

    return {"status": "ok", "message": "Message received"}
