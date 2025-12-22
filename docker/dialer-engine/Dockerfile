# =============================================================================
# Dialer Engine Dockerfile with PJSIP/PJSUA2 Support
# =============================================================================
# This container runs the SIP auto-dialer engine that registers with
# Grandstream UCM as a PJSIP extension and handles outbound calling.
#
# PJSIP provides full SIP stack with:
# - SIP registration with digest authentication
# - TLS 1.2+ support for secure SIP
# - RTP media handling for audio playback
# - DTMF detection (RFC 2833)
# - Full codec support (G.711, G.722, etc.)
# =============================================================================

FROM python:3.11-slim AS builder

# Install build dependencies for PJSIP
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    make \
    autoconf \
    automake \
    libtool \
    pkg-config \
    git \
    wget \
    libssl-dev \
    libasound2-dev \
    libspeex-dev \
    libspeexdsp-dev \
    libopus-dev \
    libsndfile1-dev \
    swig \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Build PJSIP from source
WORKDIR /build

# Download PJSIP source (version 2.14.1)
RUN wget -q https://github.com/pjsip/pjproject/archive/refs/tags/2.14.1.tar.gz \
    && tar xzf 2.14.1.tar.gz \
    && rm 2.14.1.tar.gz

WORKDIR /build/pjproject-2.14.1

# Configure PJSIP with Python bindings and TLS support
RUN ./configure \
    --enable-shared \
    --with-external-speex \
    --with-external-opus \
    --disable-video \
    --disable-v4l2 \
    --disable-opencore-amr \
    --with-ssl=/usr \
    CFLAGS="-O2 -fPIC" \
    && make dep \
    && make -j$(nproc) \
    && make install

# Build Python SWIG bindings
WORKDIR /build/pjproject-2.14.1/pjsip-apps/src/swig/python

RUN make \
    && python setup.py build \
    && python setup.py install

# =============================================================================
# Runtime Stage
# =============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (including ca-certificates for TLS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libssl3 \
    libasound2 \
    libspeex1 \
    libspeexdsp1 \
    libopus0 \
    libsndfile1 \
    libgsm1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy PJSIP libraries from builder (including all .so files)
COPY --from=builder /usr/local/lib/*.so* /usr/local/lib/
COPY --from=builder /usr/local/lib/python3.11/site-packages/pjsua2* /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/lib/python3.11/site-packages/_pjsua2* /usr/local/lib/python3.11/site-packages/

# Update library cache
RUN ldconfig

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Create audio directory for local cache
RUN mkdir -p /var/lib/autodialer/audio && chown -R appuser:appuser /var/lib/autodialer

USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV AUDIO_BASE_PATH=/var/lib/autodialer/audio

# Note: DO App Platform workers don't need EXPOSE - they don't receive inbound traffic
# The dialer makes outbound SIP/RTP connections only

# Health check - verify Python can import pjsua2
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import pjsua2; print('PJSUA2 OK')" || exit 1

# Run the dialer engine
CMD ["python", "-m", "dialer.main"]
