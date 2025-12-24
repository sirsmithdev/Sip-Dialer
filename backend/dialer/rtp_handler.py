"""
RTP (Real-time Transport Protocol) Handler.

Implements RFC 3550 for audio streaming over UDP.
"""
import asyncio
import logging
import random
import socket
import struct
import time
from dataclasses import dataclass
from typing import Optional, Callable

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RTPPacket:
    """RTP packet structure (RFC 3550)."""
    version: int = 2  # RTP version (always 2)
    padding: bool = False
    extension: bool = False
    csrc_count: int = 0
    marker: bool = False
    payload_type: int = 0  # 0=PCMU, 8=PCMA, 9=G722
    sequence_number: int = 0
    timestamp: int = 0
    ssrc: int = 0  # Synchronization source identifier
    payload: bytes = b""

    def to_bytes(self) -> bytes:
        """Serialize RTP packet to bytes."""
        # Byte 0: V(2), P(1), X(1), CC(4)
        byte0 = (self.version << 6) | (int(self.padding) << 5) | \
                (int(self.extension) << 4) | (self.csrc_count & 0x0F)

        # Byte 1: M(1), PT(7)
        byte1 = (int(self.marker) << 7) | (self.payload_type & 0x7F)

        # Pack fixed header (12 bytes)
        header = struct.pack(
            '!BBHII',
            byte0,
            byte1,
            self.sequence_number & 0xFFFF,
            self.timestamp & 0xFFFFFFFF,
            self.ssrc & 0xFFFFFFFF
        )

        return header + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> Optional['RTPPacket']:
        """Parse RTP packet from bytes."""
        if len(data) < 12:
            return None

        # Unpack fixed header
        byte0, byte1, seq, ts, ssrc = struct.unpack('!BBHII', data[:12])

        packet = cls()
        packet.version = (byte0 >> 6) & 0x03
        packet.padding = bool((byte0 >> 5) & 0x01)
        packet.extension = bool((byte0 >> 4) & 0x01)
        packet.csrc_count = byte0 & 0x0F
        packet.marker = bool((byte1 >> 7) & 0x01)
        packet.payload_type = byte1 & 0x7F
        packet.sequence_number = seq
        packet.timestamp = ts
        packet.ssrc = ssrc

        # Extract payload (skip CSRC if present)
        header_len = 12 + (packet.csrc_count * 4)
        if len(data) > header_len:
            packet.payload = data[header_len:]

        return packet


