"""
Voice Agent plugins for external API integration.
"""
from dialer.voice_agent.plugins.base import ExternalPlugin, PluginParameter
from dialer.voice_agent.plugins.customer_lookup import (
    CustomerLookupPlugin,
    MockCustomerLookupPlugin
)
from dialer.voice_agent.plugins.transfer_call import (
    TransferCallPlugin,
    HangupCallPlugin,
    EscalatePlugin
)

__all__ = [
    "ExternalPlugin",
    "PluginParameter",
    "CustomerLookupPlugin",
    "MockCustomerLookupPlugin",
    "TransferCallPlugin",
    "HangupCallPlugin",
    "EscalatePlugin",
]
