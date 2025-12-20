"""
Campaign-related Celery tasks.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session

from workers.celery_app import app
from app.db.session import get_sync_session
from app.models.campaign import Campaign, CampaignContact, CampaignStatus, ContactStatus

logger = logging.getLogger(__name__)


@app.task(bind=True, name="workers.tasks.campaign_tasks.check_scheduled_campaigns")
def check_scheduled_campaigns(self):
    """
    Check for campaigns that should be started based on schedule.
    This task runs periodically (e.g., every minute) via Celery Beat.
    """
    started_count = 0
    now = datetime.utcnow()

    try:
        with get_sync_session() as session:
            # Find scheduled campaigns that should start
            result = session.execute(
                select(Campaign).where(
                    and_(
                        Campaign.status == CampaignStatus.SCHEDULED,
                        Campaign.scheduled_start <= now,
                        or_(
                            Campaign.scheduled_end.is_(None),
                            Campaign.scheduled_end > now
                        )
                    )
                )
            )
            campaigns = result.scalars().all()

            for campaign in campaigns:
                try:
                    campaign.status = CampaignStatus.RUNNING
                    campaign.started_at = now
                    started_count += 1
                    logger.info(f"Started scheduled campaign: {campaign.name} (ID: {campaign.id})")

                    # Populate contacts if not already done
                    existing_contacts = session.execute(
                        select(func.count()).where(CampaignContact.campaign_id == campaign.id)
                    ).scalar() or 0

                    if existing_contacts == 0:
                        # Trigger contact population
                        populate_campaign_contacts.delay(campaign.id)

                except Exception as e:
                    logger.error(f"Failed to start campaign {campaign.id}: {e}")

            session.commit()

    except Exception as e:
        logger.error(f"Error checking scheduled campaigns: {e}")

    return {"status": "checked", "campaigns_started": started_count}


@app.task(bind=True, name="workers.tasks.campaign_tasks.check_campaign_end_times")
def check_campaign_end_times(self):
    """
    Check for campaigns that have passed their scheduled end time and should be stopped.
    """
    stopped_count = 0
    now = datetime.utcnow()

    try:
        with get_sync_session() as session:
            # Find running campaigns that should end
            result = session.execute(
                select(Campaign).where(
                    and_(
                        Campaign.status == CampaignStatus.RUNNING,
                        Campaign.scheduled_end.isnot(None),
                        Campaign.scheduled_end <= now
                    )
                )
            )
            campaigns = result.scalars().all()

            for campaign in campaigns:
                try:
                    campaign.status = CampaignStatus.COMPLETED
                    campaign.completed_at = now
                    stopped_count += 1
                    logger.info(f"Ended scheduled campaign: {campaign.name} (ID: {campaign.id})")
                except Exception as e:
                    logger.error(f"Failed to end campaign {campaign.id}: {e}")

            session.commit()

    except Exception as e:
        logger.error(f"Error checking campaign end times: {e}")

    return {"status": "checked", "campaigns_stopped": stopped_count}


@app.task(bind=True, name="workers.tasks.campaign_tasks.cleanup_stale_calls")
def cleanup_stale_calls(self):
    """
    Clean up stale call records - contacts stuck in IN_PROGRESS state.
    This can happen if the dialer crashes while calls are active.
    """
    cleaned_count = 0
    stale_threshold = datetime.utcnow() - timedelta(hours=1)

    try:
        with get_sync_session() as session:
            # Find contacts stuck in IN_PROGRESS for too long
            result = session.execute(
                select(CampaignContact).where(
                    and_(
                        CampaignContact.status == ContactStatus.IN_PROGRESS,
                        CampaignContact.last_attempt_at < stale_threshold
                    )
                )
            )
            stale_contacts = result.scalars().all()

            for contact in stale_contacts:
                try:
                    # Reset to PENDING for retry
                    contact.status = ContactStatus.PENDING
                    contact.next_attempt_at = datetime.utcnow()
                    cleaned_count += 1
                except Exception as e:
                    logger.error(f"Failed to clean stale contact {contact.id}: {e}")

            session.commit()
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} stale call records")

    except Exception as e:
        logger.error(f"Error cleaning stale calls: {e}")

    return {"status": "cleaned", "calls_cleaned": cleaned_count}


@app.task(bind=True, name="workers.tasks.campaign_tasks.populate_campaign_contacts")
def populate_campaign_contacts(self, campaign_id: str):
    """
    Populate campaign_contacts from the contact list.
    This is called when a campaign starts to copy contacts for tracking.
    """
    contacts_added = 0

    try:
        with get_sync_session() as session:
            from app.models.contact import Contact, DNCEntry

            # Get campaign
            campaign = session.execute(
                select(Campaign).where(Campaign.id == campaign_id)
            ).scalar_one_or_none()

            if not campaign:
                logger.error(f"Campaign not found: {campaign_id}")
                return {"status": "error", "error": "Campaign not found"}

            # Check if already populated
            existing = session.execute(
                select(func.count()).where(CampaignContact.campaign_id == campaign_id)
            ).scalar() or 0

            if existing > 0:
                logger.info(f"Campaign {campaign_id} already has {existing} contacts")
                return {"status": "already_populated", "contacts": existing}

            # Get valid contacts from the contact list
            contacts = session.execute(
                select(Contact).where(
                    and_(
                        Contact.contact_list_id == campaign.contact_list_id,
                        Contact.is_valid == True
                    )
                )
            ).scalars().all()

            # Get DNC numbers
            dnc_result = session.execute(
                select(DNCEntry.phone_number).where(
                    or_(
                        DNCEntry.organization_id == campaign.organization_id,
                        DNCEntry.organization_id.is_(None)
                    )
                )
            )
            dnc_numbers = set(row[0] for row in dnc_result.all())

            # Create campaign contacts
            for contact in contacts:
                phone = contact.phone_number_e164 or contact.phone_number
                status = ContactStatus.DNC if phone in dnc_numbers else ContactStatus.PENDING

                cc = CampaignContact(
                    campaign_id=campaign_id,
                    contact_id=contact.id,
                    status=status
                )
                session.add(cc)
                contacts_added += 1

            # Update campaign stats
            campaign.total_contacts = contacts_added

            session.commit()
            logger.info(f"Populated campaign {campaign_id} with {contacts_added} contacts")

    except Exception as e:
        logger.error(f"Error populating campaign contacts: {e}")
        return {"status": "error", "error": str(e)}

    return {"status": "populated", "campaign_id": campaign_id, "contacts_added": contacts_added}


@app.task(bind=True, name="workers.tasks.campaign_tasks.update_campaign_stats")
def update_campaign_stats(self, campaign_id: str):
    """
    Recalculate and update campaign statistics.
    """
    try:
        with get_sync_session() as session:
            campaign = session.execute(
                select(Campaign).where(Campaign.id == campaign_id)
            ).scalar_one_or_none()

            if not campaign:
                return {"status": "error", "error": "Campaign not found"}

            # Count contacts by status
            status_counts = {}
            for status in ContactStatus:
                count = session.execute(
                    select(func.count()).where(
                        and_(
                            CampaignContact.campaign_id == campaign_id,
                            CampaignContact.status == status
                        )
                    )
                ).scalar() or 0
                status_counts[status.value] = count

            # Update campaign stats
            campaign.total_contacts = sum(status_counts.values())
            campaign.contacts_completed = (
                status_counts.get(ContactStatus.COMPLETED.value, 0) +
                status_counts.get(ContactStatus.FAILED.value, 0) +
                status_counts.get(ContactStatus.DNC.value, 0) +
                status_counts.get(ContactStatus.SKIPPED.value, 0)
            )

            session.commit()

            return {
                "status": "updated",
                "campaign_id": campaign_id,
                "stats": status_counts
            }

    except Exception as e:
        logger.error(f"Error updating campaign stats: {e}")
        return {"status": "error", "error": str(e)}


@app.task(bind=True, name="workers.tasks.campaign_tasks.generate_campaign_report")
def generate_campaign_report(self, campaign_id: str):
    """Generate a report for a completed campaign."""
    try:
        with get_sync_session() as session:
            from app.models.campaign import CallDisposition

            campaign = session.execute(
                select(Campaign).where(Campaign.id == campaign_id)
            ).scalar_one_or_none()

            if not campaign:
                return {"status": "error", "error": "Campaign not found"}

            # Get status counts
            status_counts = {}
            for status in ContactStatus:
                count = session.execute(
                    select(func.count()).where(
                        and_(
                            CampaignContact.campaign_id == campaign_id,
                            CampaignContact.status == status
                        )
                    )
                ).scalar() or 0
                status_counts[status.value] = count

            # Get disposition counts
            disposition_counts = {}
            for disposition in CallDisposition:
                count = session.execute(
                    select(func.count()).where(
                        and_(
                            CampaignContact.campaign_id == campaign_id,
                            CampaignContact.last_disposition == disposition
                        )
                    )
                ).scalar() or 0
                disposition_counts[disposition.value] = count

            # Calculate metrics
            total_contacts = campaign.total_contacts or sum(status_counts.values())
            total_answered = (
                disposition_counts.get(CallDisposition.ANSWERED_HUMAN.value, 0) +
                disposition_counts.get(CallDisposition.ANSWERED_MACHINE.value, 0)
            )
            answer_rate = (total_answered / campaign.contacts_called * 100) if campaign.contacts_called > 0 else 0

            report = {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "status": campaign.status.value,
                "started_at": campaign.started_at.isoformat() if campaign.started_at else None,
                "completed_at": campaign.completed_at.isoformat() if campaign.completed_at else None,
                "total_contacts": total_contacts,
                "contacts_called": campaign.contacts_called,
                "contacts_answered": campaign.contacts_answered,
                "answer_rate": round(answer_rate, 2),
                "status_breakdown": status_counts,
                "disposition_breakdown": disposition_counts
            }

            logger.info(f"Generated report for campaign {campaign_id}")
            return {"status": "generated", "campaign_id": campaign_id, "report": report}

    except Exception as e:
        logger.error(f"Error generating campaign report: {e}")
        return {"status": "error", "error": str(e)}
