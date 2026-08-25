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
        "evaluation.hard_negative_miner",
    ]
)

celery_app.conf.update(
    task_serializer="json",
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
    beat_schedule={
        "mine-hard-negatives-every-6-hours": {
            "task": "evaluation.hard_negative_miner.mine_hard_negatives",
            "schedule": 21600.0,  # 6 hours in seconds
            "args": (6, "evaluation/golden_dataset.json"),
        },
    },
)

