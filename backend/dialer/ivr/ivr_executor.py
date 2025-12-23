"""
IVR Executor for Direct SIP Media Control.

This module executes IVR flows using direct SIP media control instead of
the AGI protocol. It processes IVR flow definitions and interacts with
calls via the PJSUA2 SIPCall and MediaHandler classes.

This replaces the AGI-based approach which required Asterisk, allowing
the auto-dialer to work directly with Grandstream UCM or any SIP endpoint.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger(__name__)


class IVRExecutionState(Enum):
    """IVR execution states."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IVRNodeType(str, Enum):
    """Types of IVR nodes (matching database model)."""
    START = "start"
    PLAY_AUDIO = "play_audio"
    MENU = "menu"
    SURVEY_QUESTION = "survey_question"
    RECORD = "record"
    TRANSFER = "transfer"
    CONDITIONAL = "conditional"
    SET_VARIABLE = "set_variable"
    HANGUP = "hangup"
    OPT_OUT = "opt_out"  # Adds caller to DNC list


@dataclass
class IVRContext:
    """Context for IVR execution, holds variables and state."""
    call_id: str
    contact_id: Optional[str] = None
    campaign_id: Optional[str] = None
    phone_number: Optional[str] = None  # For DNC opt-out
    organization_id: Optional[str] = None  # For DNC opt-out
    variables: Dict[str, Any] = field(default_factory=dict)
    survey_responses: Dict[str, str] = field(default_factory=dict)
    dtmf_inputs: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    current_node_id: Optional[str] = None
    opted_out: bool = False  # Set to True if caller opted out


@dataclass
class IVRResult:
    """Result of IVR execution."""
    state: IVRExecutionState
    completed_normally: bool
    survey_responses: Dict[str, str]
    dtmf_inputs: List[str]
    variables: Dict[str, Any]
    duration_seconds: float
    last_node_id: Optional[str] = None
    error_message: Optional[str] = None
    opted_out: bool = False  # True if caller chose to opt out


