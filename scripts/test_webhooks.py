"""Manual webhook testing script."""

import asyncio
import httpx
import argparse
from datetime import datetime

# Sample webhook payloads
LIVECHAT_CHAT_STARTED = {
    "webhook_id": f"test_lc_{datetime.utcnow().timestamp()}",
    "action": "incoming_chat",
    "organization_id": "test_org",
    "payload": {
        "chat": {
            "id": "test_chat_001",
            "users": [
                {
                    "id": "lc_agent_001",
                    "type": "agent",
                    "name": "John Smith",
                    "email": "agent1@example.com",
                },
                {
                    "id": "lc_customer_001",
                    "type": "customer",
                    "name": "Test Customer",
                    "email": "customer@example.com",
                },
            ],
        }
    },
}

LIVECHAT_CHAT_ENDED = {
    "webhook_id": f"test_lc_end_{datetime.utcnow().timestamp()}",
    "action": "chat_deactivated",
    "payload": {
        "chat_id": "test_chat_001",
        "chat": {
            "users": [
                {
                    "id": "lc_agent_001",
                    "type": "agent",
                }
            ]
        },
    },
}

RINGCENTRAL_CALL_STARTED = {
    "uuid": f"test_rc_{datetime.utcnow().timestamp()}",
    "event": "/restapi/v1.0/account/~/extension/101/telephony/sessions",
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "subscription_id": "test_subscription",
    "body": {
        "sessionId": "test_session_001",
        "id": "test_session_001",
        "parties": [
            {
                "extensionId": "101",
                "direction": {"value": "Inbound"},
                "from": {"phoneNumber": "+15551234567"},
                "to": {"extensionNumber": "101"},
                "status": {"code": "Answered"},
            }
        ],
    },
}

RINGCENTRAL_CALL_ENDED = {
    "uuid": f"test_rc_end_{datetime.utcnow().timestamp()}",
    "event": "/restapi/v1.0/account/~/extension/101/telephony/sessions",
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "subscription_id": "test_subscription",
    "body": {
        "sessionId": "test_session_001",
        "id": "test_session_001",
        "parties": [
            {
                "extensionId": "101",
                "status": {"code": "Disconnected"},
            }
        ],
    },
}


async def send_webhook(base_url: str, endpoint: str, payload: dict):
    """
    Send a test webhook to the application.

    Args:
        base_url: Base URL of the application
        endpoint: Webhook endpoint path
        payload: Webhook payload
    """
    url = f"{base_url}{endpoint}"

    print(f"\n📤 Sending webhook to: {url}")
    print(f"📦 Payload: {payload.get('webhook_id') or payload.get('uuid')}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=10.0)
            print(f"✅ Response: {response.status_code}")
            print(f"📄 Body: {response.json()}")
        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test webhooks manually")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the application",
    )
    parser.add_argument(
        "--platform",
        choices=["livechat", "ringcentral", "all"],
        default="all",
        help="Platform to test",
    )
    parser.add_argument(
        "--event",
        choices=["chat_started", "chat_ended", "call_started", "call_ended", "all"],
        default="all",
        help="Event to test",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🧪 Webhook Testing Script")
    print("=" * 60)
    print(f"Target: {args.base_url}")
    print(f"Platform: {args.platform}")
    print(f"Event: {args.event}")

    # Test LiveChat webhooks
    if args.platform in ["livechat", "all"]:
        if args.event in ["chat_started", "all"]:
            await send_webhook(
                args.base_url,
                "/webhooks/livechat/incoming_chat",
                LIVECHAT_CHAT_STARTED,
            )
            await asyncio.sleep(2)

        if args.event in ["chat_ended", "all"]:
            await send_webhook(
                args.base_url,
                "/webhooks/livechat/chat_deactivated",
                LIVECHAT_CHAT_ENDED,
            )
            await asyncio.sleep(2)

    # Test RingCentral webhooks
    if args.platform in ["ringcentral", "all"]:
        if args.event in ["call_started", "all"]:
            await send_webhook(
                args.base_url,
                "/webhooks/ringcentral/telephony-session",
                RINGCENTRAL_CALL_STARTED,
            )
            await asyncio.sleep(2)

        if args.event in ["call_ended", "all"]:
            await send_webhook(
                args.base_url,
                "/webhooks/ringcentral/telephony-session",
                RINGCENTRAL_CALL_ENDED,
            )

    print("\n" + "=" * 60)
    print("✅ Testing completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
