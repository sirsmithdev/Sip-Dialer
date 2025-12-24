"""
Concurrent Call Manager.

This module manages concurrent call limits and rate limiting for campaigns.
It handles the logic for determining how many calls can be initiated and
when, respecting both global and per-campaign limits.
"""
import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any

logger = logging.getLogger(__name__)


@dataclass
class CampaignCallState:
    """Tracks call state for a single campaign."""
    campaign_id: str
    max_concurrent_calls: int
    calls_per_minute: Optional[int] = None

    # Active calls for this campaign
    active_call_ids: Set[str] = field(default_factory=set)

    # Rate limiting - timestamps of recent calls
    call_timestamps: List[float] = field(default_factory=list)

    # Statistics
    total_calls_initiated: int = 0
    total_calls_completed: int = 0
    total_calls_failed: int = 0

    @property
    def active_call_count(self) -> int:
        """Get current number of active calls."""
        return len(self.active_call_ids)

    @property
    def available_slots(self) -> int:
        """Get number of available call slots."""
        return max(0, self.max_concurrent_calls - self.active_call_count)

    def can_make_call(self) -> bool:
        """Check if we can make another call for this campaign."""
        # Check concurrent limit
        if self.active_call_count >= self.max_concurrent_calls:
            return False

        # Check rate limit if configured
        if self.calls_per_minute:
            return self._check_rate_limit()

        return True

    def _check_rate_limit(self) -> bool:
        """Check if rate limit allows another call."""
        if not self.calls_per_minute:
            return True

        now = time.time()
        one_minute_ago = now - 60

        # Clean old timestamps
        self.call_timestamps = [ts for ts in self.call_timestamps if ts > one_minute_ago]

        # Check if under limit
        return len(self.call_timestamps) < self.calls_per_minute

    def record_call_start(self, call_id: str) -> None:
        """Record that a call has started."""
        self.active_call_ids.add(call_id)
        self.call_timestamps.append(time.time())
        self.total_calls_initiated += 1
        logger.debug(
            f"Campaign {self.campaign_id}: Call started {call_id}, "
            f"active={self.active_call_count}/{self.max_concurrent_calls}"
        )

    def record_call_end(self, call_id: str, success: bool = True) -> None:
        """Record that a call has ended."""
        self.active_call_ids.discard(call_id)
        if success:
            self.total_calls_completed += 1
        else:
            self.total_calls_failed += 1
        logger.debug(
            f"Campaign {self.campaign_id}: Call ended {call_id}, "
            f"active={self.active_call_count}/{self.max_concurrent_calls}"
        )


@dataclass
class PendingContact:
    """Represents a contact waiting to be called."""
    campaign_id: str
    campaign_contact_id: str
    contact_id: str
    phone_number: str
    caller_id: str
    ivr_flow_definition: Optional[Dict] = None
    priority: int = 100
    attempts: int = 0
    scheduled_at: Optional[datetime] = None


