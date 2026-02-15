"""Demo script to trigger test webhooks for live demo."""

import asyncio
import sys
from pathlib import Path
import httpx
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_URL = "http://localhost:8000"


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_action(text):
    """Print an action message."""
    print(f"\n→ {text}")


def print_success(text):
    """Print a success message."""
    print(f"  ✓ {text}")


def print_error(text):
    """Print an error message."""
    print(f"  ✗ {text}")


async def send_livechat_chat_started(agent_id="lc_agent_001", chat_id=None):
    """Simulate a LiveChat chat starting."""
    if chat_id is None:
        chat_id = f"demo_chat_{datetime.now().timestamp()}"

    payload = {
        "webhook_id": f"webhook_{datetime.now().timestamp()}",
        "action": "incoming_chat",
        "payload": {
            "chat": {
                "id": chat_id,
                "users": [
                    {
                        "id": agent_id,
                        "type": "agent",
                        "email": "agent@example.com",
                        "name": "Demo Agent"
                    },
                    {
                        "id": "customer_demo",
                        "type": "customer",
                        "email": "customer@demo.com",
                        "name": "Demo Customer"
                    }
                ],
                "thread": {
                    "active": True
                }
            }
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/webhooks/livechat/incoming_chat",
                json=payload,
                timeout=10.0
            )
            if response.status_code == 200:
                print_success(f"LiveChat chat started webhook sent (Chat ID: {chat_id})")
                print(f"    Agent {agent_id} is now on a chat")
            else:
                print_error(f"Failed: {response.status_code} - {response.text[:100]}")
        except Exception as e:
            print_error(f"Error: {e}")


async def send_livechat_chat_ended(chat_id):
    """Simulate a LiveChat chat ending."""
    payload = {
        "webhook_id": f"webhook_{datetime.now().timestamp()}",
        "action": "chat_deactivated",
        "payload": {
            "chat": {
                "id": chat_id,
                "users": []
            }
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/webhooks/livechat/chat_deactivated",
                json=payload,
                timeout=10.0
            )
            if response.status_code == 200:
                print_success(f"LiveChat chat ended webhook sent (Chat ID: {chat_id})")
                print(f"    Agent is now available again")
            else:
                print_error(f"Failed: {response.status_code} - {response.text[:100]}")
        except Exception as e:
            print_error(f"Error: {e}")


async def send_ringcentral_call_started(extension_id="101", session_id=None):
    """Simulate a RingCentral call starting."""
    if session_id is None:
        session_id = f"demo_session_{datetime.now().timestamp()}"

    payload = {
        "uuid": f"webhook_{datetime.now().timestamp()}",
        "event": f"/restapi/v1.0/account/~/extension/{extension_id}/telephony/sessions",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "body": {
            "sessionId": session_id,
            "extensionId": extension_id,
            "parties": [
                {
                    "extensionId": extension_id,
                    "status": {
                        "code": "Answered"
                    },
                    "direction": "Inbound",
                    "from": {
                        "phoneNumber": "+15550001234"
                    },
                    "to": {
                        "phoneNumber": "+15550005678"
                    }
                }
            ]
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/webhooks/ringcentral/telephony-session",
                json=payload,
                timeout=10.0
            )
            if response.status_code == 200:
                print_success(f"RingCentral call started webhook sent (Session ID: {session_id})")
                print(f"    Extension {extension_id} is now on a call")
            else:
                print_error(f"Failed: {response.status_code} - {response.text[:100]}")
        except Exception as e:
            print_error(f"Error: {e}")


async def send_ringcentral_call_ended(extension_id="101", session_id=None):
    """Simulate a RingCentral call ending."""
    if session_id is None:
        session_id = f"demo_session_{datetime.now().timestamp()}"

    payload = {
        "uuid": f"webhook_{datetime.now().timestamp()}",
        "event": f"/restapi/v1.0/account/~/extension/{extension_id}/telephony/sessions",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "body": {
            "sessionId": session_id,
            "extensionId": extension_id,
            "parties": [
                {
                    "extensionId": extension_id,
                    "status": {
                        "code": "Disconnected"
                    }
                }
            ]
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/webhooks/ringcentral/telephony-session",
                json=payload,
                timeout=10.0
            )
            if response.status_code == 200:
                print_success(f"RingCentral call ended webhook sent (Session ID: {session_id})")
                print(f"    Extension {extension_id} is now available again")
            else:
                print_error(f"Failed: {response.status_code} - {response.text[:100]}")
        except Exception as e:
            print_error(f"Error: {e}")


async def demo_scenario_chat():
    """Demo scenario: Agent receives a LiveChat chat."""
    print_header("Demo: LiveChat Chat Scenario")
    print("\nThis simulates an agent receiving and completing a chat.")
    print("Watch the frontend to see the agent status change!")

    chat_id = f"demo_chat_{datetime.now().timestamp()}"

    print_action("Sending: Agent receives incoming chat...")
    await send_livechat_chat_started(agent_id="lc_agent_001", chat_id=chat_id)

    print("\n⏰ Wait 5 seconds... (check the frontend - agent should be busy)")
    await asyncio.sleep(5)

    print_action("Sending: Chat ends...")
    await send_livechat_chat_ended(chat_id=chat_id)

    print("\n✓ Demo complete! Agent should return to available status.")


async def demo_scenario_call():
    """Demo scenario: Agent receives a RingCentral call."""
    print_header("Demo: RingCentral Call Scenario")
    print("\nThis simulates an agent receiving and completing a call.")
    print("Watch the frontend to see the agent status change!")

    session_id = f"demo_session_{datetime.now().timestamp()}"

    print_action("Sending: Agent receives incoming call...")
    await send_ringcentral_call_started(extension_id="101", session_id=session_id)

    print("\n⏰ Wait 5 seconds... (check the frontend - agent should be busy)")
    await asyncio.sleep(5)

    print_action("Sending: Call ends...")
    await send_ringcentral_call_ended(extension_id="101", session_id=session_id)

    print("\n✓ Demo complete! Agent should return to available status.")


async def demo_scenario_both():
    """Demo scenario: Show syncing between both platforms."""
    print_header("Demo: Cross-Platform Sync Scenario")
    print("\nThis simulates events on both platforms to show unified tracking.")
    print("Watch the frontend to see both platforms sync!")

    print_action("1. Agent receives LiveChat chat...")
    chat_id = f"demo_chat_{datetime.now().timestamp()}"
    await send_livechat_chat_started(agent_id="lc_agent_002", chat_id=chat_id)

    print("\n⏰ Wait 3 seconds...")
    await asyncio.sleep(3)

    print_action("2. Different agent receives RingCentral call...")
    session_id = f"demo_session_{datetime.now().timestamp()}"
    await send_ringcentral_call_started(extension_id="103", session_id=session_id)

    print("\n⏰ Wait 4 seconds...")
    await asyncio.sleep(4)

    print_action("3. LiveChat chat ends...")
    await send_livechat_chat_ended(chat_id=chat_id)

    print("\n⏰ Wait 3 seconds...")
    await asyncio.sleep(3)

    print_action("4. RingCentral call ends...")
    await send_ringcentral_call_ended(extension_id="103", session_id=session_id)

    print("\n✓ Demo complete! All agents should be available again.")


async def interactive_menu():
    """Interactive menu for triggering demo events."""
    while True:
        print_header("Demo Webhook Trigger Menu")
        print("\nChoose a demo scenario:")
        print("\n  1. LiveChat Chat (agent goes busy, then available)")
        print("  2. RingCentral Call (agent goes busy, then available)")
        print("  3. Both Platforms (show cross-platform sync)")
        print("  4. Start LiveChat Chat Only")
        print("  5. End LiveChat Chat Only")
        print("  6. Start RingCentral Call Only")
        print("  7. End RingCentral Call Only")
        print("  8. Exit")

        choice = input("\n→ Enter your choice (1-8): ").strip()

        if choice == "1":
            await demo_scenario_chat()
        elif choice == "2":
            await demo_scenario_call()
        elif choice == "3":
            await demo_scenario_both()
        elif choice == "4":
            agent_id = input("  Agent ID (default: lc_agent_001): ").strip() or "lc_agent_001"
            await send_livechat_chat_started(agent_id=agent_id)
        elif choice == "5":
            chat_id = input("  Chat ID: ").strip()
            if chat_id:
                await send_livechat_chat_ended(chat_id)
            else:
                print_error("Chat ID required")
        elif choice == "6":
            extension_id = input("  Extension ID (default: 101): ").strip() or "101"
            await send_ringcentral_call_started(extension_id=extension_id)
        elif choice == "7":
            session_id = input("  Session ID: ").strip()
            if session_id:
                await send_ringcentral_call_ended(session_id=session_id)
            else:
                print_error("Session ID required")
        elif choice == "8":
            print("\n👋 Goodbye!")
            break
        else:
            print_error("Invalid choice. Please try again.")

        print("\n" + "-" * 60)
        input("Press Enter to continue...")


async def main():
    """Main function."""
    print_header("LiveChat-RingCentral Sync Demo Webhook Trigger")
    print("\nThis tool simulates webhook events to demonstrate real-time syncing.")
    print("Open http://localhost:8000/demo/ in your browser to watch the changes!")

    if len(sys.argv) > 1:
        scenario = sys.argv[1]
        if scenario == "chat":
            await demo_scenario_chat()
        elif scenario == "call":
            await demo_scenario_call()
        elif scenario == "both":
            await demo_scenario_both()
        else:
            print_error(f"Unknown scenario: {scenario}")
            print("Usage: python demo_webhook_trigger.py [chat|call|both]")
    else:
        await interactive_menu()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)
