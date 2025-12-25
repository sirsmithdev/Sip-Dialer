"""
Simple Voice Activity Detection (VAD) for speech boundary detection.
"""
import time
import struct
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class SimpleVAD:
    """
    Simple energy-based Voice Activity Detection.

    Detects speech boundaries by monitoring audio energy levels.
    Returns complete utterances when silence is detected after speech.
    """

    def __init__(
        self,
        energy_threshold: float = 0.02,
        silence_duration: float = 0.8,
        min_speech_duration: float = 0.3,
        max_speech_duration: float = 30.0,
        sample_rate: int = 16000,
        sample_width: int = 2
    ):
        """
        Initialize VAD.

        Args:
            energy_threshold: RMS energy threshold for speech detection (0-1)
            silence_duration: Seconds of silence to mark end of speech
            min_speech_duration: Minimum speech duration to be valid
            max_speech_duration: Maximum speech duration before forced return
            sample_rate: Audio sample rate in Hz
            sample_width: Bytes per sample (2 for 16-bit)
        """
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self.min_speech_duration = min_speech_duration
        self.max_speech_duration = max_speech_duration
        self.sample_rate = sample_rate
        self.sample_width = sample_width

        # State
        self._buffer: List[bytes] = []
        self._speech_start: Optional[float] = None
        self._silence_start: Optional[float] = None
        self._is_speaking = False

    def process_chunk(self, audio_chunk: bytes) -> Optional[bytes]:
        """
        Process an audio chunk and detect speech boundaries.

        Args:
            audio_chunk: Raw PCM audio data

        Returns:
            Complete utterance bytes if speech ended, None otherwise
        """
        if not audio_chunk:
            return None

        current_time = time.time()
        energy = self._calculate_energy(audio_chunk)

        # Speech detected
        if energy > self.energy_threshold:
            if self._speech_start is None:
                self._speech_start = current_time
                logger.debug("Speech started")

            self._silence_start = None
            self._is_speaking = True
            self._buffer.append(audio_chunk)

            # Check max duration
            if current_time - self._speech_start > self.max_speech_duration:
                logger.debug("Max speech duration reached")
                return self._flush_buffer()

        # Silence detected
        else:
            if self._is_speaking:
                # Include some trailing silence
                self._buffer.append(audio_chunk)

                if self._silence_start is None:
                    self._silence_start = current_time
                elif current_time - self._silence_start > self.silence_duration:
                    # End of speech
                    speech_duration = current_time - self._speech_start if self._speech_start else 0

                    if speech_duration >= self.min_speech_duration:
                        logger.debug(f"Speech ended, duration: {speech_duration:.2f}s")
                        return self._flush_buffer()
                    else:
                        logger.debug("Speech too short, discarding")
                        self._reset()

        return None

    def _calculate_energy(self, audio_chunk: bytes) -> float:
        """
        Calculate RMS energy of audio chunk.

        Args:
            audio_chunk: Raw PCM audio data

        Returns:
            Normalized RMS energy (0-1)
        """
        if len(audio_chunk) < self.sample_width:
            return 0.0

        # Unpack 16-bit samples
        num_samples = len(audio_chunk) // self.sample_width
        samples = struct.unpack(f'{num_samples}h', audio_chunk[:num_samples * self.sample_width])

        # Calculate RMS
        sum_squares = sum(s * s for s in samples)
        rms = (sum_squares / num_samples) ** 0.5

        # Normalize to 0-1 range (32768 is max for 16-bit)
        return rms / 32768.0

    def _flush_buffer(self) -> bytes:
        """Flush and return buffered audio."""
        utterance = b''.join(self._buffer)
        self._reset()
        return utterance

    def _reset(self):
        """Reset VAD state."""
        self._buffer = []
        self._speech_start = None
        self._silence_start = None
        self._is_speaking = False

    def reset(self):
        """Public reset method."""
        self._reset()

    @property
    def is_speaking(self) -> bool:
        """Check if currently in speaking state."""
        return self._is_speaking

    @property
    def speech_duration(self) -> float:
        """Get current speech duration in seconds."""
        if self._speech_start is None:
            return 0.0
        return time.time() - self._speech_start

    def force_end(self) -> Optional[bytes]:
        """
        Force end of speech and return buffer.

        Useful for timeouts or call end.

        Returns:
            Buffered audio bytes if any
        """
        if self._buffer:
            return self._flush_buffer()
        return None


