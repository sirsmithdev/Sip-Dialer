"""
Audio format conversion utilities.
"""
import struct
import wave
from io import BytesIO
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

# G.711 u-law encoding/decoding tables
ULAW_BIAS = 0x84
ULAW_CLIP = 32635

# Pre-computed u-law to linear table
ULAW_TO_LINEAR = []
for i in range(256):
    # Complement the bits
    sample = ~i
    sign = sample & 0x80
    exponent = (sample & 0x70) >> 4
    mantissa = sample & 0x0F
    linear = ((mantissa << 3) + ULAW_BIAS) << exponent
    linear -= ULAW_BIAS
    if sign:
        linear = -linear
    ULAW_TO_LINEAR.append(linear)


def ulaw_to_linear(ulaw_byte: int) -> int:
    """Convert single u-law byte to linear 16-bit sample."""
    return ULAW_TO_LINEAR[ulaw_byte]


def linear_to_ulaw(sample: int) -> int:
    """Convert linear 16-bit sample to u-law byte."""
    # Get sign
    sign = 0
    if sample < 0:
        sign = 0x80
        sample = -sample

    # Clip
    if sample > ULAW_CLIP:
        sample = ULAW_CLIP

    # Add bias
    sample += ULAW_BIAS

    # Find exponent and mantissa
    exponent = 7
    exp_mask = 0x4000
    while exponent > 0:
        if sample & exp_mask:
            break
        exponent -= 1
        exp_mask >>= 1

    mantissa = (sample >> (exponent + 3)) & 0x0F
    ulaw_byte = ~(sign | (exponent << 4) | mantissa) & 0xFF

    return ulaw_byte


def ulaw_to_pcm16(ulaw_bytes: bytes) -> bytes:
    """
    Convert u-law encoded audio to 16-bit PCM.

    Args:
        ulaw_bytes: u-law encoded audio data

    Returns:
        16-bit PCM audio data
    """
    samples = []
    for byte in ulaw_bytes:
        samples.append(ulaw_to_linear(byte))
    return struct.pack(f'{len(samples)}h', *samples)


def pcm16_to_ulaw(pcm_bytes: bytes) -> bytes:
    """
    Convert 16-bit PCM audio to u-law encoding.

    Args:
        pcm_bytes: 16-bit PCM audio data

    Returns:
        u-law encoded audio data
    """
    num_samples = len(pcm_bytes) // 2
    samples = struct.unpack(f'{num_samples}h', pcm_bytes)
    ulaw_bytes = bytes([linear_to_ulaw(s) for s in samples])
    return ulaw_bytes


def resample(
    audio_bytes: bytes,
    from_rate: int,
    to_rate: int,
    sample_width: int = 2
) -> bytes:
    """
    Simple linear interpolation resampling.

    Args:
        audio_bytes: Input audio data
        from_rate: Source sample rate
        to_rate: Target sample rate
        sample_width: Bytes per sample (2 for 16-bit)

    Returns:
        Resampled audio data
    """
    if from_rate == to_rate:
        return audio_bytes

    # Unpack samples
    num_samples = len(audio_bytes) // sample_width
    if sample_width == 2:
        samples = list(struct.unpack(f'{num_samples}h', audio_bytes))
    elif sample_width == 1:
        samples = list(audio_bytes)
    else:
        raise ValueError(f"Unsupported sample width: {sample_width}")

    # Calculate new length
    ratio = to_rate / from_rate
    new_length = int(len(samples) * ratio)

    # Linear interpolation
    resampled = []
    for i in range(new_length):
        src_pos = i / ratio
        src_idx = int(src_pos)
        frac = src_pos - src_idx

        if src_idx + 1 < len(samples):
            sample = int(samples[src_idx] * (1 - frac) + samples[src_idx + 1] * frac)
        else:
            sample = samples[src_idx] if src_idx < len(samples) else 0

        resampled.append(sample)

    # Pack samples
    if sample_width == 2:
        return struct.pack(f'{len(resampled)}h', *resampled)
    else:
        return bytes(resampled)


