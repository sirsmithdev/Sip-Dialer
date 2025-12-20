"""
Email-related Celery tasks for sending reports and notifications.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from workers.celery_app import app

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _get_db_session():
    """Get async database session."""
    from app.db.session import async_session_maker
    async with async_session_maker() as session:
        yield session


@app.task(bind=True, name="workers.tasks.email_tasks.send_email")
def send_email_task(
    self,
    organization_id: str,
    to_emails: List[str],
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
    email_type: str = "system_alert",
    campaign_id: Optional[str] = None,
):
    """
    Send an email asynchronously via Celery.

    Args:
        organization_id: Organization ID
        to_emails: List of recipient email addresses
        subject: Email subject
        body_html: HTML email body
        body_text: Plain text email body (optional)
        email_type: Type of email (campaign_report, daily_summary, etc.)
        campaign_id: Related campaign ID (optional)
    """
    async def _send():
        from app.db.session import async_session_maker
        from app.services.email_service import EmailService
        from app.models.email_log import EmailType

        async with async_session_maker() as session:
            email_service = EmailService(session)

            # Convert email_type string to enum
            try:
                email_type_enum = EmailType(email_type)
            except ValueError:
                email_type_enum = EmailType.SYSTEM_ALERT

            results = await email_service.send_email(
                organization_id=organization_id,
                to_emails=to_emails,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                email_type=email_type_enum,
                campaign_id=campaign_id,
            )

            return [
                {
                    "success": r.success,
                    "message_id": r.message_id,
                    "error": r.error,
                    "log_id": r.log_id,
                }
                for r in results
            ]

    try:
        results = run_async(_send())
        success_count = sum(1 for r in results if r["success"])
        logger.info(
            f"Email task completed: {success_count}/{len(results)} sent successfully"
        )
        return {
            "status": "completed",
            "results": results,
            "success_count": success_count,
            "total_count": len(results),
        }
    except Exception as e:
        logger.error(f"Email task failed: {str(e)}")
        return {"status": "failed", "error": str(e)}


@app.task(bind=True, name="workers.tasks.email_tasks.send_campaign_report")
def send_campaign_report_task(
    self,
    campaign_id: str,
    organization_id: str,
    recipient_emails: List[str],
):
    """
    Generate and send a campaign report email.

    Args:
        campaign_id: Campaign ID to generate report for
        organization_id: Organization ID
        recipient_emails: List of recipient email addresses
    """
    async def _send_report():
        from app.db.session import async_session_maker
        from app.services.email_service import EmailService
        from app.services.report_generator import ReportGenerator
        from app.models.email_log import EmailType

        async with async_session_maker() as session:
            # Generate report
            report_generator = ReportGenerator(session)
            report_data = await report_generator.generate_campaign_report(campaign_id)

            if not report_data:
                return {"success": False, "error": "Failed to generate report"}

            # Send email with report
            email_service = EmailService(session)
            results = await email_service.send_email(
                organization_id=organization_id,
                to_emails=recipient_emails,
                subject=report_data["subject"],
                body_html=report_data["html"],
                body_text=report_data.get("text"),
                email_type=EmailType.CAMPAIGN_REPORT,
                campaign_id=campaign_id,
            )

            return [
                {
                    "success": r.success,
                    "message_id": r.message_id,
                    "error": r.error,
                    "log_id": r.log_id,
                }
                for r in results
            ]

    try:
        results = run_async(_send_report())
        if isinstance(results, dict) and not results.get("success", True):
            return {"status": "failed", "error": results.get("error")}

        success_count = sum(1 for r in results if r["success"])
        logger.info(
            f"Campaign report sent: {success_count}/{len(results)} emails delivered"
        )
        return {
            "status": "completed",
            "campaign_id": campaign_id,
            "results": results,
            "success_count": success_count,
        }
    except Exception as e:
        logger.error(f"Campaign report task failed: {str(e)}")
        return {"status": "failed", "error": str(e)}


@app.task(bind=True, name="workers.tasks.email_tasks.send_campaign_completed_notification")
def send_campaign_completed_notification(
    self,
    campaign_id: str,
    organization_id: str,
):
    """
    Send notification when a campaign completes.

    Args:
        campaign_id: Completed campaign ID
        organization_id: Organization ID
    """
    async def _send_notification():
        from app.db.session import async_session_maker
        from app.services.email_service import EmailService
        from app.services.report_generator import ReportGenerator
        from app.models.email_log import EmailType
        from app.models.campaign import Campaign
        from app.models.user import User, Organization
        from sqlalchemy import select

        async with async_session_maker() as session:
            # Get campaign details
            result = await session.execute(
                select(Campaign).where(Campaign.id == campaign_id)
            )
            campaign = result.scalar_one_or_none()
            if not campaign:
                return {"success": False, "error": "Campaign not found"}

            # Get organization admin/manager emails
            result = await session.execute(
                select(User).where(
                    User.organization_id == organization_id,
                    User.is_active == True,
                    User.role.in_(["admin", "manager"])
                )
            )
            users = result.scalars().all()
            recipient_emails = [u.email for u in users if u.email]

            if not recipient_emails:
                return {"success": False, "error": "No recipients found"}

            # Generate report
            report_generator = ReportGenerator(session)
            report_data = await report_generator.generate_campaign_completed_email(
                campaign_id
            )

            if not report_data:
                return {"success": False, "error": "Failed to generate notification"}

            # Send email
            email_service = EmailService(session)
            results = await email_service.send_email(
                organization_id=organization_id,
                to_emails=recipient_emails,
                subject=report_data["subject"],
                body_html=report_data["html"],
                body_text=report_data.get("text"),
                email_type=EmailType.CAMPAIGN_COMPLETED,
                campaign_id=campaign_id,
            )

            return [
                {
                    "success": r.success,
                    "message_id": r.message_id,
                    "error": r.error,
                }
                for r in results
            ]

    try:
        results = run_async(_send_notification())
        if isinstance(results, dict) and not results.get("success", True):
            return {"status": "failed", "error": results.get("error")}

        success_count = sum(1 for r in results if r["success"])
        logger.info(f"Campaign completed notification sent to {success_count} users")
        return {"status": "completed", "campaign_id": campaign_id}
    except Exception as e:
        logger.error(f"Campaign completed notification failed: {str(e)}")
        return {"status": "failed", "error": str(e)}


@app.task(bind=True, name="workers.tasks.email_tasks.send_daily_summary")
def send_daily_summary_task(self, organization_id: Optional[str] = None):
    """
    Send daily summary emails to all organizations (or a specific one).

    This task should be scheduled via Celery Beat to run daily.

    Args:
        organization_id: Optional specific organization ID
    """
    async def _send_summaries():
        from app.db.session import async_session_maker
        from app.services.email_service import EmailService
        from app.services.report_generator import ReportGenerator
        from app.models.email_log import EmailType
        from app.models.email_settings import EmailSettings
        from app.models.user import User, Organization
        from sqlalchemy import select

        async with async_session_maker() as session:
            # Get organizations with active email settings
            if organization_id:
                org_ids = [organization_id]
            else:
                result = await session.execute(
                    select(EmailSettings.organization_id).where(
                        EmailSettings.is_active == True
                    )
                )
                org_ids = [r[0] for r in result.all()]

            if not org_ids:
                return {"success": True, "message": "No organizations with active email"}

            summaries_sent = 0
            for org_id in org_ids:
                try:
                    # Get admin/manager emails for this org
                    result = await session.execute(
                        select(User).where(
                            User.organization_id == org_id,
                            User.is_active == True,
                            User.role.in_(["admin", "manager"])
                        )
                    )
                    users = result.scalars().all()
                    recipient_emails = [u.email for u in users if u.email]

                    if not recipient_emails:
                        continue

                    # Generate daily summary
                    report_generator = ReportGenerator(session)
                    report_data = await report_generator.generate_daily_summary(org_id)

                    if not report_data:
                        continue

                    # Send email
                    email_service = EmailService(session)
                    await email_service.send_email(
                        organization_id=org_id,
                        to_emails=recipient_emails,
                        subject=report_data["subject"],
                        body_html=report_data["html"],
                        body_text=report_data.get("text"),
                        email_type=EmailType.DAILY_SUMMARY,
                    )
                    summaries_sent += 1

                except Exception as e:
                    logger.error(f"Failed to send daily summary for org {org_id}: {e}")
                    continue

            return {"success": True, "summaries_sent": summaries_sent}

    try:
        result = run_async(_send_summaries())
        logger.info(f"Daily summary task completed: {result}")
        return {"status": "completed", **result}
    except Exception as e:
        logger.error(f"Daily summary task failed: {str(e)}")
        return {"status": "failed", "error": str(e)}


@app.task(bind=True, name="workers.tasks.email_tasks.process_scheduled_reports")
def process_scheduled_reports(self):
    """
    Check for scheduled reports that are due and send them.

    This task should be scheduled via Celery Beat to run hourly.
    """
    async def _process_reports():
        from app.db.session import async_session_maker
        from app.models.report import ReportSchedule
        from sqlalchemy import select

        async with async_session_maker() as session:
            # Get due report schedules
            now = datetime.now(timezone.utc)
            result = await session.execute(
                select(ReportSchedule).where(
                    ReportSchedule.is_active == True,
                    ReportSchedule.next_run_at <= now
                )
            )
            schedules = result.scalars().all()

            reports_processed = 0
            for schedule in schedules:
                try:
                    # Trigger the appropriate report task
                    if schedule.report_type == "campaign":
                        send_campaign_report_task.delay(
                            campaign_id=schedule.campaign_id,
                            organization_id=schedule.organization_id,
                            recipient_emails=schedule.email_recipients,
                        )
                    elif schedule.report_type == "daily_summary":
                        send_daily_summary_task.delay(
                            organization_id=schedule.organization_id
                        )

                    # Update next run time
                    schedule.last_run_at = now
                    schedule.next_run_at = _calculate_next_run(schedule)
                    reports_processed += 1

                except Exception as e:
                    logger.error(f"Failed to process schedule {schedule.id}: {e}")
                    continue

            await session.commit()
            return {"reports_processed": reports_processed}

    try:
        result = run_async(_process_reports())
        logger.info(f"Scheduled reports processed: {result}")
        return {"status": "completed", **result}
    except Exception as e:
        logger.error(f"Scheduled reports task failed: {str(e)}")
        return {"status": "failed", "error": str(e)}


def _calculate_next_run(schedule) -> datetime:
    """Calculate next run time based on schedule frequency."""
    now = datetime.now(timezone.utc)

    if schedule.frequency == "daily":
        return now + timedelta(days=1)
    elif schedule.frequency == "weekly":
        return now + timedelta(weeks=1)
    elif schedule.frequency == "monthly":
        # Approximate month as 30 days
        return now + timedelta(days=30)
    else:
        # Default to daily
        return now + timedelta(days=1)
