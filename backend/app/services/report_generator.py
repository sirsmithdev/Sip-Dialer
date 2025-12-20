"""
Report Generator service for creating email report content.
Generates HTML content from templates for email reports.
"""
import os
import logging
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Optional, Dict, Any, List
from string import Template

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignStatus, CampaignContact, CallDisposition
from app.models.call_log import CallLog, CallResult
from app.models.user import Organization


logger = logging.getLogger(__name__)

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "emails"


class ReportGenerator:
    """
    Service for generating email report content.

    Generates HTML and plain text content for:
    - Campaign reports
    - Daily summaries
    - Campaign completion notifications
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.templates_dir = TEMPLATES_DIR

    def _load_template(self, template_name: str) -> str:
        """Load template file content."""
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            logger.error(f"Template not found: {template_path}")
            return ""
        return template_path.read_text(encoding="utf-8")

    def _load_base_template(self) -> str:
        """Load the base email template."""
        return self._load_template("base.html")

    def _render_template(self, template_content: str, context: Dict[str, Any]) -> str:
        """
        Simple template rendering with Jinja2-like syntax support.

        Supports:
        - {{ variable }} - Variable substitution
        - {% for item in items %} ... {% endfor %} - Basic loops
        - {% if condition %} ... {% endif %} - Basic conditionals
        """
        # For simplicity, use Python's string.Template for variables
        # and implement basic loop/conditional support
        result = template_content

        # Handle simple variable substitution first
        for key, value in context.items():
            if not isinstance(value, (list, dict)):
                result = result.replace("{{ " + key + " }}", str(value))
                result = result.replace("{{" + key + "}}", str(value))

        # Handle for loops for lists
        import re

        # Simple for loop pattern: {% for item in items %}...{% endfor %}
        for_pattern = r"\{% for (\w+) in (\w+) %\}(.*?)\{% endfor %\}"
        matches = re.findall(for_pattern, result, re.DOTALL)

        for match in matches:
            item_name, list_name, loop_content = match
            items = context.get(list_name, [])
            rendered_items = []

            for item in items:
                item_content = loop_content
                if isinstance(item, dict):
                    for k, v in item.items():
                        item_content = item_content.replace(
                            "{{ " + f"{item_name}.{k}" + " }}", str(v)
                        )
                        item_content = item_content.replace(
                            "{{" + f"{item_name}.{k}" + "}}", str(v)
                        )
                rendered_items.append(item_content)

            full_pattern = r"\{% for " + item_name + r" in " + list_name + r" %\}.*?\{% endfor %\}"
            result = re.sub(full_pattern, "".join(rendered_items), result, flags=re.DOTALL)

        # Handle if statements
        if_pattern = r"\{% if (\w+) %\}(.*?)\{% endif %\}"
        matches = re.findall(if_pattern, result, re.DOTALL)

        for match in matches:
            condition_name, if_content = match
            condition_value = context.get(condition_name)

            if condition_value:
                # Keep content
                full_pattern = r"\{% if " + condition_name + r" %\}(.*?)\{% endif %\}"
                result = re.sub(full_pattern, if_content, result, flags=re.DOTALL)
            else:
                # Remove content
                full_pattern = r"\{% if " + condition_name + r" %\}.*?\{% endif %\}"
                result = re.sub(full_pattern, "", result, flags=re.DOTALL)

        return result

    def _wrap_in_base(self, content: str, title: str) -> str:
        """Wrap content in the base template."""
        base_template = self._load_base_template()
        return base_template.replace("{{ title }}", title).replace("{{ content }}", content)

    def _format_duration(self, seconds: Optional[int]) -> str:
        """Format duration in seconds to human-readable string."""
        if seconds is None or seconds == 0:
            return "0s"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)

    def _format_datetime(self, dt: Optional[datetime]) -> str:
        """Format datetime for display."""
        if dt is None:
            return "N/A"
        return dt.strftime("%b %d, %Y %I:%M %p")

    def _get_status_class(self, status: CampaignStatus) -> str:
        """Get CSS class for campaign status."""
        status_classes = {
            CampaignStatus.DRAFT: "paused",
            CampaignStatus.SCHEDULED: "paused",
            CampaignStatus.RUNNING: "running",
            CampaignStatus.PAUSED: "paused",
            CampaignStatus.COMPLETED: "completed",
            CampaignStatus.CANCELLED: "failed",
        }
        return status_classes.get(status, "paused")

    async def _get_campaign_stats(self, campaign_id: str) -> Dict[str, Any]:
        """Get campaign statistics from call logs."""
        # Total calls
        total_result = await self.db.execute(
            select(func.count(CallLog.id)).where(CallLog.campaign_id == campaign_id)
        )
        total_calls = total_result.scalar() or 0

        # Answered calls
        answered_result = await self.db.execute(
            select(func.count(CallLog.id)).where(
                CallLog.campaign_id == campaign_id,
                CallLog.result == CallResult.ANSWERED
            )
        )
        answered_calls = answered_result.scalar() or 0

        # Total talk duration
        duration_result = await self.db.execute(
            select(func.sum(CallLog.talk_duration_seconds)).where(
                CallLog.campaign_id == campaign_id,
                CallLog.talk_duration_seconds.isnot(None)
            )
        )
        total_duration = duration_result.scalar() or 0

        # Average duration
        avg_duration_result = await self.db.execute(
            select(func.avg(CallLog.talk_duration_seconds)).where(
                CallLog.campaign_id == campaign_id,
                CallLog.talk_duration_seconds.isnot(None),
                CallLog.talk_duration_seconds > 0
            )
        )
        avg_duration = avg_duration_result.scalar() or 0

        # Disposition breakdown
        disposition_result = await self.db.execute(
            select(
                CallLog.result,
                func.count(CallLog.id).label("count")
            ).where(
                CallLog.campaign_id == campaign_id
            ).group_by(CallLog.result)
        )
        dispositions = []
        for row in disposition_result:
            percentage = round((row.count / total_calls * 100), 1) if total_calls > 0 else 0
            dispositions.append({
                "name": row.result.value.replace("_", " ").title() if row.result else "Unknown",
                "count": row.count,
                "percentage": percentage
            })

        return {
            "total_calls": total_calls,
            "answered_calls": answered_calls,
            "answer_rate": round((answered_calls / total_calls * 100), 1) if total_calls > 0 else 0,
            "total_duration": total_duration,
            "avg_duration": int(avg_duration) if avg_duration else 0,
            "dispositions": dispositions,
        }

    async def generate_campaign_report(self, campaign_id: str) -> Optional[Dict[str, str]]:
        """
        Generate a campaign report email.

        Returns dict with 'subject', 'html', and 'text' keys.
        """
        # Get campaign
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()

        if not campaign:
            logger.error(f"Campaign not found: {campaign_id}")
            return None

        # Get stats
        stats = await self._get_campaign_stats(campaign_id)

        # Build context
        context = {
            "campaign_name": campaign.name,
            "status": campaign.status.value.title(),
            "status_class": self._get_status_class(campaign.status),
            "total_calls": stats["total_calls"],
            "answered_calls": stats["answered_calls"],
            "answer_rate": stats["answer_rate"],
            "avg_duration": self._format_duration(stats["avg_duration"]),
            "start_date": self._format_datetime(campaign.started_at or campaign.created_at),
            "end_date": self._format_datetime(campaign.completed_at) if campaign.completed_at else "Ongoing",
            "contact_list_name": campaign.contact_list.name if campaign.contact_list else "N/A",
            "total_contacts": campaign.total_contacts,
            "progress": round((campaign.contacts_completed / campaign.total_contacts * 100), 1) if campaign.total_contacts > 0 else 0,
            "dispositions": stats["dispositions"],
            "notes": campaign.description or "",
            "generated_at": datetime.now(timezone.utc).strftime("%b %d, %Y at %I:%M %p UTC"),
            "dashboard_url": "#",  # Placeholder - should be configurable
        }

        # Load and render template
        template_content = self._load_template("campaign_report.html")
        body_content = self._render_template(template_content, context)
        html = self._wrap_in_base(body_content, f"Campaign Report: {campaign.name}")

        # Plain text version
        text = f"""
