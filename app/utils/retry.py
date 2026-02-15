"""Retry utilities using tenacity."""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import httpx

from app.config import settings


# Retry decorator for HTTP requests
# Reduced retries for faster demo mode (API calls will fail without real credentials)
retry_http = retry(
    stop=stop_after_attempt(1),  # Only 1 attempt for demo
    wait=wait_exponential(multiplier=1, min=0.5, max=2),  # Shorter waits
    retry=retry_if_exception_type((httpx.TimeoutException,)),  # Only retry timeouts, not auth errors
    reraise=True,
)
