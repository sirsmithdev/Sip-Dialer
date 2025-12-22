"""
Celery application configuration.
"""
import os
import ssl
from celery import Celery
from celery.schedules import crontab

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)

# SSL configuration for DigitalOcean Managed Redis (rediss:// URLs)
broker_use_ssl = None
redis_backend_use_ssl = None

if CELERY_BROKER_URL.startswith("rediss://"):
    # DigitalOcean Managed Redis requires SSL with cert verification disabled
    broker_use_ssl = {
        'ssl_cert_reqs': ssl.CERT_NONE,
        'ssl_check_hostname': False,
    }
    redis_backend_use_ssl = broker_use_ssl

# Also check REDIS_URL for backend SSL
if REDIS_URL.startswith("rediss://"):
    redis_backend_use_ssl = {
        'ssl_cert_reqs': ssl.CERT_NONE,
        'ssl_check_hostname': False,
    }

# Create Celery app
app = Celery(
    "autodialer",
    broker=CELERY_BROKER_URL,
    backend=REDIS_URL,
    include=[
        "workers.tasks.campaign_tasks",
        "workers.tasks.audio_tasks",
        "workers.tasks.email_tasks",
    ]
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
    # SSL for broker and backend
    broker_use_ssl=broker_use_ssl,
    redis_backend_use_ssl=redis_backend_use_ssl,
    # Beat schedule for periodic tasks
    beat_schedule={
        "check-scheduled-campaigns": {
            "task": "workers.tasks.campaign_tasks.check_scheduled_campaigns",
            "schedule": 60.0,  # Every 60 seconds
        },
        "check-campaign-end-times": {
            "task": "workers.tasks.campaign_tasks.check_campaign_end_times",
            "schedule": 60.0,  # Every 60 seconds
        },
        "cleanup-stale-calls": {
            "task": "workers.tasks.campaign_tasks.cleanup_stale_calls",
            "schedule": 300.0,  # Every 5 minutes
        },
        "process-scheduled-reports": {
            "task": "workers.tasks.email_tasks.process_scheduled_reports",
            "schedule": 3600.0,  # Every hour
        },
        "send-daily-summaries": {
            "task": "workers.tasks.email_tasks.send_daily_summary",
            "schedule": crontab(hour=8, minute=0),  # 8:00 AM daily
        },
    },
)

if __name__ == "__main__":
    app.start()