Campaign Report: {campaign.name}
Status: {context['status']}

Summary:
- Total Calls: {stats['total_calls']}
- Answered: {stats['answered_calls']}
- Answer Rate: {stats['answer_rate']}%
- Average Duration: {context['avg_duration']}

Campaign ran from {context['start_date']} to {context['end_date']}.

---
Generated on {context['generated_at']}
SIP Auto-Dialer
        """.strip()

        return {
            "subject": f"Campaign Report: {campaign.name}",
            "html": html,
            "text": text,
        }

    async def generate_campaign_completed_email(self, campaign_id: str) -> Optional[Dict[str, str]]:
        """
        Generate a campaign completed notification email.

        Returns dict with 'subject', 'html', and 'text' keys.
        """
        # Get campaign
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()

        if not campaign:
            logger.error(f"Campaign not found: {campaign_id}")
            return None

        # Get stats
        stats = await self._get_campaign_stats(campaign_id)

        # Calculate campaign duration
        if campaign.started_at and campaign.completed_at:
            duration_delta = campaign.completed_at - campaign.started_at
            campaign_duration = self._format_duration(int(duration_delta.total_seconds()))
        else:
            campaign_duration = "N/A"

        # Build context
        context = {
            "campaign_name": campaign.name,
            "total_calls": stats["total_calls"],
            "answered_calls": stats["answered_calls"],
            "answer_rate": stats["answer_rate"],
            "total_duration": self._format_duration(stats["total_duration"]),
            "start_date": self._format_datetime(campaign.started_at),
            "end_date": self._format_datetime(campaign.completed_at),
            "campaign_duration": campaign_duration,
            "dispositions": stats["dispositions"],
            "completed_at": self._format_datetime(campaign.completed_at),
            "report_url": "#",  # Placeholder
            "dashboard_url": "#",  # Placeholder
        }

        # Load and render template
        template_content = self._load_template("campaign_completed.html")
        body_content = self._render_template(template_content, context)
        html = self._wrap_in_base(body_content, f"Campaign Completed: {campaign.name}")

        # Plain text version
        text = f"""