class IVRExecutor:
    """
    Execute IVR flows using SIP media.

    This class processes IVR flow definitions and controls call media
    to play audio, collect DTMF, and navigate the flow based on user input.
    """

    def __init__(
        self,
        call: 'SIPCall',
        media_handler: 'MediaHandler',
        audio_file_resolver: Optional[Callable[[str], str]] = None
    ):
        """
        Initialize the IVR executor.

        Args:
            call: The SIPCall instance for this IVR session
            media_handler: MediaHandler for audio playback and DTMF
            audio_file_resolver: Function to resolve audio file IDs to paths
        """
        self.call = call
        self.media = media_handler
        self.audio_file_resolver = audio_file_resolver or (lambda x: x)

        self._state = IVRExecutionState.IDLE
        self._context: Optional[IVRContext] = None
        self._flow_definition: Optional[Dict] = None
        self._nodes: Dict[str, Dict] = {}
        self._cancelled = False

    @property
    def state(self) -> IVRExecutionState:
        """Get current execution state."""
        return self._state

    @property
    def context(self) -> Optional[IVRContext]:
        """Get current execution context."""
        return self._context

    async def execute_flow(
        self,
        flow_definition: Dict,
        context: Optional[IVRContext] = None
    ) -> IVRResult:
        """
        Process IVR flow nodes.

        Args:
            flow_definition: The IVR flow definition from database
                Expected structure:
                {
                    "nodes": [...],
                    "edges": [...],
                    "start_node": "node_id"
                }
            context: Optional execution context (created if not provided)

        Returns:
            IVRResult with execution results
        """
        self._state = IVRExecutionState.RUNNING
        self._flow_definition = flow_definition
        self._cancelled = False

        # Build node lookup
        self._nodes = {
            node["id"]: node
            for node in flow_definition.get("nodes", [])
        }

        # Initialize context
        self._context = context or IVRContext(call_id=self.call.info.call_id)

        start_time = time.time()
        logger.info(f"Starting IVR execution for call {self._context.call_id}")

        try:
            # Get start node
            start_node_id = flow_definition.get("start_node")
            if not start_node_id:
                # Find START node type
                for node in flow_definition.get("nodes", []):
                    if node.get("type") == IVRNodeType.START.value:
                        start_node_id = node["id"]
                        break

            if not start_node_id:
                raise ValueError("No start node found in IVR flow")

            # Process nodes
            current_node_id = start_node_id
            while current_node_id and not self._cancelled:
                self._context.current_node_id = current_node_id
                node = self._nodes.get(current_node_id)

                if not node:
                    logger.error(f"Node not found: {current_node_id}")
                    break

                logger.debug(f"Processing node: {current_node_id} ({node.get('type')})")

                # Process the node
                next_node_id = await self._process_node(node)

                # Move to next node
                current_node_id = next_node_id

            # Execution completed
            self._state = IVRExecutionState.COMPLETED
            return IVRResult(
                state=self._state,
                completed_normally=not self._cancelled,
                survey_responses=self._context.survey_responses,
                dtmf_inputs=self._context.dtmf_inputs,
                variables=self._context.variables,
                duration_seconds=time.time() - start_time,
                last_node_id=self._context.current_node_id,
                opted_out=self._context.opted_out
            )

        except Exception as e:
            logger.error(f"IVR execution error: {e}")
            self._state = IVRExecutionState.FAILED
            return IVRResult(
                state=self._state,
                completed_normally=False,
                survey_responses=self._context.survey_responses if self._context else {},
                dtmf_inputs=self._context.dtmf_inputs if self._context else [],
                variables=self._context.variables if self._context else {},
                duration_seconds=time.time() - start_time,
                last_node_id=self._context.current_node_id if self._context else None,
                error_message=str(e),
                opted_out=self._context.opted_out if self._context else False
            )

    async def _process_node(self, node: Dict) -> Optional[str]:
        """
        Process single IVR node, return next node ID.

        Args:
            node: Node definition

        Returns:
            ID of next node to process, or None to end
        """
        node_type = node.get("type", "").lower()
        node_data = node.get("data", {})

        if node_type == IVRNodeType.START.value:
            return await self._handle_start_node(node, node_data)

        elif node_type == IVRNodeType.PLAY_AUDIO.value:
            return await self._handle_play_audio_node(node, node_data)

        elif node_type == IVRNodeType.MENU.value:
            return await self._handle_menu_node(node, node_data)

        elif node_type == IVRNodeType.SURVEY_QUESTION.value:
            return await self._handle_survey_question_node(node, node_data)

        elif node_type == IVRNodeType.CONDITIONAL.value:
            return await self._handle_conditional_node(node, node_data)

        elif node_type == IVRNodeType.SET_VARIABLE.value:
            return await self._handle_set_variable_node(node, node_data)

        elif node_type == IVRNodeType.HANGUP.value:
            return await self._handle_hangup_node(node, node_data)

        elif node_type == IVRNodeType.TRANSFER.value:
            return await self._handle_transfer_node(node, node_data)

        elif node_type == IVRNodeType.RECORD.value:
            return await self._handle_record_node(node, node_data)

        elif node_type == IVRNodeType.OPT_OUT.value:
            return await self._handle_opt_out_node(node, node_data)

        else:
            logger.warning(f"Unknown node type: {node_type}")
            return self._get_default_next_node(node)

    async def _handle_start_node(self, node: Dict, data: Dict) -> Optional[str]:
        """Handle START node."""
        # START node just passes through to next node
        return self._get_default_next_node(node)

    async def _handle_play_audio_node(self, node: Dict, data: Dict) -> Optional[str]:
        """Handle PLAY_AUDIO node."""
        audio_file_id = data.get("audio_file_id")
        wait_for_dtmf = data.get("wait_for_dtmf", False)
        dtmf_timeout = data.get("dtmf_timeout", 5.0)

        if not audio_file_id:
            logger.warning(f"No audio file specified for node {node['id']}")
            return self._get_default_next_node(node)

        # Resolve audio file path
        audio_path = self.audio_file_resolver(audio_file_id)

        try:
            if wait_for_dtmf:
                # Play with DTMF interrupt
                interrupt_digit = await self.media.play_file(
                    audio_path,
                    wait_for_completion=True,
                    allow_dtmf_interrupt=True
                )

                if interrupt_digit:
                    self._context.dtmf_inputs.append(interrupt_digit)
                    # Check if there's a specific route for this digit
                    options = data.get("options", {})
                    if interrupt_digit in options:
                        return options[interrupt_digit]
            else:
                # Just play the file
                await self.media.play_file(audio_path, wait_for_completion=True)

        except FileNotFoundError:
            logger.error(f"Audio file not found: {audio_path}")
        except Exception as e:
            logger.error(f"Error playing audio: {e}")

        return self._get_default_next_node(node)

    async def _handle_menu_node(self, node: Dict, data: Dict) -> Optional[str]:
        """Handle MENU node."""
        prompt_audio_id = data.get("prompt_audio_id")
        timeout = data.get("timeout", 5.0)
        max_retries = data.get("max_retries", 3)
        options = data.get("options", {})
        invalid_node = data.get("invalid_node")
        timeout_node = data.get("timeout_node") or options.get("timeout")

        for attempt in range(max_retries):
            # Play prompt
            if prompt_audio_id:
                audio_path = self.audio_file_resolver(prompt_audio_id)
                try:
                    interrupt = await self.media.play_file(
                        audio_path,
                        wait_for_completion=True,
                        allow_dtmf_interrupt=True
                    )
                    if interrupt and interrupt in options:
                        self._context.dtmf_inputs.append(interrupt)
                        return options[interrupt]
                except Exception as e:
                    logger.error(f"Error playing menu prompt: {e}")

            # Collect DTMF
            result = await self.media.collect_dtmf(
                max_digits=1,
                timeout=timeout,
                termination_digits=""  # Don't terminate on any digit
            )

            if result.timed_out:
                if attempt == max_retries - 1:
                    return timeout_node
                continue

            digit = result.digits
            if digit:
                self._context.dtmf_inputs.append(digit)

                if digit in options:
                    return options[digit]
                elif invalid_node:
                    return invalid_node

        # All retries exhausted
        return timeout_node or self._get_default_next_node(node)

    async def _handle_survey_question_node(self, node: Dict, data: Dict) -> Optional[str]:
        """Handle SURVEY_QUESTION node."""
        question_id = data.get("question_id", node["id"])
        prompt_audio_id = data.get("prompt_audio_id")
        valid_inputs = data.get("valid_inputs", ["1", "2", "3", "4", "5"])
        timeout = data.get("timeout", 10.0)
        max_retries = data.get("max_retries", 2)

        for attempt in range(max_retries):
            # Play prompt
            if prompt_audio_id:
                audio_path = self.audio_file_resolver(prompt_audio_id)
                try:
                    interrupt = await self.media.play_file(
                        audio_path,
                        wait_for_completion=True,
                        allow_dtmf_interrupt=True
                    )
                    if interrupt and interrupt in valid_inputs:
                        self._context.dtmf_inputs.append(interrupt)
                        self._context.survey_responses[question_id] = interrupt
                        return self._get_default_next_node(node)
                except Exception as e:
                    logger.error(f"Error playing survey prompt: {e}")

            # Collect response
            result = await self.media.collect_dtmf(
                max_digits=1,
                timeout=timeout,
                termination_digits=""
            )

            if result.digits and result.digits in valid_inputs:
                self._context.dtmf_inputs.append(result.digits)
                self._context.survey_responses[question_id] = result.digits
                logger.info(f"Survey response for {question_id}: {result.digits}")
                return self._get_default_next_node(node)

        # No valid response received
        self._context.survey_responses[question_id] = ""
        return self._get_default_next_node(node)

    async def _handle_conditional_node(self, node: Dict, data: Dict) -> Optional[str]:
        """Handle CONDITIONAL node."""
        variable = data.get("variable")
        operator = data.get("operator", "equals")
        value = data.get("value")
        true_node = data.get("true_node")
        false_node = data.get("false_node")

        if not variable:
            return self._get_default_next_node(node)

        # Get variable value
        var_value = self._context.variables.get(variable)

        # Evaluate condition
        result = False
        if operator == "equals":
            result = str(var_value) == str(value)
        elif operator == "not_equals":
            result = str(var_value) != str(value)
        elif operator == "contains":
            result = str(value) in str(var_value)
        elif operator == "exists":
            result = var_value is not None
        elif operator == "empty":
            result = not var_value

        return true_node if result else (false_node or self._get_default_next_node(node))

    async def _handle_set_variable_node(self, node: Dict, data: Dict) -> Optional[str]:
        """Handle SET_VARIABLE node."""
        variable = data.get("variable")
        value = data.get("value")

        if variable:
            self._context.variables[variable] = value
            logger.debug(f"Set variable {variable} = {value}")

        return self._get_default_next_node(node)

    async def _handle_hangup_node(self, node: Dict, data: Dict) -> Optional[str]:
        """Handle HANGUP node."""
        # Optionally play goodbye message
        goodbye_audio_id = data.get("goodbye_audio_id")
        if goodbye_audio_id:
            audio_path = self.audio_file_resolver(goodbye_audio_id)
            try:
                await self.media.play_file(audio_path, wait_for_completion=True)
            except Exception as e:
                logger.error(f"Error playing goodbye audio: {e}")

        # Hang up the call
        self.call.hangup()

        # Return None to end flow
        return None

    async def _handle_transfer_node(self, node: Dict, data: Dict) -> Optional[str]:
        """Handle TRANSFER node (not implemented for direct SIP)."""
        # Transfer requires PBX features - log and continue
        transfer_to = data.get("transfer_to")
        logger.warning(f"Transfer to {transfer_to} requested but not supported in direct SIP mode")
        return self._get_default_next_node(node)

    async def _handle_record_node(self, node: Dict, data: Dict) -> Optional[str]:
        """Handle RECORD node (not implemented yet)."""
        # Recording requires RTP capture - not implemented
        logger.warning("Recording not yet implemented in direct SIP mode")
        return self._get_default_next_node(node)

    async def _handle_opt_out_node(self, node: Dict, data: Dict) -> Optional[str]:
        """
        Handle OPT_OUT node - marks caller for DNC list addition.

        The actual DNC entry creation happens in the dialer main.py after
        IVR execution completes, using the opted_out flag in IVRResult.

        This node can optionally:
        - Play a confirmation audio
        - Then hang up or continue to next node
        """
        # Mark context as opted out
        self._context.opted_out = True
        self._context.variables["opt_out_reason"] = data.get("reason", "user_request")

        logger.info(
            f"Call {self._context.call_id}: Caller opted out "
            f"(phone: {self._context.phone_number})"
        )

        # Play confirmation audio if specified
        confirmation_audio_id = data.get("confirmation_audio_id")
        if confirmation_audio_id:
            audio_path = self.audio_file_resolver(confirmation_audio_id)
            try:
                await self.media.play_file(audio_path, wait_for_completion=True)
            except Exception as e:
                logger.error(f"Error playing opt-out confirmation: {e}")

        # Check if we should hang up after opt-out (default: yes)
        hangup_after = data.get("hangup_after", True)
        if hangup_after:
            self.call.hangup()
            return None

        return self._get_default_next_node(node)

    def _get_default_next_node(self, node: Dict) -> Optional[str]:
        """Get the default next node from edges."""
        node_id = node["id"]

        # Look for edge from this node
        for edge in self._flow_definition.get("edges", []):
            if edge.get("source") == node_id:
                return edge.get("target")

        # Check node data for explicit next
        if "next_node" in node.get("data", {}):
            return node["data"]["next_node"]

        return None

    def cancel(self):
        """Cancel IVR execution."""
        self._cancelled = True
        self._state = IVRExecutionState.CANCELLED


# Type hints for IDE support
try:
    from ..sip_engine.pjsua_client import SIPCall
    from ..sip_engine.media_handler import MediaHandler
except ImportError:
    pass
