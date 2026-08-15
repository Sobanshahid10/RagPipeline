from celery import Celery
from app.config import settings

celery_app = Celery(
    "rag_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.tasks.high_priority.*": {"queue": "high_priority"},
        "app.tasks.low_priority.*": {"queue": "low_priority"},
    },
)