class RTPSession:
    """
    RTP session for audio streaming.

    Handles:
    - Packet encoding/decoding
    - Sequence number management
    - Timestamp calculation
    - SSRC generation
    """

    def __init__(
        self,
        local_ip: str,
        local_port: int,
        payload_type: int = 0,  # 0=PCMU (G.711 μ-law)
        sample_rate: int = 8000,  # 8kHz for G.711
        ptime: int = 20  # Packetization time in ms
    ):
        self.local_ip = local_ip
        self.local_port = local_port
        self.payload_type = payload_type
        self.sample_rate = sample_rate
        self.ptime = ptime  # milliseconds

        # RTP state
        self.ssrc = random.randint(0, 0xFFFFFFFF)
        self.sequence_number = random.randint(0, 0xFFFF)
        self.timestamp = random.randint(0, 0xFFFFFFFF)
        self.timestamp_increment = int(sample_rate * ptime / 1000)  # 160 for 20ms @ 8kHz

        # Remote endpoint
        self.remote_ip: Optional[str] = None
        self.remote_port: Optional[int] = None

        # Socket
        self.socket: Optional[socket.socket] = None
        self.running = False

        # Callbacks
        self.on_audio_received: Optional[Callable[[bytes], None]] = None

        # Statistics
        self.packets_sent = 0
        self.packets_received = 0
        self.bytes_sent = 0
        self.bytes_received = 0

    async def start(self):
        """Start RTP session."""
        logger.info(f"Starting RTP session on {self.local_ip}:{self.local_port}")

        # Create UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.local_ip, self.local_port))
        self.socket.setblocking(False)

        self.running = True

        # Start receive loop
        asyncio.create_task(self._receive_loop())

        logger.info(f"RTP session started (SSRC={self.ssrc:08x})")

    async def stop(self):
        """Stop RTP session."""
        logger.info("Stopping RTP session")
        self.running = False

        if self.socket:
            self.socket.close()
            self.socket = None

        logger.info(f"RTP session stopped (sent={self.packets_sent}, received={self.packets_received})")

    def set_remote(self, ip: str, port: int):
        """Set remote RTP endpoint."""
        self.remote_ip = ip
        self.remote_port = port
        logger.info(f"RTP remote endpoint set to {ip}:{port}")

    async def send_audio(self, audio_data: bytes, marker: bool = False):
        """
        Send audio data as RTP packet.

        Args:
            audio_data: Audio payload (G.711 encoded)
            marker: RTP marker bit (True for first packet after silence)
        """
        if not self.socket or not self.remote_ip or not self.remote_port:
            logger.warning("Cannot send RTP: socket or remote not configured")
            return

        # Create RTP packet
        packet = RTPPacket(
            version=2,
            payload_type=self.payload_type,
            sequence_number=self.sequence_number,
            timestamp=self.timestamp,
            ssrc=self.ssrc,
            marker=marker,
            payload=audio_data
        )

        # Send packet
        packet_bytes = packet.to_bytes()
        try:
            self.socket.sendto(packet_bytes, (self.remote_ip, self.remote_port))

            # Update state
            self.sequence_number = (self.sequence_number + 1) & 0xFFFF
            self.timestamp = (self.timestamp + self.timestamp_increment) & 0xFFFFFFFF
            self.packets_sent += 1
            self.bytes_sent += len(packet_bytes)

        except Exception as e:
            logger.error(f"Error sending RTP packet: {e}")

    async def _receive_loop(self):
        """Receive loop for incoming RTP packets."""
        logger.debug("RTP receive loop started")

        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)

                # Parse RTP packet
                packet = RTPPacket.from_bytes(data)
                if packet:
                    self.packets_received += 1
                    self.bytes_received += len(data)

                    # Invoke callback with audio payload
                    if self.on_audio_received and packet.payload:
                        self.on_audio_received(packet.payload)

            except BlockingIOError:
                await asyncio.sleep(0.001)  # 1ms
            except Exception as e:
                logger.error(f"Error in RTP receive loop: {e}")
                await asyncio.sleep(0.1)

        logger.debug("RTP receive loop ended")

    def get_stats(self) -> dict:
        """Get RTP session statistics."""
        return {
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'ssrc': f"{self.ssrc:08x}",
            'current_seq': self.sequence_number,
            'current_ts': self.timestamp
        }


