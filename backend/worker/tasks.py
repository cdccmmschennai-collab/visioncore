"""Celery tasks for Visioncore background processing."""
from __future__ import annotations

import asyncio
import logging

from app.services.pipeline import process_batch
from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="visioncore.process_batch",
    max_retries=3,
    default_retry_delay=15,
)
def process_batch_task(self, batch_id: int, user_id: int) -> dict:
    """Run one uploaded batch outside the FastAPI web process.

    A worker/process failure is retried. Per-tag extraction failures are
    handled by the existing pipeline and remain visible as FAILED items.
    """
    try:
        asyncio.run(process_batch(batch_id, user_id))
        return {"batch_id": batch_id, "status": "processed"}
    except Exception as exc:  # noqa: BLE001 - let Celery retry infrastructure handle it
        logger.exception("Batch %s failed in Celery worker", batch_id)
        raise self.retry(exc=exc, countdown=15 * (2 ** self.request.retries)) from exc
