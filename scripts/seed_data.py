"""Seed database with comprehensive demo data."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import (
    Agent,
    AgentState,
    Customer,
    Conversation,
    Message,
    CallRecord,
    SyncLog,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def seed_agents(db):
    """Seed test agent mappings."""
    # Check if agents already exist
    stmt = select(Agent)
    result = await db.execute(stmt)
    existing_agents = result.scalars().all()

    if existing_agents:
        logger.info("agents_already_exist", count=len(existing_agents))
        print(f"✓ Found {len(existing_agents)} existing agents")
        return existing_agents

    # Create test agents
    test_agents = [
        Agent(
            livechat_agent_id="lc_agent_001",
            ringcentral_extension_id="101",
            email="john.smith@example.com",
            name="John Smith",
        ),
        Agent(
            livechat_agent_id="lc_agent_002",
            ringcentral_extension_id="102",
            email="jane.doe@example.com",
            name="Jane Doe",
        ),
        Agent(
            livechat_agent_id="lc_agent_003",
            ringcentral_extension_id="103",
            email="bob.wilson@example.com",
            name="Bob Wilson",
        ),
        Agent(
            livechat_agent_id="lc_agent_004",
            ringcentral_extension_id="104",
            email="alice.brown@example.com",
            name="Alice Brown",
        ),
    ]

    for agent in test_agents:
        db.add(agent)

    await db.commit()

    # Refresh to get IDs
    for agent in test_agents:
        await db.refresh(agent)

    logger.info("agents_seeded", count=len(test_agents))
    print(f"✓ Seeded {len(test_agents)} agents")
    return test_agents


async def seed_agent_states(db, agents):
    """Seed agent states - ALL agents start as available."""
    now = datetime.now()

    # Historical state configurations for demo variety
    historical_configs = [
        ("accepting_chats", "Available", "available"),
        ("not_accepting_chats", "Busy", "on_call"),
        ("not_accepting_chats", "Busy", "chatting"),
    ]

    agent_states = []
    for agent in agents:
        # Create some historical states for demo purposes
        for j in range(3):
            past_time = now - timedelta(hours=random.randint(2, 48))
            historical_config = random.choice(historical_configs)
            state = AgentState(
                agent_id=agent.id,
                livechat_status=historical_config[0],
                ringcentral_presence=historical_config[1],
                reason=historical_config[2],
                state_changed_at=past_time,
                created_at=past_time,
            )
            db.add(state)

        # ALL agents start as AVAILABLE - clean demo start!
        current_state = AgentState(
            agent_id=agent.id,
            livechat_status="accepting_chats",
            ringcentral_presence="Available",
            reason="available",
            state_changed_at=now,
            created_at=now,
        )
        db.add(current_state)
        agent_states.append(current_state)

    await db.commit()

    print(f"✓ Seeded {len(agent_states)} agents - ALL AVAILABLE")
    return agent_states


async def seed_customers(db):
    """Seed test customers."""
    customers = [
        Customer(
            name="Emily Johnson",
            email="emily.j@customer.com",
            phone="+1-555-0101",
            livechat_customer_id="lc_customer_001",
        ),
        Customer(
            name="Michael Davis",
            email="mdavis@business.com",
            phone="+1-555-0102",
            livechat_customer_id="lc_customer_002",
        ),
        Customer(
            name="Sarah Martinez",
            email="sarah.m@email.com",
            phone="+1-555-0103",
            ringcentral_contact_id="rc_contact_001",
        ),
        Customer(
            name="David Lee",
            email="dlee@company.com",
            phone="+1-555-0104",
            livechat_customer_id="lc_customer_003",
        ),
        Customer(
            name="Lisa Anderson",
            email="landerson@corp.com",
            phone="+1-555-0105",
            ringcentral_contact_id="rc_contact_002",
        ),
        Customer(
            email="anonymous@user.com",
            phone="+1-555-0106",
        ),
    ]

    for customer in customers:
        db.add(customer)

    await db.commit()

    for customer in customers:
        await db.refresh(customer)

    print(f"✓ Seeded {len(customers)} customers")
    return customers


async def seed_conversations(db, agents, customers):
    """Seed test conversations."""
    now = datetime.now()
    conversations = []

    # Create mix of active and ended conversations
    conv_configs = [
        # (type, platform, status, hours_ago, duration_minutes)
        ("chat", "livechat", "active", 0.5, None),
        ("chat", "livechat", "active", 1, None),
        ("call", "ringcentral", "active", 0.25, None),
        ("chat", "livechat", "ended", 2, 15),
        ("chat", "livechat", "ended", 3, 22),
        ("call", "ringcentral", "ended", 4, 8),
        ("chat", "livechat", "ended", 5, 18),
        ("call", "ringcentral", "ended", 6, 12),
        ("chat", "livechat", "ended", 8, 25),
        ("call", "ringcentral", "ended", 10, 5),
    ]

    for i, config in enumerate(conv_configs):
        conv_type, platform, status, hours_ago, duration_minutes = config
        agent = random.choice(agents)
        customer = random.choice(customers) if random.random() > 0.2 else None

        started_at = now - timedelta(hours=hours_ago)
        ended_at = None
        duration_seconds = None

        if status == "ended":
            ended_at = started_at + timedelta(minutes=duration_minutes)
            duration_seconds = duration_minutes * 60

        conv = Conversation(
            conversation_type=conv_type,
            platform=platform,
            livechat_chat_id=f"lc_chat_{i+1}" if platform == "livechat" else None,
            ringcentral_session_id=f"rc_session_{i+1}" if platform == "ringcentral" else None,
            agent_id=agent.id,
            customer_id=customer.id if customer else None,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            status=status,
        )
        db.add(conv)
        conversations.append(conv)

    await db.commit()

    for conv in conversations:
        await db.refresh(conv)

    print(f"✓ Seeded {len(conversations)} conversations ({sum(1 for c in conversations if c.status == 'active')} active)")
    return conversations


async def seed_messages(db, conversations):
    """Seed messages for chat conversations."""
    now = datetime.now()
    message_templates = [
        ("customer", "Hello, I need help with my account"),
        ("agent", "Hi! I'd be happy to help. What seems to be the issue?"),
        ("customer", "I can't access my dashboard"),
        ("agent", "Let me look into that for you. Can you tell me your username?"),
        ("customer", "Sure, it's user@example.com"),
        ("agent", "Thank you. I see the issue. Let me reset that for you."),
        ("customer", "Great, thank you!"),
        ("agent", "All set! You should be able to log in now."),
        ("customer", "Perfect, it's working now. Thanks!"),
        ("agent", "You're welcome! Is there anything else I can help with?"),
        ("customer", "No, that's all. Thanks again!"),
        ("agent", "Have a great day!"),
    ]

    message_count = 0
    for conv in conversations:
        if conv.conversation_type == "chat":
            num_messages = random.randint(3, 12)
            for i in range(num_messages):
                template = message_templates[i % len(message_templates)]
                sender_type, text = template

                sent_at = conv.started_at + timedelta(minutes=i)

                message = Message(
                    conversation_id=conv.id,
                    sender_type=sender_type,
                    message_text=text,
                    message_type="text",
                    sent_at=sent_at,
                    synced_to_livechat=random.random() > 0.1,
                    synced_to_ringcentral=random.random() > 0.1,
                )
                db.add(message)
                message_count += 1

    await db.commit()
    print(f"✓ Seeded {message_count} messages")


async def seed_call_records(db, conversations):
    """Seed call records for call conversations."""
    call_count = 0
    for conv in conversations:
        if conv.conversation_type == "call":
            call_record = CallRecord(
                conversation_id=conv.id,
                session_id=conv.ringcentral_session_id,
                direction=random.choice(["inbound", "outbound"]),
                from_number="+1-555-0200",
                to_number="+1-555-0100",
                call_status="Connected" if conv.status == "active" else "Disconnected",
                recording_url=f"https://recordings.example.com/{conv.ringcentral_session_id}.mp3" if conv.status == "ended" else None,
                recording_duration=conv.duration_seconds if conv.status == "ended" else None,
            )
            db.add(call_record)
            call_count += 1

    await db.commit()
    print(f"✓ Seeded {call_count} call records")


async def seed_sync_logs(db, agents, conversations):
    """Seed sync operation logs."""
    now = datetime.now()
    operations = [
        "agent_state_sync",
        "message_sync",
        "conversation_sync",
        "call_sync",
    ]

    logs = []
    for i in range(150):
        operation = random.choice(operations)
        status = "success" if random.random() > 0.05 else "failed"
        error_message = "API timeout" if status == "failed" else None

        log = SyncLog(
            operation_type=operation,
            source_platform=random.choice(["livechat", "ringcentral"]),
            target_platform=random.choice(["livechat", "ringcentral"]),
            status=status,
            error_message=error_message,
            retry_count=random.randint(0, 2) if status == "failed" else 0,
            agent_id=random.choice(agents).id if random.random() > 0.5 else None,
            conversation_id=random.choice(conversations).id if random.random() > 0.5 else None,
            created_at=now - timedelta(hours=random.randint(0, 48)),
        )
        db.add(log)
        logs.append(log)

    await db.commit()
    print(f"✓ Seeded {len(logs)} sync logs ({sum(1 for l in logs if l.status == 'success')} successful)")


async def clear_all_data(db):
    """Clear all existing data from database."""
    print("\n⚠️  Clearing existing data...")

    # Delete in reverse order of dependencies
    for model in [SyncLog, CallRecord, Message, Conversation, AgentState, Customer, Agent]:
        result = await db.execute(select(model))
        items = result.scalars().all()
        for item in items:
            await db.delete(item)

    await db.commit()
    print("✓ Cleared all existing data")


async def main():
    """Main seed function."""
    print("=" * 60)
    print("Seeding database with comprehensive demo data...")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            # Option to clear existing data
            if "--clear" in sys.argv:
                await clear_all_data(db)

            # Seed data in order
            print("\n1. Creating agents...")
            agents = await seed_agents(db)

            print("\n2. Creating agent states...")
            await seed_agent_states(db, agents)

            print("\n3. Creating customers...")
            customers = await seed_customers(db)

            print("\n4. Creating conversations...")
            conversations = await seed_conversations(db, agents, customers)

            print("\n5. Creating messages...")
            await seed_messages(db, conversations)

            print("\n6. Creating call records...")
            await seed_call_records(db, conversations)

            print("\n7. Creating sync logs...")
            await seed_sync_logs(db, agents, conversations)

            print("\n" + "=" * 60)
            print("✓ Database seeding completed successfully!")
            print("=" * 60)
            print("\nYou can now access the demo at: http://localhost:8000/demo/")
            print("\nRun with --clear flag to clear existing data first")

        except Exception as e:
            logger.error("seed_failed", error=str(e))
            print(f"\n✗ Seeding failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
