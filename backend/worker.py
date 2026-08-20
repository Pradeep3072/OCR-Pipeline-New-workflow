import os
from celery import Celery
from logger import get_logger

logger = get_logger(__name__)

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

from pipeline import main as run_pipeline
from db.session import SessionLocal
from db.models import Document

@celery_app.task(name="process_ocr_task", bind=True)
def process_ocr_task(self, s3_input_key: str, poppler_path: str = None, ground_truth: str = None):
    """
    Background task to run the OCR pipeline.
    """
    logger.info(f"Starting OCR task for {s3_input_key}")
    
    import time
    from ocr.evaluation import calculate_metrics

    db = SessionLocal()
    start_time = time.time()
    
    try:
        # run_pipeline will download from S3, process, and upload results to S3
        results = run_pipeline(s3_input_key, poppler_path=poppler_path)
        logger.info(f"Finished OCR task for {s3_input_key}")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        evaluation_metrics = None
        if ground_truth:
            # Combine all text from results for metrics
            full_pred_text = " ".join([res["result_data"]["text"] for res in results])
            evaluation_metrics = calculate_metrics(full_pred_text, ground_truth)
        
        # Update DB
        doc = db.query(Document).filter(Document.task_id == self.request.id).first()
        if doc:
            doc.status = "SUCCESS"
            doc.result_data = results
            doc.processing_time = processing_time
            doc.evaluation_metrics = evaluation_metrics
            db.commit()
            
        return {
            "results": results,
            "processing_time": processing_time,
            "evaluation_metrics": evaluation_metrics
        }
    except Exception as e:
        doc = db.query(Document).filter(Document.task_id == self.request.id).first()
        if doc:
            doc.status = "FAILED"
            db.commit()
        raise e
    finally:
        db.close()