Campaign Completed: {campaign.name}

Your campaign has completed successfully!

Results:
- Total Calls: {stats['total_calls']}
- Answered: {stats['answered_calls']}
- Answer Rate: {stats['answer_rate']}%
- Total Talk Time: {context['total_duration']}

Timeline:
- Started: {context['start_date']}
- Completed: {context['end_date']}
- Duration: {campaign_duration}

---
SIP Auto-Dialer
        """.strip()

        return {
            "subject": f"Campaign Completed: {campaign.name}",
            "html": html,
            "text": text,
        }

    async def generate_daily_summary(
        self,
        organization_id: str,
        for_date: Optional[date] = None
    ) -> Optional[Dict[str, str]]:
        """
        Generate a daily summary email for an organization.

        Returns dict with 'subject', 'html', and 'text' keys.
        """
        # Default to yesterday if no date specified
        if for_date is None:
            for_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

        # Get organization
        result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        organization = result.scalar_one_or_none()

        if not organization:
            logger.error(f"Organization not found: {organization_id}")
            return None

        # Date range for the day
        start_of_day = datetime.combine(for_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_of_day = datetime.combine(for_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Get campaigns that were active during this day
        campaigns_result = await self.db.execute(
            select(Campaign).where(
                Campaign.organization_id == organization_id,
                Campaign.status.in_([
                    CampaignStatus.RUNNING,
                    CampaignStatus.COMPLETED,
                    CampaignStatus.PAUSED
                ])
            )
        )
        campaigns = list(campaigns_result.scalars().all())

        # Get call stats for the day
        total_calls_result = await self.db.execute(
            select(func.count(CallLog.id)).where(
                CallLog.initiated_at >= start_of_day,
                CallLog.initiated_at <= end_of_day,
                CallLog.campaign_id.in_([c.id for c in campaigns]) if campaigns else False
            )
        )
        total_calls = total_calls_result.scalar() or 0

        answered_calls_result = await self.db.execute(
            select(func.count(CallLog.id)).where(
                CallLog.initiated_at >= start_of_day,
                CallLog.initiated_at <= end_of_day,
                CallLog.result == CallResult.ANSWERED,
                CallLog.campaign_id.in_([c.id for c in campaigns]) if campaigns else False
            )
        )
        answered_calls = answered_calls_result.scalar() or 0

        duration_result = await self.db.execute(
            select(func.sum(CallLog.talk_duration_seconds)).where(
                CallLog.initiated_at >= start_of_day,
                CallLog.initiated_at <= end_of_day,
                CallLog.talk_duration_seconds.isnot(None),
                CallLog.campaign_id.in_([c.id for c in campaigns]) if campaigns else False
            )
        )
        total_duration = duration_result.scalar() or 0

        # Build campaign data
        campaigns_data = []
        completed_campaigns = []
        active_count = 0

        for campaign in campaigns:
            # Get campaign calls for this day
            camp_calls_result = await self.db.execute(
                select(func.count(CallLog.id)).where(
                    CallLog.campaign_id == campaign.id,
                    CallLog.initiated_at >= start_of_day,
                    CallLog.initiated_at <= end_of_day
                )
            )
            camp_calls = camp_calls_result.scalar() or 0

            camp_answered_result = await self.db.execute(
                select(func.count(CallLog.id)).where(
                    CallLog.campaign_id == campaign.id,
                    CallLog.initiated_at >= start_of_day,
                    CallLog.initiated_at <= end_of_day,
                    CallLog.result == CallResult.ANSWERED
                )
            )
            camp_answered = camp_answered_result.scalar() or 0

            rate = round((camp_answered / camp_calls * 100), 1) if camp_calls > 0 else 0

            campaigns_data.append({
                "name": campaign.name,
                "status": campaign.status.value.title(),
                "status_class": self._get_status_class(campaign.status),
                "calls": camp_calls,
                "answered": camp_answered,
                "rate": rate,
            })

            if campaign.status == CampaignStatus.RUNNING:
                active_count += 1

            if campaign.status == CampaignStatus.COMPLETED and campaign.completed_at:
                if campaign.completed_at.date() == for_date:
                    completed_campaigns.append({
                        "name": campaign.name,
                        "total_calls": campaign.contacts_called,
                        "answer_rate": round(
                            (campaign.contacts_answered / campaign.contacts_called * 100), 1
                        ) if campaign.contacts_called > 0 else 0,
                    })

        # Determine greeting based on time
        hour = datetime.now(timezone.utc).hour
        if hour < 12:
            greeting = "morning"
        elif hour < 17:
            greeting = "afternoon"
        else:
            greeting = "evening"

        # Build context
        context = {
            "date": for_date.strftime("%B %d, %Y"),
            "greeting": greeting,
            "organization_name": organization.name,
            "total_calls": total_calls,
            "answered_calls": answered_calls,
            "active_campaigns": active_count,
            "total_duration": self._format_duration(total_duration),
            "campaigns": campaigns_data,
            "completed_campaigns": completed_campaigns,
            "alerts": [],  # Placeholder for alerts
            "generated_at": datetime.now(timezone.utc).strftime("%b %d, %Y at %I:%M %p UTC"),
            "dashboard_url": "#",  # Placeholder
        }

        # Load and render template
        template_content = self._load_template("daily_summary.html")
        body_content = self._render_template(template_content, context)
        html = self._wrap_in_base(body_content, f"Daily Summary - {context['date']}")

        # Plain text version
        campaigns_text = "\n".join([
            f"  - {c['name']}: {c['calls']} calls, {c['rate']}% answered"
            for c in campaigns_data
        ]) or "  No campaign activity"

        text = f"""
Daily Summary - {context['date']}

Good {greeting}, {organization.name}!

Overview:
- Total Calls: {total_calls}
- Answered: {answered_calls}
- Active Campaigns: {active_count}
- Total Talk Time: {context['total_duration']}

Campaign Activity:
{campaigns_text}

---
Generated on {context['generated_at']}
SIP Auto-Dialer
        """.strip()

        return {
            "subject": f"Daily Summary - {context['date']}",
            "html": html,
            "text": text,
        }
