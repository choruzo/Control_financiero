"""
Instancia de la aplicación Celery con configuración del beat schedule.

El worker se lanza con:
    celery -A app.tasks worker --loglevel=info

El scheduler se lanza con:
    celery -A app.tasks beat --loglevel=info
"""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "fincontrol",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.ml_retraining"],
)

celery_app.conf.timezone = "Europe/Madrid"
celery_app.conf.enable_utc = True

celery_app.conf.beat_schedule = {
    "retrain-ml-weekly": {
        "task": "app.tasks.ml_retraining.trigger_ml_retrain",
        "schedule": crontab(
            hour=settings.ml_retrain_schedule_hour,
            day_of_week=settings.ml_retrain_schedule_day_of_week,
        ),
    },
}