class G711Codec:
    """
    G.711 μ-law codec encoder/decoder.

    Converts between linear PCM and μ-law compressed audio.
    """

    # μ-law compression/expansion tables (precomputed)
    ULAW_MAX = 0x7FFF  # Maximum 16-bit PCM value
    ULAW_BIAS = 0x84

    @staticmethod
    def encode_sample(sample: int) -> int:
        """
        Encode single 16-bit linear PCM sample to μ-law.

        Args:
            sample: 16-bit signed PCM sample (-32768 to 32767)

        Returns:
            8-bit μ-law encoded value (0-255)
        """
        # Get sign and magnitude
        sign = 0 if sample >= 0 else 1
        magnitude = abs(sample)

        # Clip to max
        if magnitude > G711Codec.ULAW_MAX:
            magnitude = G711Codec.ULAW_MAX

        # Add bias
        magnitude += G711Codec.ULAW_BIAS

        # Find segment
        if magnitude >= 0x8000:
            segment = 7
        elif magnitude >= 0x4000:
            segment = 6
        elif magnitude >= 0x2000:
            segment = 5
        elif magnitude >= 0x1000:
            segment = 4
        elif magnitude >= 0x800:
            segment = 3
        elif magnitude >= 0x400:
            segment = 2
        elif magnitude >= 0x200:
            segment = 1
        else:
            segment = 0

        # Quantize
        shift = segment + 3
        quantized = (magnitude >> shift) & 0x0F

        # Compose μ-law byte
        ulaw = (sign << 7) | (segment << 4) | (0x0F - quantized)

        # Complement for transmission
        return ulaw ^ 0xFF

    @staticmethod
    def decode_sample(ulaw: int) -> int:
        """
        Decode μ-law byte to 16-bit linear PCM.

        Args:
            ulaw: 8-bit μ-law encoded value (0-255)

        Returns:
            16-bit signed PCM sample
        """
        # Complement
        ulaw = (~ulaw) & 0xFF

        # Extract fields
        sign = (ulaw >> 7) & 0x01
        segment = (ulaw >> 4) & 0x07
        quantized = ulaw & 0x0F

        # Calculate value
        value = ((quantized << 1) | 1) << (segment + 2)
        value -= G711Codec.ULAW_BIAS

        # Apply sign
        return -value if sign else value

    @classmethod
    def encode(cls, pcm_data: bytes) -> bytes:
        """
        Encode 16-bit PCM to μ-law.

        Args:
            pcm_data: Raw 16-bit signed PCM audio (little-endian)

        Returns:
            μ-law encoded audio (8-bit per sample)
        """
        # Convert bytes to 16-bit samples
        samples = np.frombuffer(pcm_data, dtype=np.int16)

        # Encode each sample
        ulaw_samples = np.array([cls.encode_sample(int(s)) for s in samples], dtype=np.uint8)

        return ulaw_samples.tobytes()

    @classmethod
    def decode(cls, ulaw_data: bytes) -> bytes:
        """
        Decode μ-law to 16-bit PCM.

        Args:
            ulaw_data: μ-law encoded audio

        Returns:
            Raw 16-bit signed PCM audio
        """
        # Convert bytes to samples
        ulaw_samples = np.frombuffer(ulaw_data, dtype=np.uint8)

        # Decode each sample
        pcm_samples = np.array([cls.decode_sample(int(u)) for u in ulaw_samples], dtype=np.int16)

        return pcm_samples.tobytes()


class AudioBuffer:
    """
    Circular buffer for audio data with jitter compensation.
    """

    def __init__(self, size_ms: int = 200, sample_rate: int = 8000):
        """
        Initialize audio buffer.

        Args:
            size_ms: Buffer size in milliseconds
            sample_rate: Audio sample rate (Hz)
        """
        self.sample_rate = sample_rate
        self.samples_per_ms = sample_rate // 1000

        # Buffer size in bytes (16-bit PCM)
        self.max_samples = size_ms * self.samples_per_ms
        self.buffer = np.zeros(self.max_samples, dtype=np.int16)

        # Read/write pointers
        self.write_pos = 0
        self.read_pos = 0
        self.available = 0

    def write(self, data: bytes):
        """Write audio data to buffer."""
        samples = np.frombuffer(data, dtype=np.int16)
        num_samples = len(samples)

        # Calculate write positions
        end_pos = (self.write_pos + num_samples) % self.max_samples

        if end_pos > self.write_pos:
            # No wrap
            self.buffer[self.write_pos:end_pos] = samples
        else:
            # Wrap around
            first_chunk = self.max_samples - self.write_pos
            self.buffer[self.write_pos:] = samples[:first_chunk]
            self.buffer[:end_pos] = samples[first_chunk:]

        self.write_pos = end_pos
        self.available = min(self.available + num_samples, self.max_samples)

    def read(self, num_samples: int) -> Optional[bytes]:
        """Read audio data from buffer."""
        if self.available < num_samples:
            return None  # Not enough data

        # Calculate read positions
        end_pos = (self.read_pos + num_samples) % self.max_samples

        if end_pos > self.read_pos:
            # No wrap
            samples = self.buffer[self.read_pos:end_pos]
        else:
            # Wrap around
            first_chunk = self.max_samples - self.read_pos
            samples = np.concatenate([
                self.buffer[self.read_pos:],
                self.buffer[:end_pos]
            ])

        self.read_pos = end_pos
        self.available -= num_samples

        return samples.tobytes()

    def clear(self):
        """Clear buffer."""
        self.buffer.fill(0)
        self.write_pos = 0
        self.read_pos = 0
        self.available = 0
