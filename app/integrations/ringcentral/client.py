"""RingCentral API client."""

from typing import Optional, Dict, Any

from app.config import settings
from app.integrations.base_client import BaseHTTPClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RingCentralClient(BaseHTTPClient):
    """RingCentral API client for managing presence, messaging, and notes."""

    def __init__(self) -> None:
        """Initialize RingCentral client."""
        super().__init__(
            base_url=settings.RINGCENTRAL_API_URL,
            auth_token=settings.RINGCENTRAL_JWT_TOKEN,
        )

    async def set_user_presence(
        self,
        extension_id: str,
        presence_status: str,
        user_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Set user presence status.

        Args:
            extension_id: RingCentral extension ID
            presence_status: Presence status (Available, Busy, Offline)
            user_status: Optional user status message

        Returns:
            API response
        """
        logger.info(
            "ringcentral_set_user_presence",
            extension_id=extension_id,
            presence_status=presence_status,
        )

        payload: Dict[str, Any] = {
            "presenceStatus": presence_status,
        }

        if user_status:
            payload["userStatus"] = user_status

        try:
            response = await self.put(
                f"/restapi/v1.0/account/~/extension/{extension_id}/presence",
                json=payload,
            )
            logger.info(
                "ringcentral_presence_updated",
                extension_id=extension_id,
                status=presence_status,
            )
            return response
        except Exception as e:
            logger.error(
                "ringcentral_set_presence_failed",
                extension_id=extension_id,
                error=str(e),
            )
            raise

    async def get_user_presence(self, extension_id: str) -> Dict[str, Any]:
        """
        Get user presence status.

        Args:
            extension_id: RingCentral extension ID

        Returns:
            Presence information
        """
        logger.debug("ringcentral_get_user_presence", extension_id=extension_id)

        try:
            response = await self.get(
                f"/restapi/v1.0/account/~/extension/{extension_id}/presence"
            )
            return response
        except Exception as e:
            logger.error(
                "ringcentral_get_presence_failed",
                extension_id=extension_id,
                error=str(e),
            )
            raise

    async def send_team_message(
        self,
        chat_id: str,
        text: str,
    ) -> Dict[str, Any]:
        """
        Send a message to a team chat.

        Args:
            chat_id: RingCentral chat/conversation ID
            text: Message text

        Returns:
            API response
        """
        logger.info("ringcentral_send_team_message", chat_id=chat_id)

        payload = {
            "text": text,
        }

        try:
            response = await self.post(
                f"/team-messaging/v1/chats/{chat_id}/posts",
                json=payload,
            )
            logger.info("ringcentral_message_sent", chat_id=chat_id)
            return response
        except Exception as e:
            logger.error(
                "ringcentral_send_message_failed",
                chat_id=chat_id,
                error=str(e),
            )
            raise

    async def create_note(
        self,
        title: str,
        body: str,
        contact_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a note (e.g., for call transcripts).

        Args:
            title: Note title
            body: Note content
            contact_id: Optional contact ID to associate with

        Returns:
            API response
        """
        logger.info("ringcentral_create_note", title=title)

        payload: Dict[str, Any] = {
            "subject": title,
            "body": body,
        }

        if contact_id:
            payload["contactId"] = contact_id

        try:
            response = await self.post(
                "/restapi/v1.0/account/~/extension/~/note",
                json=payload,
            )
            logger.info("ringcentral_note_created", title=title)
            return response
        except Exception as e:
            logger.error(
                "ringcentral_create_note_failed",
                title=title,
                error=str(e),
            )
            raise

    async def get_call_recording(
        self,
        recording_id: str,
    ) -> Dict[str, Any]:
        """
        Get call recording details.

        Args:
            recording_id: Recording ID

        Returns:
            Recording information
        """
        logger.debug("ringcentral_get_call_recording", recording_id=recording_id)

        try:
            response = await self.get(
                f"/restapi/v1.0/account/~/recording/{recording_id}"
            )
            return response
        except Exception as e:
            logger.error(
                "ringcentral_get_recording_failed",
                recording_id=recording_id,
                error=str(e),
            )
            raise

    async def get_telephony_session(
        self,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Get telephony session details.

        Args:
            session_id: Session ID

        Returns:
            Session details
        """
        logger.debug("ringcentral_get_telephony_session", session_id=session_id)

        try:
            response = await self.get(
                f"/restapi/v1.0/account/~/telephony/sessions/{session_id}"
            )
            return response
        except Exception as e:
            logger.error(
                "ringcentral_get_session_failed",
                session_id=session_id,
                error=str(e),
            )
            raise