class WebRTCVAD:
    """
    WebRTC-based VAD using py-webrtcvad library.

    More accurate than energy-based VAD but requires additional dependency.
    Falls back to SimpleVAD if webrtcvad is not available.
    """

    def __init__(
        self,
        aggressiveness: int = 2,
        frame_duration_ms: int = 30,
        silence_duration: float = 0.8,
        min_speech_duration: float = 0.3,
        sample_rate: int = 16000
    ):
        """
        Initialize WebRTC VAD.

        Args:
            aggressiveness: VAD aggressiveness (0-3, higher = more aggressive)
            frame_duration_ms: Frame duration (10, 20, or 30 ms)
            silence_duration: Seconds of silence to mark end of speech
            min_speech_duration: Minimum speech duration
            sample_rate: Audio sample rate (8000, 16000, 32000, or 48000)
        """
        self.frame_duration_ms = frame_duration_ms
        self.silence_duration = silence_duration
        self.min_speech_duration = min_speech_duration
        self.sample_rate = sample_rate

        # Calculate frame size
        self.frame_size = int(sample_rate * frame_duration_ms / 1000) * 2  # 2 bytes per sample

        try:
            import webrtcvad
            self.vad = webrtcvad.Vad(aggressiveness)
            self._use_webrtc = True
        except ImportError:
            logger.warning("webrtcvad not available, using SimpleVAD")
            self._fallback = SimpleVAD(
                silence_duration=silence_duration,
                min_speech_duration=min_speech_duration,
                sample_rate=sample_rate
            )
            self._use_webrtc = False

        # State
        self._buffer: List[bytes] = []
        self._speech_start: Optional[float] = None
        self._silence_start: Optional[float] = None
        self._is_speaking = False
        self._frame_buffer = b''

    def process_chunk(self, audio_chunk: bytes) -> Optional[bytes]:
        """Process audio chunk and detect speech boundaries."""
        if not self._use_webrtc:
            return self._fallback.process_chunk(audio_chunk)

        # Buffer audio until we have enough for a frame
        self._frame_buffer += audio_chunk
        current_time = time.time()

        while len(self._frame_buffer) >= self.frame_size:
            frame = self._frame_buffer[:self.frame_size]
            self._frame_buffer = self._frame_buffer[self.frame_size:]

            is_speech = self.vad.is_speech(frame, self.sample_rate)

            if is_speech:
                if self._speech_start is None:
                    self._speech_start = current_time
                self._silence_start = None
                self._is_speaking = True
                self._buffer.append(frame)
            else:
                if self._is_speaking:
                    self._buffer.append(frame)
                    if self._silence_start is None:
                        self._silence_start = current_time
                    elif current_time - self._silence_start > self.silence_duration:
                        speech_duration = current_time - self._speech_start if self._speech_start else 0
                        if speech_duration >= self.min_speech_duration:
                            return self._flush_buffer()
                        self._reset()

        return None

    def _flush_buffer(self) -> bytes:
        """Flush and return buffered audio."""
        utterance = b''.join(self._buffer)
        self._reset()
        return utterance

    def _reset(self):
        """Reset state."""
        self._buffer = []
        self._speech_start = None
        self._silence_start = None
        self._is_speaking = False

    def reset(self):
        """Public reset."""
        self._reset()
        self._frame_buffer = b''
        if not self._use_webrtc:
            self._fallback.reset()

    def force_end(self) -> Optional[bytes]:
        """Force end of speech."""
        if self._buffer:
            return self._flush_buffer()
        return None
