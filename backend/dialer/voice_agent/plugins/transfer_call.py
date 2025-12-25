"""
Call transfer plugin - transfers calls to human agents.
"""
from typing import Dict, Any, Optional, List
import logging

from dialer.voice_agent.plugins.base import ExternalPlugin, PluginParameter

logger = logging.getLogger(__name__)


class TransferCallPlugin(ExternalPlugin):
    """
    Transfer the current call to a human agent or department.

    Returns a special action that signals the voice agent session
    to initiate a call transfer.
    """

    name = "transfer_call"
    description = "Transfer the current call to a specific department or human agent when the AI cannot help or the customer requests it"
    parameters = [
        PluginParameter(
            name="department",
            type="string",
            description="Department to transfer to",
            required=True,
            enum=["sales", "support", "billing", "general"]
        ),
        PluginParameter(
            name="reason",
            type="string",
            description="Brief reason for the transfer to help the agent",
            required=False
        ),
        PluginParameter(
            name="priority",
            type="string",
            description="Transfer priority level",
            required=False,
            enum=["normal", "urgent"]
        )
    ]

    def __init__(
        self,
        department_extensions: Optional[Dict[str, str]] = None
    ):
        """
        Initialize transfer plugin.

        Args:
            department_extensions: Mapping of department names to extensions
        """
        self.department_extensions = department_extensions or {
            "sales": "2001",
            "support": "2002",
            "billing": "2003",
            "general": "2000"
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Signal a call transfer.

        Args:
            params: Transfer parameters
            context: Conversation context

        Returns:
            Transfer action for the voice agent session
        """
        department = params.get("department", "general")
        reason = params.get("reason", "Customer request")
        priority = params.get("priority", "normal")

        # Get extension for department
        extension = self.department_extensions.get(
            department,
            self.department_extensions.get("general", "2000")
        )

        logger.info(
            f"Transfer requested: {department} (ext: {extension}), "
            f"reason: {reason}, priority: {priority}"
        )

        return {
            "action": "transfer",
            "department": department,
            "extension": extension,
            "reason": reason,
            "priority": priority,
            "message": f"Transferring to {department} department"
        }


class HangupCallPlugin(ExternalPlugin):
    """
    End the current call gracefully.

    Used when the conversation is complete or the customer
    requests to end the call.
    """

    name = "end_call"
    description = "End the call gracefully when the conversation is complete or customer requests to hang up"
    parameters = [
        PluginParameter(
            name="reason",
            type="string",
            description="Reason for ending the call",
            required=False,
            enum=["completed", "customer_request", "no_further_assistance"]
        )
    ]

    async def execute(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Signal to end the call.

        Returns:
            Hangup action for the voice agent session
        """
        reason = params.get("reason", "completed")

        logger.info(f"Hangup requested: {reason}")

        return {
            "action": "hangup",
            "reason": reason,
            "message": "Thank you for calling. Goodbye!"
        }


class EscalatePlugin(ExternalPlugin):
    """
    Escalate the call to a supervisor or specialized team.
    """

    name = "escalate_call"
    description = "Escalate the call to a supervisor when the situation requires immediate attention or special handling"
    parameters = [
        PluginParameter(
            name="issue_type",
            type="string",
            description="Type of issue requiring escalation",
            required=True,
            enum=["complaint", "technical", "billing_dispute", "urgent", "other"]
        ),
        PluginParameter(
            name="summary",
            type="string",
            description="Brief summary of the issue for the supervisor",
            required=True
        )
    ]

    def __init__(self, supervisor_extension: str = "3000"):
        """Initialize with supervisor extension."""
        self.supervisor_extension = supervisor_extension

    async def execute(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Signal escalation to supervisor."""
        issue_type = params.get("issue_type", "other")
        summary = params.get("summary", "")

        logger.info(f"Escalation requested: {issue_type} - {summary}")

        return {
            "action": "transfer",
            "department": "supervisor",
            "extension": self.supervisor_extension,
            "reason": f"Escalation ({issue_type}): {summary}",
            "priority": "urgent",
            "is_escalation": True,
            "message": "I'm connecting you with a supervisor who can better assist you."
        }
