"""
SIP Engine Package for Grandstream UCM PJSIP Integration.

This package provides a complete SIP User Agent implementation using PJSUA2
(Python bindings for PJSIP) that registers with Grandstream UCM6302 as an
extension and handles outbound calling with full RTP media support.

Components:
- SIPEngine: Main engine class for managing SIP registration and calls
- SIPAccount: PJSUA2 Account class for UCM registration
- SIPCall: PJSUA2 Call class with media handling
- MediaHandler: RTP audio playback and DTMF detection
"""

from .pjsua_client import SIPEngine, SIPAccount, SIPCall
from .media_handler import MediaHandler

__all__ = [
    'SIPEngine',
    'SIPAccount',
    'SIPCall',
    'MediaHandler',
]
