FROM python:3.11-slim

# Cache buster - change this value to force rebuild
ARG CACHE_BUST=20251222_v1

WORKDIR /app

# Install system dependencies including FFmpeg for audio transcoding
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set PYTHONPATH to include the app directory
ENV PYTHONPATH=/app

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Default command (overridden in docker-compose)
CMD ["celery", "-A", "workers.celery_app", "worker", "--loglevel=info"]
