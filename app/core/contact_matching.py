"""Customer contact matching logic."""

from typing import Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Customer
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContactMatcher:
    """Match customers between LiveChat and RingCentral."""

    def __init__(self, db: AsyncSession):
        """
        Initialize contact matcher.

        Args:
            db: Database session
        """
        self.db = db

    async def match_by_email(self, email: str) -> Optional[Customer]:
        """
        Find customer by email address.

        Args:
            email: Customer email

        Returns:
            Customer record or None
        """
        if not email:
            return None

        logger.debug("matching_customer_by_email", email=email)

        stmt = select(Customer).where(Customer.email == email)
        result = await self.db.execute(stmt)
        customer = result.scalar_one_or_none()

        if customer:
            logger.info("customer_matched_by_email", email=email, customer_id=customer.id)

        return customer

    async def match_by_phone(self, phone: str) -> Optional[Customer]:
        """
        Find customer by phone number.

        Args:
            phone: Customer phone number

        Returns:
            Customer record or None
        """
        if not phone:
            return None

        logger.debug("matching_customer_by_phone", phone=phone)

        # Normalize phone number (remove spaces, dashes, etc.)
        normalized_phone = "".join(c for c in phone if c.isdigit())

        stmt = select(Customer).where(Customer.phone.contains(normalized_phone[-10:]))
        result = await self.db.execute(stmt)
        customer = result.scalar_one_or_none()

        if customer:
            logger.info("customer_matched_by_phone", phone=phone, customer_id=customer.id)

        return customer

    async def find_or_create_customer(
        self,
        livechat_customer_id: Optional[str] = None,
        ringcentral_contact_id: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Customer:
        """
        Find existing customer or create new one.

        Tries to match by:
        1. External IDs (livechat_customer_id or ringcentral_contact_id)
        2. Email address
        3. Phone number
        4. Create new if no match

        Args:
            livechat_customer_id: LiveChat customer ID
            ringcentral_contact_id: RingCentral contact ID
            email: Customer email
            phone: Customer phone
            name: Customer name

        Returns:
            Customer record
        """
        logger.debug(
            "finding_or_creating_customer",
            livechat_id=livechat_customer_id,
            ringcentral_id=ringcentral_contact_id,
            email=email,
            phone=phone,
        )

        # Try to match by external IDs
        if livechat_customer_id or ringcentral_contact_id:
            conditions = []
            if livechat_customer_id:
                conditions.append(Customer.livechat_customer_id == livechat_customer_id)
            if ringcentral_contact_id:
                conditions.append(Customer.ringcentral_contact_id == ringcentral_contact_id)

            stmt = select(Customer).where(or_(*conditions))
            result = await self.db.execute(stmt)
            customer = result.scalar_one_or_none()

            if customer:
                logger.info("customer_found_by_external_id", customer_id=customer.id)

                # Update with any new information
                if livechat_customer_id and not customer.livechat_customer_id:
                    customer.livechat_customer_id = livechat_customer_id
                if ringcentral_contact_id and not customer.ringcentral_contact_id:
                    customer.ringcentral_contact_id = ringcentral_contact_id
                if email and not customer.email:
                    customer.email = email
                if phone and not customer.phone:
                    customer.phone = phone
                if name and not customer.name:
                    customer.name = name

                await self.db.commit()
                await self.db.refresh(customer)
                return customer

        # Try to match by email
        if email:
            customer = await self.match_by_email(email)
            if customer:
                # Update with new platform IDs
                if livechat_customer_id:
                    customer.livechat_customer_id = livechat_customer_id
                if ringcentral_contact_id:
                    customer.ringcentral_contact_id = ringcentral_contact_id
                if phone and not customer.phone:
                    customer.phone = phone
                if name and not customer.name:
                    customer.name = name

                await self.db.commit()
                await self.db.refresh(customer)
                return customer

        # Try to match by phone
        if phone:
            customer = await self.match_by_phone(phone)
            if customer:
                # Update with new information
                if livechat_customer_id:
                    customer.livechat_customer_id = livechat_customer_id
                if ringcentral_contact_id:
                    customer.ringcentral_contact_id = ringcentral_contact_id
                if email and not customer.email:
                    customer.email = email
                if name and not customer.name:
                    customer.name = name

                await self.db.commit()
                await self.db.refresh(customer)
                return customer

        # No match found, create new customer
        customer = Customer(
            livechat_customer_id=livechat_customer_id,
            ringcentral_contact_id=ringcentral_contact_id,
            email=email,
            phone=phone,
            name=name,
        )

        self.db.add(customer)
        await self.db.commit()
        await self.db.refresh(customer)

        logger.info("customer_created", customer_id=customer.id)
        return customer