def convert_for_whisper(
    audio_bytes: bytes,
    source_format: str = "ulaw",
    source_rate: int = 8000
) -> Tuple[bytes, int]:
    """
    Convert audio to format suitable for Whisper API.

    Whisper works best with 16kHz 16-bit mono PCM.

    Args:
        audio_bytes: Input audio data
        source_format: Source format ("ulaw", "alaw", "pcm16", "pcm8")
        source_rate: Source sample rate

    Returns:
        Tuple of (converted audio bytes, sample rate)
    """
    # Convert to PCM16 if needed
    if source_format == "ulaw":
        pcm_bytes = ulaw_to_pcm16(audio_bytes)
    elif source_format == "alaw":
        # A-law conversion (simplified - for proper implementation use audioop)
        pcm_bytes = alaw_to_pcm16(audio_bytes)
    elif source_format == "pcm16":
        pcm_bytes = audio_bytes
    elif source_format == "pcm8":
        # Convert 8-bit to 16-bit
        samples = [(b - 128) * 256 for b in audio_bytes]
        pcm_bytes = struct.pack(f'{len(samples)}h', *samples)
    else:
        raise ValueError(f"Unsupported source format: {source_format}")

    # Resample to 16kHz if needed
    target_rate = 16000
    if source_rate != target_rate:
        pcm_bytes = resample(pcm_bytes, source_rate, target_rate, 2)

    return pcm_bytes, target_rate


def convert_from_tts(
    audio_bytes: bytes,
    source_format: str = "pcm",
    target_format: str = "ulaw",
    target_rate: int = 8000
) -> bytes:
    """
    Convert TTS output to telephony format.

    OpenAI TTS returns 24kHz PCM.

    Args:
        audio_bytes: TTS audio data
        source_format: TTS output format
        target_format: Target format for telephony
        target_rate: Target sample rate

    Returns:
        Converted audio bytes
    """
    source_rate = 24000  # OpenAI TTS default

    # Resample to target rate
    if source_rate != target_rate:
        audio_bytes = resample(audio_bytes, source_rate, target_rate, 2)

    # Convert format
    if target_format == "ulaw":
        return pcm16_to_ulaw(audio_bytes)
    elif target_format == "pcm16":
        return audio_bytes
    else:
        raise ValueError(f"Unsupported target format: {target_format}")


def pcm_to_wav(
    pcm_bytes: bytes,
    sample_rate: int = 16000,
    sample_width: int = 2,
    channels: int = 1
) -> bytes:
    """
    Convert raw PCM to WAV format.

    Args:
        pcm_bytes: Raw PCM audio data
        sample_rate: Sample rate in Hz
        sample_width: Bytes per sample
        channels: Number of channels

    Returns:
        WAV file bytes
    """
    buffer = BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_bytes)
    return buffer.getvalue()


def wav_to_pcm(wav_bytes: bytes) -> Tuple[bytes, int, int, int]:
    """
    Extract PCM data from WAV file.

    Args:
        wav_bytes: WAV file bytes

    Returns:
        Tuple of (pcm_bytes, sample_rate, sample_width, channels)
    """
    buffer = BytesIO(wav_bytes)
    with wave.open(buffer, 'rb') as wav:
        sample_rate = wav.getframerate()
        sample_width = wav.getsampwidth()
        channels = wav.getnchannels()
        pcm_bytes = wav.readframes(wav.getnframes())
    return pcm_bytes, sample_rate, sample_width, channels


# A-law tables (simplified)
ALAW_TO_LINEAR = []
for i in range(256):
    sample = i ^ 0x55
    sign = sample & 0x80
    exponent = (sample & 0x70) >> 4
    mantissa = sample & 0x0F
    if exponent:
        linear = ((mantissa << 4) + 0x108) << (exponent - 1)
    else:
        linear = (mantissa << 4) + 8
    if sign:
        linear = -linear
    ALAW_TO_LINEAR.append(linear)


def alaw_to_pcm16(alaw_bytes: bytes) -> bytes:
    """Convert A-law to 16-bit PCM."""
    samples = [ALAW_TO_LINEAR[b] for b in alaw_bytes]
    return struct.pack(f'{len(samples)}h', *samples)
