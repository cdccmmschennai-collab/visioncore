"""Celery application configuration.

Redis is used as the broker and result backend. The API only enqueues jobs;
Celery workers perform the long-running Claude extraction and Excel work.
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "visioncore",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
    include=["worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_soft_time_limit=15 * 60,
    task_time_limit=20 * 60,
    result_expires=3600,
)
