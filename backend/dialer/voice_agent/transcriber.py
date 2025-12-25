"""
OpenAI Whisper transcription wrapper.
"""
import asyncio
import wave
import struct
from io import BytesIO
from typing import Optional
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Transcribe audio using OpenAI Whisper API."""

    def __init__(
        self,
        api_key: str,
        model: str = "whisper-1",
        language: str = "en"
    ):
        """
        Initialize Whisper transcriber.

        Args:
            api_key: OpenAI API key
            model: Whisper model to use
            language: Language code for transcription
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.language = language
        self._total_seconds = 0.0

    @property
    def total_seconds_transcribed(self) -> float:
        """Get total audio seconds transcribed for cost tracking."""
        return self._total_seconds

    async def transcribe(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        sample_width: int = 2,
        channels: int = 1
    ) -> str:
        """
        Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw PCM audio data
            sample_rate: Audio sample rate (default 16000 Hz)
            sample_width: Bytes per sample (default 2 for 16-bit)
            channels: Number of audio channels (default 1 for mono)

        Returns:
            Transcribed text
        """
        if not audio_bytes:
            return ""

        try:
            # Convert to WAV format for Whisper API
            wav_buffer = self._pcm_to_wav(
                audio_bytes, sample_rate, sample_width, channels
            )

            # Track duration for cost calculation
            duration_seconds = len(audio_bytes) / (sample_rate * sample_width * channels)
            self._total_seconds += duration_seconds

            # Call Whisper API in thread pool
            response = await asyncio.to_thread(
                self._call_whisper_api,
                wav_buffer
            )

            return response.text.strip()

        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return ""

    def _call_whisper_api(self, wav_buffer: BytesIO) -> object:
        """Make synchronous call to Whisper API."""
        return self.client.audio.transcriptions.create(
            model=self.model,
            file=("audio.wav", wav_buffer, "audio/wav"),
            language=self.language,
            response_format="text"
        )

    def _pcm_to_wav(
        self,
        pcm_bytes: bytes,
        sample_rate: int,
        sample_width: int,
        channels: int
    ) -> BytesIO:
        """
        Convert raw PCM audio to WAV format.

        Args:
            pcm_bytes: Raw PCM audio data
            sample_rate: Audio sample rate
            sample_width: Bytes per sample
            channels: Number of audio channels

        Returns:
            BytesIO containing WAV data
        """
        buffer = BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(sample_width)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm_bytes)
        buffer.seek(0)
        return buffer

    def reset_stats(self):
        """Reset transcription statistics."""
        self._total_seconds = 0.0
