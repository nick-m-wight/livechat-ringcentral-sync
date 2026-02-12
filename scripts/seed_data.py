"""Seed database with test agent mappings."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import Agent
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def seed_agents():
    """Seed test agent mappings."""
    async with AsyncSessionLocal() as db:
        # Check if agents already exist
        stmt = select(Agent)
        result = await db.execute(stmt)
        existing_agents = result.scalars().all()

        if existing_agents:
            logger.info("agents_already_exist", count=len(existing_agents))
            print(f"✓ Found {len(existing_agents)} existing agents:")
            for agent in existing_agents:
                print(f"  - {agent.name} (LiveChat: {agent.livechat_agent_id}, RC: {agent.ringcentral_extension_id})")
            return

        # Create test agents
        test_agents = [
            Agent(
                livechat_agent_id="lc_agent_001",
                ringcentral_extension_id="101",
                email="agent1@example.com",
                name="John Smith",
            ),
            Agent(
                livechat_agent_id="lc_agent_002",
                ringcentral_extension_id="102",
                email="agent2@example.com",
                name="Jane Doe",
            ),
            Agent(
                livechat_agent_id="lc_agent_003",
                ringcentral_extension_id="103",
                email="agent3@example.com",
                name="Bob Wilson",
            ),
        ]

        for agent in test_agents:
            db.add(agent)

        await db.commit()

        logger.info("agents_seeded", count=len(test_agents))
        print(f"\n✓ Seeded {len(test_agents)} test agents:")
        for agent in test_agents:
            print(f"  - {agent.name} (LiveChat: {agent.livechat_agent_id}, RC: {agent.ringcentral_extension_id})")


async def main():
    """Main seed function."""
    print("Seeding database with test data...\n")

    try:
        await seed_agents()
        print("\n✓ Database seeding completed successfully!")
    except Exception as e:
        logger.error("seed_failed", error=str(e))
        print(f"\n✗ Seeding failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
