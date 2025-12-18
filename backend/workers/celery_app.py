"""
Celery application configuration.
"""
import os
from celery import Celery

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
app = Celery(
    "autodialer",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["workers.tasks.campaign_tasks", "workers.tasks.audio_tasks"]
)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Beat schedule for periodic tasks
    beat_schedule={
        "check-scheduled-campaigns": {
            "task": "workers.tasks.campaign_tasks.check_scheduled_campaigns",
            "schedule": 60.0,  # Every 60 seconds
        },
        "cleanup-stale-calls": {
            "task": "workers.tasks.campaign_tasks.cleanup_stale_calls",
            "schedule": 300.0,  # Every 5 minutes
        },
    },
)

if __name__ == "__main__":
    app.start()
