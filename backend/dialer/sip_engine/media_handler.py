"""
Media Handler for PJSUA2 SIP Calls.

This module handles RTP audio playback and DTMF detection for SIP calls.
It provides methods to:
- Play audio files (WAV format) to the call
- Stop audio playback
- Collect DTMF digits from the call

The MediaHandler works with PJSUA2's AudioMediaPlayer and AudioMedia
to stream audio to the remote party and receive DTMF events.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List, Callable, Any

logger = logging.getLogger(__name__)

# Try to import pjsua2
try:
    import pjsua2 as pj
    PJSUA2_AVAILABLE = True
except ImportError:
    PJSUA2_AVAILABLE = False
    pj = None


class PlaybackState(Enum):
    """Audio playback state."""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class DTMFCollectionResult:
    """Result of DTMF collection."""
    digits: str
    timed_out: bool
    max_reached: bool
    terminated_by: str = ""  # Digit that caused termination (e.g., '#')


class MediaHandler:
    """
    Handles RTP audio playback and DTMF detection for a SIP call.

    This class provides methods to play audio files to the remote party
    and collect DTMF digits from their input.
    """

    def __init__(self, call: 'SIPCall'):
        """
        Initialize the media handler.

        Args:
            call: The SIPCall instance this handler is for
        """
        self.call = call
        self._audio_player: Optional[Any] = None
        self._playback_state = PlaybackState.IDLE
        self._dtmf_buffer: List[str] = []
        self._dtmf_event = asyncio.Event()
        self._playback_completed_event = asyncio.Event()

        # Register for DTMF callbacks
        call.set_dtmf_callback(self._on_dtmf_digit)

    def _on_dtmf_digit(self, digit: str):
        """Internal callback when DTMF digit received."""
        self._dtmf_buffer.append(digit)
        self._dtmf_event.set()
        logger.debug(f"DTMF digit received: {digit}")

    async def play_file(
        self,
        filepath: str,
        wait_for_completion: bool = True,
        allow_dtmf_interrupt: bool = False,
        interrupt_digits: str = "#*0123456789"
    ) -> Optional[str]:
        """
        Play an audio file to the call.

        Args:
            filepath: Path to the audio file (WAV format, 8kHz or 16kHz, mono)
            wait_for_completion: Wait for playback to complete
            allow_dtmf_interrupt: Allow DTMF to interrupt playback
            interrupt_digits: Digits that can interrupt playback

        Returns:
            The interrupting DTMF digit if interrupted, None otherwise

        Raises:
            FileNotFoundError: If the audio file doesn't exist
            RuntimeError: If PJSUA2 is not available or call media not active
        """
        if not PJSUA2_AVAILABLE:
            raise RuntimeError("PJSUA2 not available")

        # Verify file exists
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {filepath}")

        # Get call audio media
        audio_media = self.call.get_audio_media()
        if not audio_media:
            raise RuntimeError("Call audio media not active")

        logger.info(f"Playing audio file: {filepath}")

        try:
            # Create audio player
            self._audio_player = pj.AudioMediaPlayer()
            self._audio_player.createPlayer(str(path), pj.PJMEDIA_FILE_NO_LOOP)

            # Log audio media info for debugging
            try:
                port_info = audio_media.getPortInfo()
                logger.info(f"Call audio media: name={port_info.name}, format={port_info.format.clockRate}Hz")
            except Exception as e:
                logger.debug(f"Could not get port info: {e}")

            # Connect player to call's audio media
            # This transmits the audio file to the remote party via RTP
            self._audio_player.startTransmit(audio_media)
            logger.info(f"Audio player connected to call media - transmitting to remote party")

            self._playback_state = PlaybackState.PLAYING
            self._playback_completed_event.clear()

            if wait_for_completion:
                # Clear DTMF buffer for interrupt detection
                if allow_dtmf_interrupt:
                    self._dtmf_buffer.clear()
                    self._dtmf_event.clear()

                # Wait for playback to complete or be interrupted
                interrupt_digit = await self._wait_for_playback(
                    allow_dtmf_interrupt,
                    interrupt_digits
                )

                return interrupt_digit

            return None

        except Exception as e:
            self._playback_state = PlaybackState.ERROR
            logger.error(f"Error playing audio file: {e}")
            raise

    async def _wait_for_playback(
        self,
        allow_dtmf_interrupt: bool,
        interrupt_digits: str
    ) -> Optional[str]:
        """Wait for playback completion or DTMF interrupt."""
        # Poll for playback completion since PJSUA2 doesn't have async completion callback
        poll_interval = 0.1  # seconds

        while self._playback_state == PlaybackState.PLAYING:
            # Check for DTMF interrupt
            if allow_dtmf_interrupt:
                if self._dtmf_buffer:
                    for digit in self._dtmf_buffer:
                        if digit in interrupt_digits:
                            await self.stop_playback()
                            return digit

            # Check if player is still playing
            if self._audio_player:
                try:
                    # getPos() returns 0 when playback is done
                    pos = self._audio_player.getPos()
                    # This is a simplified check - actual implementation may vary
                    if pos == 0 and self._playback_state == PlaybackState.PLAYING:
                        # Check if we've been playing for a while
                        await asyncio.sleep(poll_interval)
                        if self._audio_player.getPos() == 0:
                            self._playback_state = PlaybackState.COMPLETED
                            break
                except Exception:
                    # Player might be done
                    self._playback_state = PlaybackState.COMPLETED
                    break

            await asyncio.sleep(poll_interval)

        return None

    async def stop_playback(self):
        """Stop current audio playback."""
        if self._audio_player:
            try:
                # Stop transmitting
                audio_media = self.call.get_audio_media()
                if audio_media:
                    self._audio_player.stopTransmit(audio_media)

                # Destroy player
                self._audio_player = None
            except Exception as e:
                logger.warning(f"Error stopping playback: {e}")

        self._playback_state = PlaybackState.STOPPED
        self._playback_completed_event.set()

    async def collect_dtmf(
        self,
        max_digits: int = 1,
        timeout: float = 10.0,
        inter_digit_timeout: float = 3.0,
        termination_digits: str = "#",
        initial_timeout: Optional[float] = None
    ) -> DTMFCollectionResult:
        """
        Collect DTMF digits from the call.

        Args:
            max_digits: Maximum number of digits to collect
            timeout: Total timeout for collection (seconds)
            inter_digit_timeout: Timeout between digits (seconds)
            termination_digits: Digits that terminate collection early (e.g., '#')
            initial_timeout: Timeout for first digit (uses timeout if not specified)

        Returns:
            DTMFCollectionResult with collected digits and termination info
        """
        logger.debug(f"Collecting DTMF: max={max_digits}, timeout={timeout}s")

        # Clear buffer
        self._dtmf_buffer.clear()
        self._dtmf_event.clear()

        collected_digits = []
        start_time = time.time()
        last_digit_time = start_time
        first_digit_received = False

        first_timeout = initial_timeout or timeout

        while len(collected_digits) < max_digits:
            # Calculate remaining timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                return DTMFCollectionResult(
                    digits="".join(collected_digits),
                    timed_out=True,
                    max_reached=False
                )

            # Calculate inter-digit timeout
            if first_digit_received:
                remaining_inter = inter_digit_timeout - (time.time() - last_digit_time)
            else:
                remaining_inter = first_timeout - elapsed

            if remaining_inter <= 0:
                return DTMFCollectionResult(
                    digits="".join(collected_digits),
                    timed_out=True,
                    max_reached=False
                )

            # Wait for digit
            try:
                await asyncio.wait_for(
                    self._dtmf_event.wait(),
                    timeout=min(remaining_inter, timeout - elapsed)
                )

                # Process received digits
                while self._dtmf_buffer:
                    digit = self._dtmf_buffer.pop(0)
                    last_digit_time = time.time()
                    first_digit_received = True

                    # Check for termination digit
                    if digit in termination_digits:
                        return DTMFCollectionResult(
                            digits="".join(collected_digits),
                            timed_out=False,
                            max_reached=False,
                            terminated_by=digit
                        )

                    collected_digits.append(digit)

                    if len(collected_digits) >= max_digits:
                        return DTMFCollectionResult(
                            digits="".join(collected_digits),
                            timed_out=False,
                            max_reached=True
                        )

                self._dtmf_event.clear()

            except asyncio.TimeoutError:
                return DTMFCollectionResult(
                    digits="".join(collected_digits),
                    timed_out=True,
                    max_reached=False
                )

        return DTMFCollectionResult(
            digits="".join(collected_digits),
            timed_out=False,
            max_reached=True
        )

    def clear_dtmf_buffer(self):
        """Clear the DTMF buffer."""
        self._dtmf_buffer.clear()
        self._dtmf_event.clear()

    @property
    def dtmf_buffer(self) -> List[str]:
        """Get current DTMF buffer (copy)."""
        return self._dtmf_buffer.copy()

    @property
    def playback_state(self) -> PlaybackState:
        """Get current playback state."""
        return self._playback_state

    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._playback_state == PlaybackState.PLAYING


# Type hint import for IDE support
if PJSUA2_AVAILABLE:
    from .pjsua_client import SIPCall
