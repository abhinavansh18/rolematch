from celery import Celery
from shared.config.settings import get_settings

settings = get_settings()

celery = Celery(
    "jobmatch-workers",
    broker=settings.redis_url.replace("/0", "/4"),   # Use DB 4 for Celery broker
    backend=settings.redis_url.replace("/0", "/4"),
    include=[
        "app.tasks.notification_tasks",
        "app.tasks.cache_warming_tasks",
    ],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.cache_warming_tasks.*": {"queue": "cache"},
    },
    beat_schedule={
        "warm-top-job-cache": {
            "task": "app.tasks.cache_warming_tasks.warm_top_jobs_cache",
            "schedule": 900.0,  # Every 15 minutes
        },
    },
)
