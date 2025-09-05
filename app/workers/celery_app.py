from celery import Celery
from app.config.settings import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "docx_converter",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=['app.workers.tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
)

# Task routing removed - using default queue for simplicity
# celery_app.conf.task_routes = {
#     'app.workers.tasks.convert_docx_to_pdf': {'queue': 'conversion'},
#     'app.workers.tasks.process_conversion_job': {'queue': 'job_processing'},
#     'app.workers.tasks.create_final_archive': {'queue': 'archiving'},
# }

logger.info("Celery app configured successfully")
