import os
from celery import Celery
from main import main as run_pipeline

# Initialize Celery app
# Point to the redis container defined in docker-compose.yml
# We use localhost fallback for local testing without docker
REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "ocr_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(name="process_ocr_task")
def process_ocr_task(s3_input_key: str, poppler_path: str = None):
    """
    Background task to run the OCR pipeline.
    """
    print(f"Starting OCR task for {s3_input_key}")
    # run_pipeline will download from S3, process, and upload results to S3
    results = run_pipeline(s3_input_key, poppler_path=poppler_path)
    print(f"Finished OCR task for {s3_input_key}")
    return results
