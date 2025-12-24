"""
Campaign service for business logic.
"""
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.campaign import (
    Campaign,
    CampaignContact,
    CampaignStatus,
    ContactStatus,
    CallDisposition,
)
from app.models.contact import Contact, ContactList, DNCEntry
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignStatsResponse,
)


class CampaignService:
    """Service for campaign-related operations."""

    # Valid status transitions
    VALID_TRANSITIONS = {
        CampaignStatus.DRAFT: [CampaignStatus.SCHEDULED, CampaignStatus.RUNNING, CampaignStatus.CANCELLED],
        CampaignStatus.SCHEDULED: [CampaignStatus.RUNNING, CampaignStatus.CANCELLED, CampaignStatus.DRAFT],
        CampaignStatus.RUNNING: [CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.CANCELLED],
        CampaignStatus.PAUSED: [CampaignStatus.RUNNING, CampaignStatus.CANCELLED],
        CampaignStatus.COMPLETED: [],
        CampaignStatus.CANCELLED: [],
    }

    async def list_campaigns(
        self,
        db: AsyncSession,
        organization_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[CampaignStatus] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Campaign], int]:
        """List campaigns for an organization with pagination."""
        query = select(Campaign).where(Campaign.organization_id == organization_id)

        if status:
            query = query.where(Campaign.status == status)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Campaign.name.ilike(search_term),
                    Campaign.description.ilike(search_term),
                )
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        total = result.scalar() or 0

        # Get paginated results
        query = query.order_by(Campaign.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        campaigns = result.scalars().all()

        return list(campaigns), total

    async def get_campaign(
        self,
        db: AsyncSession,
        campaign_id: str,
        organization_id: str,
    ) -> Optional[Campaign]:
        """Get a campaign by ID."""
        query = select(Campaign).where(
            and_(
                Campaign.id == campaign_id,
                Campaign.organization_id == organization_id,
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create_campaign(
        self,
        db: AsyncSession,
        organization_id: str,
        user_id: str,
        data: CampaignCreate,
    ) -> Campaign:
        """Create a new campaign."""
        # Verify contact list exists and belongs to organization
        contact_list = await db.execute(
            select(ContactList).where(
                and_(
                    ContactList.id == data.contact_list_id,
                    ContactList.organization_id == organization_id,
                )
            )
        )
        contact_list = contact_list.scalar_one_or_none()
        if not contact_list:
            raise ValueError("Contact list not found")

        campaign = Campaign(
            name=data.name,
            description=data.description,
            organization_id=organization_id,
            contact_list_id=data.contact_list_id,
            ivr_flow_id=data.ivr_flow_id,
            greeting_audio_id=data.greeting_audio_id,
            voicemail_audio_id=data.voicemail_audio_id,
            dialing_mode=data.dialing_mode,
            max_concurrent_calls=data.max_concurrent_calls,
            calls_per_minute=data.calls_per_minute,
            max_retries=data.max_retries,
            retry_delay_minutes=data.retry_delay_minutes,
            retry_on_no_answer=data.retry_on_no_answer,
            retry_on_busy=data.retry_on_busy,
            retry_on_failed=data.retry_on_failed,
            ring_timeout_seconds=data.ring_timeout_seconds,
            amd_enabled=data.amd_enabled,
            amd_action_human=data.amd_action_human.value if data.amd_action_human else None,
            amd_action_machine=data.amd_action_machine.value if data.amd_action_machine else None,
            scheduled_start=data.scheduled_start,
            scheduled_end=data.scheduled_end,
            calling_hours_start=data.calling_hours_start,
            calling_hours_end=data.calling_hours_end,
            respect_timezone=data.respect_timezone,
            status=CampaignStatus.DRAFT,
            created_by_id=user_id,
        )

        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)

        return campaign

    async def update_campaign(
        self,
        db: AsyncSession,
        campaign: Campaign,
        data: CampaignUpdate,
    ) -> Campaign:
        """Update a campaign."""
        # Some fields can only be changed in DRAFT status
        draft_only_fields = ["contact_list_id"]

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field in draft_only_fields and campaign.status != CampaignStatus.DRAFT:
                raise ValueError(f"Cannot change {field} after campaign has been started")

            # Handle AMD action enums
            if field in ["amd_action_human", "amd_action_machine"] and value is not None:
                value = value.value

            setattr(campaign, field, value)

        await db.commit()
        await db.refresh(campaign)

        return campaign

    async def delete_campaign(
        self,
        db: AsyncSession,
        campaign: Campaign,
    ) -> None:
        """Delete a campaign."""
        # Can only delete DRAFT or CANCELLED campaigns
        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.CANCELLED]:
            raise ValueError("Can only delete draft or cancelled campaigns")

        await db.delete(campaign)
        await db.commit()

    async def update_status(
        self,
        db: AsyncSession,
        campaign: Campaign,
        new_status: CampaignStatus,
    ) -> Campaign:
        """Update campaign status with validation."""
        current_status = campaign.status

        # Validate transition
        if new_status not in self.VALID_TRANSITIONS.get(current_status, []):
            raise ValueError(
                f"Invalid status transition from {current_status.value} to {new_status.value}"
            )

        campaign.status = new_status

        # Handle state-specific logic
        if new_status == CampaignStatus.RUNNING and not campaign.started_at:
            campaign.started_at = datetime.utcnow()
            # Populate campaign contacts if not already done
            await self.populate_campaign_contacts(db, campaign)

        elif new_status == CampaignStatus.COMPLETED:
            campaign.completed_at = datetime.utcnow()

        elif new_status == CampaignStatus.CANCELLED:
            if not campaign.completed_at:
                campaign.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(campaign)

        return campaign

    async def populate_campaign_contacts(
        self,
        db: AsyncSession,
        campaign: Campaign,
    ) -> int:
        """Copy contacts from contact list to campaign contacts."""
        # Check if already populated
        existing_count = await db.execute(
            select(func.count(CampaignContact.id)).where(CampaignContact.campaign_id == campaign.id)
        )
        if existing_count.scalar() > 0:
            return 0

        # Get valid contacts from the contact list
        contacts_query = select(Contact).where(
            and_(
                Contact.contact_list_id == campaign.contact_list_id,
                Contact.is_valid == True,
            )
        )
        result = await db.execute(contacts_query)
        contacts = result.scalars().all()

        # Check against DNC list
        dnc_query = select(DNCEntry.phone_number).where(
            or_(
                DNCEntry.organization_id == campaign.organization_id,
                DNCEntry.organization_id.is_(None),  # Global DNC
            )
        )
        dnc_result = await db.execute(dnc_query)
        dnc_numbers = set(row[0] for row in dnc_result.all())

        # Create campaign contacts
        campaign_contacts = []
        dnc_count = 0

        for contact in contacts:
            phone = contact.phone_number_e164 or contact.phone_number
            if phone in dnc_numbers:
                status = ContactStatus.DNC
                dnc_count += 1
            else:
                status = ContactStatus.PENDING

            campaign_contact = CampaignContact(
                campaign_id=campaign.id,
                contact_id=contact.id,
                status=status,
            )
            campaign_contacts.append(campaign_contact)

        db.add_all(campaign_contacts)

        # Update campaign statistics
        campaign.total_contacts = len(campaign_contacts)

        await db.commit()

        return len(campaign_contacts)

    async def get_campaign_contacts(
        self,
        db: AsyncSession,
        campaign_id: str,
        organization_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[ContactStatus] = None,
    ) -> Tuple[List[CampaignContact], int]:
        """Get contacts for a campaign with pagination."""
        # Verify campaign belongs to organization
        campaign = await self.get_campaign(db, campaign_id, organization_id)
        if not campaign:
            raise ValueError("Campaign not found")

        query = (
            select(CampaignContact)
            .options(selectinload(CampaignContact.contact))
            .where(CampaignContact.campaign_id == campaign_id)
        )

        if status:
            query = query.where(CampaignContact.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        total = result.scalar() or 0

        # Get paginated results
        query = query.order_by(CampaignContact.priority, CampaignContact.created_at)
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        contacts = result.scalars().all()

        return list(contacts), total

    async def get_statistics(
        self,
        db: AsyncSession,
        campaign_id: str,
        organization_id: str,
    ) -> CampaignStatsResponse:
        """Get detailed statistics for a campaign."""
        campaign = await self.get_campaign(db, campaign_id, organization_id)
        if not campaign:
            raise ValueError("Campaign not found")

        # Count contacts by status
        status_counts = await db.execute(
            select(CampaignContact.status, func.count())
            .where(CampaignContact.campaign_id == campaign_id)
            .group_by(CampaignContact.status)
        )
        status_dict = {row[0]: row[1] for row in status_counts.all()}

        # Count calls by disposition
        disposition_counts = await db.execute(
            select(CampaignContact.last_disposition, func.count())
            .where(
                and_(
                    CampaignContact.campaign_id == campaign_id,
                    CampaignContact.last_disposition.isnot(None),
                )
            )
            .group_by(CampaignContact.last_disposition)
        )
        disposition_dict = {row[0]: row[1] for row in disposition_counts.all()}

        # Calculate stats
        total_contacts = campaign.total_contacts or sum(status_dict.values())
        contacts_called = campaign.contacts_called

        answered_human = disposition_dict.get(CallDisposition.ANSWERED_HUMAN, 0)
        answered_machine = disposition_dict.get(CallDisposition.ANSWERED_MACHINE, 0)
        total_answered = answered_human + answered_machine

        # Calculate rates
        answer_rate = (total_answered / contacts_called * 100) if contacts_called > 0 else 0
        completion_rate = (campaign.contacts_completed / total_contacts * 100) if total_contacts > 0 else 0
        human_rate = (answered_human / total_answered * 100) if total_answered > 0 else 0

        return CampaignStatsResponse(
            campaign_id=campaign.id,
            status=campaign.status,
            total_contacts=total_contacts,
            contacts_pending=status_dict.get(ContactStatus.PENDING, 0),
            contacts_in_progress=status_dict.get(ContactStatus.IN_PROGRESS, 0),
            contacts_completed=status_dict.get(ContactStatus.COMPLETED, 0),
            contacts_failed=status_dict.get(ContactStatus.FAILED, 0),
            contacts_dnc=status_dict.get(ContactStatus.DNC, 0),
            contacts_skipped=status_dict.get(ContactStatus.SKIPPED, 0),
            total_calls=contacts_called,
            answered_human=answered_human,
            answered_machine=answered_machine,
            no_answer=disposition_dict.get(CallDisposition.NO_ANSWER, 0),
            busy=disposition_dict.get(CallDisposition.BUSY, 0),
            failed=disposition_dict.get(CallDisposition.FAILED, 0),
            invalid_number=disposition_dict.get(CallDisposition.INVALID_NUMBER, 0),
            answer_rate=round(answer_rate, 2),
            completion_rate=round(completion_rate, 2),
            human_rate=round(human_rate, 2),
            average_call_duration=None,  # Would need call logs
            total_talk_time=0,  # Would need call logs
            started_at=campaign.started_at,
            completed_at=campaign.completed_at,
            last_call_at=None,  # Would need call logs
        )


# Global service instance
campaign_service = CampaignService()