class ConcurrentCallManager:
    """
    Manages concurrent call limits across all campaigns.

    This class is responsible for:
    - Tracking active calls per campaign
    - Enforcing max_concurrent_calls limits
    - Enforcing calls_per_minute rate limits
    - Managing a queue of pending contacts to dial
    - Coordinating with the dialer engine to initiate calls
    """

    def __init__(
        self,
        global_max_concurrent: int = 50,
        call_initiator: Optional[Callable] = None
    ):
        """
        Initialize the call manager.

        Args:
            global_max_concurrent: Maximum total concurrent calls across all campaigns
            call_initiator: Async function to initiate a call (destination, caller_id, ivr_flow, campaign_id, contact_id)
        """
        self.global_max_concurrent = global_max_concurrent
        self.call_initiator = call_initiator

        # Campaign states keyed by campaign_id
        self.campaign_states: Dict[str, CampaignCallState] = {}

        # Map call_id to campaign_id for quick lookup
        self.call_to_campaign: Dict[str, str] = {}

        # Pending contacts queue (sorted by priority then scheduled time)
        self.pending_contacts: List[PendingContact] = []

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        # Processing flag
        self._processing = False
        self._process_task: Optional[asyncio.Task] = None

    @property
    def total_active_calls(self) -> int:
        """Get total active calls across all campaigns."""
        return sum(state.active_call_count for state in self.campaign_states.values())

    @property
    def global_slots_available(self) -> int:
        """Get available global call slots."""
        return max(0, self.global_max_concurrent - self.total_active_calls)

    def register_campaign(
        self,
        campaign_id: str,
        max_concurrent_calls: int,
        calls_per_minute: Optional[int] = None
    ) -> None:
        """Register a campaign for call management."""
        if campaign_id not in self.campaign_states:
            self.campaign_states[campaign_id] = CampaignCallState(
                campaign_id=campaign_id,
                max_concurrent_calls=max_concurrent_calls,
                calls_per_minute=calls_per_minute
            )
            logger.info(
                f"Registered campaign {campaign_id} with "
                f"max_concurrent={max_concurrent_calls}, "
                f"calls_per_minute={calls_per_minute}"
            )
        else:
            # Update settings if campaign already registered
            state = self.campaign_states[campaign_id]
            state.max_concurrent_calls = max_concurrent_calls
            state.calls_per_minute = calls_per_minute

    def unregister_campaign(self, campaign_id: str) -> None:
        """Unregister a campaign."""
        if campaign_id in self.campaign_states:
            state = self.campaign_states[campaign_id]
            # Clean up call mappings
            for call_id in list(state.active_call_ids):
                self.call_to_campaign.pop(call_id, None)
            del self.campaign_states[campaign_id]

            # Remove pending contacts for this campaign
            self.pending_contacts = [
                pc for pc in self.pending_contacts
                if pc.campaign_id != campaign_id
            ]

            logger.info(f"Unregistered campaign {campaign_id}")

    async def add_contacts_to_queue(self, contacts: List[PendingContact]) -> int:
        """Add contacts to the pending queue."""
        async with self._lock:
            for contact in contacts:
                # Ensure campaign is registered
                if contact.campaign_id not in self.campaign_states:
                    logger.warning(
                        f"Campaign {contact.campaign_id} not registered, skipping contact"
                    )
                    continue
                self.pending_contacts.append(contact)

            # Sort by priority (lower first) then by scheduled time
            self.pending_contacts.sort(
                key=lambda c: (c.priority, c.scheduled_at or datetime.min)
            )

            logger.debug(f"Added {len(contacts)} contacts to queue, total pending: {len(self.pending_contacts)}")
            return len(contacts)

    def can_make_call(self, campaign_id: str) -> bool:
        """Check if a call can be made for the given campaign."""
        # Check global limit
        if self.total_active_calls >= self.global_max_concurrent:
            return False

        # Check campaign-specific limits
        state = self.campaign_states.get(campaign_id)
        if not state:
            return False

        return state.can_make_call()

    def get_available_slots(self, campaign_id: str) -> int:
        """Get number of available slots for a campaign."""
        state = self.campaign_states.get(campaign_id)
        if not state:
            return 0

        # Limit by both campaign and global limits
        campaign_slots = state.available_slots
        global_slots = self.global_slots_available

        return min(campaign_slots, global_slots)

    async def record_call_start(self, campaign_id: str, call_id: str) -> None:
        """Record that a call has started."""
        async with self._lock:
            state = self.campaign_states.get(campaign_id)
            if state:
                state.record_call_start(call_id)
                self.call_to_campaign[call_id] = campaign_id

    async def record_call_end(self, call_id: str, success: bool = True) -> None:
        """Record that a call has ended."""
        async with self._lock:
            campaign_id = self.call_to_campaign.pop(call_id, None)
            if campaign_id:
                state = self.campaign_states.get(campaign_id)
                if state:
                    state.record_call_end(call_id, success)

    async def start_processing(self) -> None:
        """Start the call processing loop."""
        if self._processing:
            return

        self._processing = True
        self._process_task = asyncio.create_task(self._process_loop())
        logger.info("Call manager processing started")

    async def stop_processing(self) -> None:
        """Stop the call processing loop."""
        self._processing = False
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
        logger.info("Call manager processing stopped")

    async def _process_loop(self) -> None:
        """Main processing loop that initiates calls from the queue."""
        while self._processing:
            try:
                await self._process_pending_contacts()
                # Small delay between processing cycles
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in call processing loop: {e}")
                await asyncio.sleep(1)

    async def _process_pending_contacts(self) -> None:
        """Process pending contacts and initiate calls where possible."""
        if not self.call_initiator:
            return

        if not self.pending_contacts:
            return

        async with self._lock:
            now = datetime.utcnow()
            contacts_to_dial = []
            remaining_contacts = []

            for contact in self.pending_contacts:
                # Check if scheduled for later
                if contact.scheduled_at and contact.scheduled_at > now:
                    remaining_contacts.append(contact)
                    continue

                # Check if we can make a call for this campaign
                if self.can_make_call(contact.campaign_id):
                    contacts_to_dial.append(contact)
                else:
                    remaining_contacts.append(contact)

            self.pending_contacts = remaining_contacts

        # Initiate calls outside the lock
        for contact in contacts_to_dial:
            try:
                await self._initiate_call(contact)
            except Exception as e:
                logger.error(f"Failed to initiate call to {contact.phone_number}: {e}")
                # Re-queue failed contact with a short delay for retry
                contact.scheduled_at = datetime.utcnow() + timedelta(seconds=30)
                async with self._lock:
                    self.pending_contacts.append(contact)
                logger.info(f"Re-queued contact {contact.phone_number} for retry in 30 seconds")

    async def _initiate_call(self, contact: PendingContact) -> None:
        """Initiate a single call."""
        if not self.call_initiator:
            return

        logger.info(
            f"Initiating call to {contact.phone_number} for campaign {contact.campaign_id}"
        )

        try:
            call = await self.call_initiator(
                destination=contact.phone_number,
                caller_id=contact.caller_id,
                ivr_flow_definition=contact.ivr_flow_definition,
                campaign_id=contact.campaign_id,
                contact_id=contact.contact_id,
                campaign_contact_id=contact.campaign_contact_id
            )

            if call:
                await self.record_call_start(contact.campaign_id, call.info.call_id)
            else:
                logger.warning(f"Call initiation returned None for {contact.phone_number}")

        except Exception as e:
            logger.error(f"Error initiating call: {e}")
            raise

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the call manager."""
        return {
            "global_max_concurrent": self.global_max_concurrent,
            "total_active_calls": self.total_active_calls,
            "global_slots_available": self.global_slots_available,
            "pending_contacts": len(self.pending_contacts),
            "campaigns": {
                campaign_id: {
                    "max_concurrent_calls": state.max_concurrent_calls,
                    "active_calls": state.active_call_count,
                    "available_slots": state.available_slots,
                    "calls_per_minute": state.calls_per_minute,
                    "total_initiated": state.total_calls_initiated,
                    "total_completed": state.total_calls_completed,
                    "total_failed": state.total_calls_failed,
                }
                for campaign_id, state in self.campaign_states.items()
            }
        }
