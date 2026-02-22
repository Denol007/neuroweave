"""Celery application instance.

Usage:
    celery -A api.celery_app worker --loglevel=info
"""

from celery import Celery

from api.config import settings

app = Celery(
    "neuroweave",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "api.tasks.process_messages.*": {"queue": "extraction"},
        "api.tasks.generate_article.*": {"queue": "extraction"},
        "api.tasks.export_dataset.*": {"queue": "export"},
    },
)

app.autodiscover_tasks(["api.tasks"])

# Explicit imports to ensure tasks are always registered
import api.tasks.process_messages  # noqa: F401, E402
import api.tasks.generate_article  # noqa: F401, E402
import api.tasks.export_dataset  # noqa: F401, E402
