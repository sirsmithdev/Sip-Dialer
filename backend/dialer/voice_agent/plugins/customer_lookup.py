"""
Customer lookup plugin - fetches customer data from external API.
"""
from typing import Dict, Any, Optional
import httpx
import logging

from dialer.voice_agent.plugins.base import ExternalPlugin, PluginParameter

logger = logging.getLogger(__name__)


class CustomerLookupPlugin(ExternalPlugin):
    """
    Look up customer information by phone number.

    This plugin calls an external CRM or customer database API
    to fetch customer information like name, account status, etc.
    """

    name = "lookup_customer"
    description = "Look up customer information including name, account status, and recent activity by their phone number"
    parameters = [
        PluginParameter(
            name="phone_number",
            type="string",
            description="Customer phone number in E.164 format (e.g., +15551234567)",
            required=True
        )
    ]

    def __init__(
        self,
        api_endpoint: str,
        api_key: Optional[str] = None,
        timeout: float = 10.0
    ):
        """
        Initialize customer lookup plugin.

        Args:
            api_endpoint: Base URL for customer API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.api_endpoint = api_endpoint.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout

    async def execute(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fetch customer data from API.

        Args:
            params: {"phone_number": "+15551234567"}
            context: Conversation context

        Returns:
            Customer data or error message
        """
        phone_number = params.get("phone_number", "")

        # Validate phone number
        if not phone_number:
            return {"error": "Phone number is required"}

        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.api_endpoint}/customers",
                    params={"phone": phone_number},
                    headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "found": True,
                        "customer": data
                    }
                elif response.status_code == 404:
                    return {
                        "found": False,
                        "message": "Customer not found"
                    }
                else:
                    logger.error(f"Customer API error: {response.status_code}")
                    return {
                        "error": "Unable to fetch customer information"
                    }

        except httpx.TimeoutException:
            logger.error("Customer API timeout")
            return {"error": "Customer lookup timed out"}
        except Exception as e:
            logger.error(f"Customer lookup error: {e}")
            return {"error": "Customer lookup failed"}


class MockCustomerLookupPlugin(ExternalPlugin):
    """
    Mock customer lookup for testing.
    Returns fake customer data based on phone number.
    """

    name = "lookup_customer"
    description = "Look up customer information including name, account status, and recent activity"
    parameters = [
        PluginParameter(
            name="phone_number",
            type="string",
            description="Customer phone number",
            required=True
        )
    ]

    # Mock customer database
    MOCK_CUSTOMERS = {
        "+15551234567": {
            "name": "John Smith",
            "account_number": "ACC-12345",
            "status": "active",
            "balance": 150.00,
            "last_order": "2024-12-20",
            "membership_tier": "gold"
        },
        "+15559876543": {
            "name": "Jane Doe",
            "account_number": "ACC-67890",
            "status": "active",
            "balance": 0.00,
            "last_order": "2024-12-15",
            "membership_tier": "silver"
        }
    }

    async def execute(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return mock customer data."""
        phone = params.get("phone_number", "")

        # Check context for caller number if not provided
        if not phone and context.get("caller_number"):
            phone = context["caller_number"]

        # Look up in mock database
        if phone in self.MOCK_CUSTOMERS:
            return {
                "found": True,
                "customer": self.MOCK_CUSTOMERS[phone]
            }

        # Generate generic response for unknown numbers
        return {
            "found": True,
            "customer": {
                "name": "Valued Customer",
                "account_number": "GUEST",
                "status": "active",
                "balance": 0.00,
                "membership_tier": "standard"
            }
        }
