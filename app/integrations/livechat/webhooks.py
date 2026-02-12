"""LiveChat webhook signature verification."""

import hmac
import hashlib
from typing import Optional

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def verify_livechat_signature(payload: bytes, signature: str) -> bool:
    """
    Verify LiveChat webhook signature using HMAC SHA-256.

    Args:
        payload: Raw request body bytes
        signature: Signature from X-LiveChat-Signature header

    Returns:
        True if signature is valid, False otherwise
    """
    if not settings.LIVECHAT_WEBHOOK_SECRET:
        logger.warning("livechat_webhook_secret_not_configured")
        return True  # Skip verification if secret not configured (development only)

    try:
        # Compute expected signature
        expected_signature = hmac.new(
            settings.LIVECHAT_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        # Timing-safe comparison
        is_valid = hmac.compare_digest(expected_signature, signature)

        if not is_valid:
            logger.warning(
                "livechat_signature_mismatch",
                expected=expected_signature[:10] + "...",
                received=signature[:10] + "...",
            )

        return is_valid

    except Exception as e:
        logger.error("livechat_signature_verification_error", error=str(e))
        return False


def extract_livechat_webhook_id(payload: dict) -> Optional[str]:
    """
    Extract unique webhook ID from LiveChat webhook payload.

    Args:
        payload: Webhook JSON payload

    Returns:
        Unique webhook identifier or None
    """
    # LiveChat uses webhook_id field
    return payload.get("webhook_id")
