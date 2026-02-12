"""LiveChat API client."""

from typing import Optional, Dict, Any

from app.config import settings
from app.integrations.base_client import BaseHTTPClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LiveChatClient(BaseHTTPClient):
    """LiveChat API client for managing agents, chats, and customers."""

    def __init__(self) -> None:
        """Initialize LiveChat client."""
        super().__init__(
            base_url=settings.LIVECHAT_API_URL,
            auth_token=settings.LIVECHAT_ACCESS_TOKEN,
        )

    async def set_agent_status(
        self,
        agent_id: str,
        status: str,
        routing_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Set agent status in LiveChat.

        Args:
            agent_id: LiveChat agent ID
            status: Status (accepting_chats, not_accepting_chats, offline)
            routing_status: Optional routing status

        Returns:
            API response
        """
        logger.info(
            "livechat_set_agent_status",
            agent_id=agent_id,
            status=status,
            routing_status=routing_status,
        )

        payload: Dict[str, Any] = {
            "status": status,
        }

        if routing_status:
            payload["routing_status"] = routing_status

        try:
            response = await self.put(
                f"/agent/action/set_routing_status",
                json=payload,
            )
            logger.info("livechat_agent_status_updated", agent_id=agent_id, status=status)
            return response
        except Exception as e:
            logger.error(
                "livechat_set_agent_status_failed",
                agent_id=agent_id,
                error=str(e),
            )
            raise

    async def send_message_to_chat(
        self,
        chat_id: str,
        text: str,
        author_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a LiveChat conversation.

        Args:
            chat_id: LiveChat chat ID
            text: Message text
            author_id: Optional author ID (defaults to bot)

        Returns:
            API response with message details
        """
        logger.info("livechat_send_message", chat_id=chat_id)

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }

        if author_id:
            payload["author_id"] = author_id

        try:
            response = await self.post(
                "/agent/action/send_event",
                json={
                    "chat_id": chat_id,
                    "event": {
                        "type": "message",
                        "text": text,
                    },
                },
            )
            logger.info("livechat_message_sent", chat_id=chat_id)
            return response
        except Exception as e:
            logger.error(
                "livechat_send_message_failed",
                chat_id=chat_id,
                error=str(e),
            )
            raise

    async def create_customer_note(
        self,
        customer_id: str,
        title: str,
        text: str,
    ) -> Dict[str, Any]:
        """
        Create a note on a customer record.

        Args:
            customer_id: LiveChat customer ID
            title: Note title
            text: Note content

        Returns:
            API response
        """
        logger.info(
            "livechat_create_customer_note",
            customer_id=customer_id,
            title=title,
        )

        payload = {
            "title": title,
            "text": text,
        }

        try:
            response = await self.post(
                f"/agent/action/create_customer_note",
                json={
                    "customer_id": customer_id,
                    "note": payload,
                },
            )
            logger.info("livechat_customer_note_created", customer_id=customer_id)
            return response
        except Exception as e:
            logger.error(
                "livechat_create_customer_note_failed",
                customer_id=customer_id,
                error=str(e),
            )
            raise

    async def get_customer_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find a customer by email address.

        Args:
            email: Customer email

        Returns:
            Customer data or None if not found
        """
        logger.debug("livechat_get_customer_by_email", email=email)

        try:
            response = await self.get(
                "/agent/action/list_customers",
                params={"filters": {"email": {"values": [email]}}},
            )

            customers = response.get("customers", [])
            if customers:
                logger.info("livechat_customer_found", email=email)
                return customers[0]

            logger.info("livechat_customer_not_found", email=email)
            return None
        except Exception as e:
            logger.error(
                "livechat_get_customer_failed",
                email=email,
                error=str(e),
            )
            raise

    async def get_chat_details(self, chat_id: str) -> Dict[str, Any]:
        """
        Get chat details.

        Args:
            chat_id: LiveChat chat ID

        Returns:
            Chat details
        """
        logger.debug("livechat_get_chat_details", chat_id=chat_id)

        try:
            response = await self.post(
                "/agent/action/get_chat",
                json={"chat_id": chat_id},
            )
            return response
        except Exception as e:
            logger.error(
                "livechat_get_chat_failed",
                chat_id=chat_id,
                error=str(e),
            )
            raise
