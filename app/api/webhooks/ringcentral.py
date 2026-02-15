"""RingCentral webhook endpoints."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.dependencies import get_database_session
from app.integrations.ringcentral.webhooks import (
    verify_ringcentral_signature,
    extract_ringcentral_webhook_id,
    handle_validation_token,
)
from app.core.idempotency import IdempotencyManager
from app.core.tasks import (
    process_ringcentral_call_started,
    process_ringcentral_call_ended,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["ringcentral-webhooks"])


@router.post("/telephony-session", status_code=status.HTTP_200_OK)
async def ringcentral_telephony_session(
    request: Request,
    db: AsyncSession = Depends(get_database_session),
    x_ringcentral_signature: Optional[str] = Header(None),
) -> dict:
    """
    Handle RingCentral telephony session webhooks.

    Receives events for call state changes (Ringing, Connected, Disconnected).

    Args:
        request: FastAPI request
        db: Database session
        x_ringcentral_signature: Webhook signature header

    Returns:
        Success response or validation token
    """
    # Get raw body for signature verification
    body_bytes = await request.body()
    payload = await request.json()

    logger.info("ringcentral_telephony_webhook_received", event_type=payload.get("event"))

    # Handle validation token (webhook setup)
    validation_token = handle_validation_token(payload)
    if validation_token:
        logger.info("ringcentral_validation_token_received")
        return {"validationToken": validation_token}

    # Verify signature (skip for validation requests)
    if x_ringcentral_signature:
        is_valid = verify_ringcentral_signature(body_bytes, x_ringcentral_signature)
        if not is_valid:
            logger.warning("ringcentral_signature_verification_failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

    # Extract webhook ID
    webhook_id = extract_ringcentral_webhook_id(payload)
    if not webhook_id:
        logger.warning("ringcentral_webhook_id_missing")
        # Don't fail - some events might not have UUID
        webhook_id = f"rc_{payload.get('timestamp', 'unknown')}"

    # Check idempotency
    idempotency_manager = IdempotencyManager(db)
    is_duplicate, webhook_event = await idempotency_manager.check_and_record_webhook(
        webhook_id=webhook_id,
        platform="ringcentral",
        event_type=payload.get("event", "unknown"),
        payload=payload,
    )

    if is_duplicate and webhook_event.processed:
        logger.info("ringcentral_webhook_already_processed", webhook_id=webhook_id)
        return {"status": "ok", "message": "Webhook already processed"}

    # Extract event data
    event = payload.get("event")
    body = payload.get("body", {})

    # Get session ID
    session_id = body.get("sessionId") or body.get("id")
    if not session_id:
        logger.warning("ringcentral_session_id_missing")
        return {"status": "ok", "message": "No session ID"}

    # Get parties (participants)
    parties = body.get("parties", [])
    if not parties:
        logger.info("ringcentral_no_parties_in_session", session_id=session_id)
        return {"status": "ok", "message": "No parties"}

    # Find agent party (internal extension)
    agent_party = None
    for party in parties:
        # Internal extensions typically have extensionId
        if party.get("extensionId"):
            agent_party = party
            break

    if not agent_party:
        logger.info("ringcentral_no_agent_party_found", session_id=session_id)
        return {"status": "ok", "message": "No agent party"}

    extension_id = agent_party.get("extensionId")

    # Get direction - handle both string and object formats
    direction_data = agent_party.get("direction", "Inbound")
    if isinstance(direction_data, dict):
        direction = direction_data.get("value", "Inbound")
    else:
        direction = direction_data

    # Get phone numbers
    from_info = agent_party.get("from", {})
    to_info = agent_party.get("to", {})
    from_number = from_info.get("phoneNumber") or from_info.get("extensionNumber")
    to_number = to_info.get("phoneNumber") or to_info.get("extensionNumber")

    # Get party status - handle both string and object formats
    status_data = agent_party.get("status")
    if isinstance(status_data, dict):
        party_status = status_data.get("code")
    else:
        party_status = status_data

    logger.info(
        "ringcentral_telephony_event_parsed",
        event_type=event,
        session_id=session_id,
        extension_id=extension_id,
        party_status=party_status,
    )

    # Return 200 OK immediately
    logger.info("ringcentral_telephony_webhook_accepted", webhook_id=webhook_id)

    # Process based on event type and status
    # "Setup" or "Proceeding" = call starting (ringing/connecting)
    # "Answered" or "Connected" = call answered
    # "Disconnected" = call ended
    if party_status in ["Setup", "Proceeding", "Answered", "Connected"]:
        # Call started/answered
        process_ringcentral_call_started.delay(
            session_id=session_id,
            extension_id=extension_id,
            direction=direction.lower(),
            from_number=from_number,
            to_number=to_number,
        )
    elif party_status == "Disconnected":
        # Call ended
        process_ringcentral_call_ended.delay(
            session_id=session_id,
            extension_id=extension_id,
        )

    return {"status": "ok", "message": "Webhook received"}


@router.post("/call-log", status_code=status.HTTP_200_OK)
async def ringcentral_call_log(
    request: Request,
    db: AsyncSession = Depends(get_database_session),
) -> dict:
    """
    Handle RingCentral call log webhooks.

    Optional endpoint for receiving call log entries after calls complete.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response
    """
    payload = await request.json()

    logger.info("ringcentral_call_log_webhook_received")

    # Handle validation token
    validation_token = handle_validation_token(payload)
    if validation_token:
        return {"validationToken": validation_token}

    # For now, just acknowledge
    # Can be extended to capture call recordings, transcripts, etc.
    return {"status": "ok", "message": "Call log received"}
