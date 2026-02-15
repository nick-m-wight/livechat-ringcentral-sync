"""Base HTTP client with retry logic."""

from typing import Any, Dict, Optional
import httpx

from app.config import settings
from app.utils.logger import get_logger
from app.utils.retry import retry_http

logger = get_logger(__name__)


class BaseHTTPClient:
    """Base HTTP client with automatic retry logic and logging."""

    def __init__(
        self,
        base_url: str,
        auth_token: Optional[str] = None,
        timeout: float = 3.0,  # Reduced for demo mode
    ):
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL for the API
            auth_token: Optional authentication token
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout

        # Create httpx client
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "LiveChat-RingCentral-Sync/0.1.0",
        }

        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    @retry_http
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a GET request.

        Args:
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            headers: Additional headers

        Returns:
            Response JSON data
        """
        logger.debug("http_get", endpoint=endpoint, params=params)

        response = await self.client.get(
            endpoint,
            params=params,
            headers=headers,
        )
        response.raise_for_status()

        return response.json()

    @retry_http
    async def post(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a POST request.

        Args:
            endpoint: API endpoint (relative to base_url)
            json: JSON body data
            data: Form data
            headers: Additional headers

        Returns:
            Response JSON data
        """
        logger.debug("http_post", endpoint=endpoint, has_json=json is not None)

        response = await self.client.post(
            endpoint,
            json=json,
            data=data,
            headers=headers,
        )
        response.raise_for_status()

        # Some endpoints may return empty responses
        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    @retry_http
    async def put(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a PUT request.

        Args:
            endpoint: API endpoint (relative to base_url)
            json: JSON body data
            headers: Additional headers

        Returns:
            Response JSON data
        """
        logger.debug("http_put", endpoint=endpoint)

        response = await self.client.put(
            endpoint,
            json=json,
            headers=headers,
        )
        response.raise_for_status()

        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    @retry_http
    async def delete(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a DELETE request.

        Args:
            endpoint: API endpoint (relative to base_url)
            headers: Additional headers

        Returns:
            Response JSON data
        """
        logger.debug("http_delete", endpoint=endpoint)

        response = await self.client.delete(
            endpoint,
            headers=headers,
        )
        response.raise_for_status()

        if response.status_code == 204 or not response.content:
            return {}

        return response.json()
