"""
Celery Application Configuration

This module configures Celery for async task processing.
Celery allows you to offload heavy operations (like form submissions,
report generation, AI processing) to background workers.
"""

from celery import Celery
from celery.schedules import crontab
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "flowform_ai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.form_tasks",
        "app.tasks.agent_tasks",
        "app.tasks.report_tasks",
        "app.tasks.maintenance_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
    },

    # Task routing
    task_routes={
        "app.tasks.form_tasks.*": {"queue": "forms"},
        "app.tasks.agent_tasks.*": {"queue": "agents"},
        "app.tasks.report_tasks.*": {"queue": "reports"},
        "app.tasks.maintenance_tasks.*": {"queue": "default"},
    },

    # Worker settings
    worker_prefetch_multiplier=1,  # Fetch one task at a time
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks

    # Task execution settings
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Reject if worker dies
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit

    # Retry settings
    task_default_retry_delay=60,  # Retry after 60 seconds
    task_max_retries=3,

    # Beat schedule (periodic tasks)
    beat_schedule={
        # Cleanup expired sessions daily at 2 AM
        "cleanup-sessions-daily": {
            "task": "app.tasks.maintenance_tasks.cleanup_expired_sessions",
            "schedule": crontab(hour=2, minute=0),
        },
        # Generate daily analytics at 3 AM
        "daily-analytics": {
            "task": "app.tasks.report_tasks.generate_daily_analytics",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)

logger.info("Celery app configured successfully")


# Helper function to get celery app instance
def get_celery_app():
    """Get configured Celery app instance"""
    return celery_app
