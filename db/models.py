from sqlalchemy import Column, String, JSON, DateTime, Float
from sqlalchemy.sql import func
from .session import Base

class Document(Base):
    __tablename__ = "documents"

    # SHA-256 hash of the uploaded file
    file_hash = Column(String, primary_key=True, index=True)
    
    # Store the s3 key where the raw file is saved
    s3_key = Column(String, nullable=False)
    
    # Status of processing (PENDING, SUCCESS, FAILED)
    status = Column(String, default="PENDING")
    
    # Store the celery task id handling this document if it's pending
    task_id = Column(String, nullable=True)
    
    # Store the final OCR JSON results
    result_data = Column(JSON, nullable=True)
    
    # Store the processing time in seconds
    processing_time = Column(Float, nullable=True)
    
    # Store evaluation metrics if testing phase
    evaluation_metrics = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
