"""RingCentral webhook signature verification."""

import hmac
import hashlib
from typing import Optional, Dict, Any

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def verify_ringcentral_signature(payload: bytes, signature: str) -> bool:
    """
    Verify RingCentral webhook signature using HMAC SHA-256.

    Args:
        payload: Raw request body bytes
        signature: Signature from X-RingCentral-Signature header

    Returns:
        True if signature is valid, False otherwise
    """
    if not settings.RINGCENTRAL_WEBHOOK_SECRET:
        logger.warning("ringcentral_webhook_secret_not_configured")
        return True  # Skip verification if secret not configured (development only)

    try:
        # Compute expected signature
        expected_signature = hmac.new(
            settings.RINGCENTRAL_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        # Timing-safe comparison
        is_valid = hmac.compare_digest(expected_signature, signature)

        if not is_valid:
            logger.warning(
                "ringcentral_signature_mismatch",
                expected=expected_signature[:10] + "...",
                received=signature[:10] + "...",
            )

        return is_valid

    except Exception as e:
        logger.error("ringcentral_signature_verification_error", error=str(e))
        return False


def extract_ringcentral_webhook_id(payload: Dict[str, Any]) -> Optional[str]:
    """
    Extract unique webhook ID from RingCentral webhook payload.

    Args:
        payload: Webhook JSON payload

    Returns:
        Unique webhook identifier or None
    """
    # RingCentral uses uuid field
    return payload.get("uuid")


def handle_validation_token(payload: Dict[str, Any]) -> Optional[str]:
    """
    Handle RingCentral webhook validation token.

    When setting up a webhook, RingCentral sends a validation token
    that must be echoed back in the response.

    Args:
        payload: Webhook JSON payload

    Returns:
        Validation token if present, None otherwise
    """
    return payload.get("validationToken")
