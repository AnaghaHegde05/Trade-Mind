from celery import Celery
from backend.config.settings import settings

celery_app = Celery(
    "trade_intel",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["backend.orchestrator.tasks"]
)

# Standard celery configuration options
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600, # 1 hour timeout
)
