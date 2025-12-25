"""
OpenAI TTS synthesis wrapper with caching support.
"""
import asyncio
import hashlib
from typing import Optional, Protocol
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)


class CacheService(Protocol):
    """Protocol for TTS cache service."""

    async def get(self, key: str) -> Optional[bytes]:
        """Get cached audio bytes."""
        ...

    async def set(self, key: str, data: bytes) -> None:
        """Cache audio bytes."""
        ...


class TTSSynthesizer:
    """Synthesize speech using OpenAI TTS API with optional caching."""

    # Available voices
    VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    # Available models
    MODELS = ["tts-1", "tts-1-hd"]

    def __init__(
        self,
        api_key: str,
        voice: str = "nova",
        model: str = "tts-1",
        cache_service: Optional[CacheService] = None,
        output_format: str = "pcm"
    ):
        """
        Initialize TTS synthesizer.

        Args:
            api_key: OpenAI API key
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: TTS model (tts-1 or tts-1-hd)
            cache_service: Optional cache service for caching audio
            output_format: Output format (pcm, mp3, opus, aac, flac)
        """
        if voice not in self.VOICES:
            raise ValueError(f"Invalid voice: {voice}. Must be one of {self.VOICES}")
        if model not in self.MODELS:
            raise ValueError(f"Invalid model: {model}. Must be one of {self.MODELS}")

        self.client = OpenAI(api_key=api_key)
        self.voice = voice
        self.model = model
        self.cache = cache_service
        self.output_format = output_format
        self._total_characters = 0

    @property
    def total_characters_synthesized(self) -> int:
        """Get total characters synthesized for cost tracking."""
        return self._total_characters

    async def synthesize(self, text: str) -> bytes:
        """
        Convert text to speech audio.

        Args:
            text: Text to synthesize

        Returns:
            Audio bytes in the specified format
        """
        if not text or not text.strip():
            return b""

        text = text.strip()

        try:
            # Check cache first
            cache_key = self._get_cache_key(text)
            if self.cache:
                cached = await self.cache.get(cache_key)
                if cached:
                    logger.debug(f"TTS cache hit for: {text[:50]}...")
                    return cached

            # Track characters for cost calculation
            self._total_characters += len(text)

            # Call TTS API
            audio_bytes = await asyncio.to_thread(
                self._call_tts_api,
                text
            )

            # Cache the result
            if self.cache and audio_bytes:
                await self.cache.set(cache_key, audio_bytes)

            return audio_bytes

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return b""

    def _call_tts_api(self, text: str) -> bytes:
        """Make synchronous call to TTS API."""
        response = self.client.audio.speech.create(
            model=self.model,
            voice=self.voice,
            input=text,
            response_format=self.output_format
        )
        return response.content

    def _get_cache_key(self, text: str) -> str:
        """
        Generate cache key from text and voice settings.

        Args:
            text: Text to synthesize

        Returns:
            SHA256 hash as cache key
        """
        key_data = f"{self.model}:{self.voice}:{self.output_format}:{text}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def synthesize_with_ssml(self, ssml: str) -> bytes:
        """
        Synthesize speech from SSML (not directly supported by OpenAI).
        Falls back to plain text synthesis.

        Args:
            ssml: SSML markup

        Returns:
            Audio bytes
        """
        # OpenAI doesn't support SSML, extract plain text
        import re
        plain_text = re.sub(r'<[^>]+>', '', ssml)
        return await self.synthesize(plain_text)

    def reset_stats(self):
        """Reset synthesis statistics."""
        self._total_characters = 0


class InMemoryTTSCache:
    """Simple in-memory cache for TTS audio."""

    def __init__(self, max_size: int = 100):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of entries to cache
        """
        self._cache: dict = {}
        self._max_size = max_size

    async def get(self, key: str) -> Optional[bytes]:
        """Get cached audio bytes."""
        return self._cache.get(key)

    async def set(self, key: str, data: bytes) -> None:
        """Cache audio bytes."""
        # Simple LRU-like behavior: remove oldest if at capacity
        if len(self._cache) >= self._max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = data
