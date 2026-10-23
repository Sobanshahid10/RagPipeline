"""
Celery Application Module.

Configures Celery distributed task worker connected to Redis broker/backend
with routing configurations for high_priority and low_priority queues.
"""

from celery import Celery
from app.config import settings

celery_app = Celery(
    "rag_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.ingestion.pipeline",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.ingestion.pipeline.process_document": {"queue": "high_priority"},
        "app.tasks.high_priority.*": {"queue": "high_priority"},
        "app.tasks.low_priority.*": {"queue": "low_priority"},
        "evaluation.hard_negative_miner.*": {"queue": "low_priority"},
    },
    # Tenant interactions must never be copied into a shared/public evaluation dataset automatically.
    beat_schedule={},
)
