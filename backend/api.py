import os
from dotenv import load_dotenv
load_dotenv()
import hashlib
import base64
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from worker import celery_app, process_ocr_task
from celery.result import AsyncResult
from s3_utils import upload_file_to_s3, get_file_bytes_from_s3
from db.session import get_db, engine
from db.models import Base, Document
from logger import get_logger

logger = get_logger(__name__)

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="OCR Pipeline API", description="Distributed API for OCR Pipeline using Celery")

@app.post("/ocr")
async def process_ocr(
    file: UploadFile = File(...), 
    ground_truth: str = Form(None),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
        
    try:
        # Read the file to calculate hash
        file_bytes = await file.read()
        
        # Calculate SHA256 hash
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        
        # Check database for existing document with this hash
        existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
        
        if existing_doc:
            if existing_doc.status == "SUCCESS":
                # Return cached result immediately
                return JSONResponse(content={
                    "status": "success",
                    "task_id": existing_doc.task_id,
                    "results": existing_doc.result_data,
                    "cached": True
                })
            elif existing_doc.status == "PENDING":
                # It is already being processed, return existing task id
                return JSONResponse(content={
                    "status": "processing",
                    "task_id": existing_doc.task_id,
                    "cached": True
                })
        
        # If not cached or it failed previously, process it again
        file_id = str(uuid.uuid4())
        s3_key = f"uploads/{file_id}{ext}"
        
        # Upload uploaded file to S3
        upload_file_to_s3(file_bytes, s3_key)
            
        # Determine poppler path
        local_poppler = os.path.join(os.path.dirname(__file__), "poppler", "poppler-24.08.0", "Library", "bin")
        poppler_path = local_poppler if os.path.exists(local_poppler) else None
        
        # Send task to Celery
        task = process_ocr_task.delay(s3_key, poppler_path, ground_truth)
        
        # Save to database
        if existing_doc:
            existing_doc.status = "PENDING"
            existing_doc.task_id = task.id
            existing_doc.s3_key = s3_key
            existing_doc.result_data = None
        else:
            new_doc = Document(
                file_hash=file_hash,
                s3_key=s3_key,
                status="PENDING",
                task_id=task.id
            )
            db.add(new_doc)
            
        db.commit()
        
        return JSONResponse(content={"status": "processing", "task_id": task.id, "cached": False})
        
    except Exception as e:
        logger.error(f"Error processing OCR request: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ocr/{task_id}")
async def get_ocr_status(task_id: str, db: Session = Depends(get_db)):
    # First, check database in case Redis dropped the task result
    doc = db.query(Document).filter(Document.task_id == task_id).first()
    
    if doc and doc.status == "SUCCESS":
        # Simulate Celery success structure from DB
        results = doc.result_data
        processing_time = doc.processing_time if hasattr(doc, "processing_time") else None
        evaluation_metrics = doc.evaluation_metrics if hasattr(doc, "evaluation_metrics") else None
        
        if not results:
            return JSONResponse(content={"status": "failed", "detail": "Processing returned no results."})
            
        # Format the response
        response_data = []
        for res in results:
            image_base64 = None
            if "image_s3_key" in res:
                img_bytes = get_file_bytes_from_s3(res["image_s3_key"])
                if img_bytes:
                    image_base64 = base64.b64encode(img_bytes).decode("utf-8")
                    
            response_data.append({
                "page": res["page"],
                "text": res["result_data"]["text"],
                "confidence": res["result_data"]["confidence"],
                "needs_review": res["result_data"]["needs_review"],
                "psm_mode": res["result_data"]["psm_mode"],
                "image_base64": image_base64
            })
            
        return JSONResponse(content={
            "status": "success", 
            "task_id": task_id, 
            "results": response_data,
            "processing_time": processing_time,
            "evaluation_metrics": evaluation_metrics
        })
    elif doc and doc.status == "FAILED":
        return JSONResponse(content={"status": "failed", "task_id": task_id, "error": "Task failed previously."})
    
    # If not finished in DB, fallback to Celery
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.state == "PENDING":
        return JSONResponse(content={"status": "processing", "task_id": task_id})
    elif task_result.state == "FAILURE":
        return JSONResponse(content={"status": "failed", "task_id": task_id, "error": str(task_result.info)})
    elif task_result.state == "SUCCESS":
        task_data = task_result.result
        
        if not task_data or "results" not in task_data:
            return JSONResponse(content={"status": "failed", "detail": "Processing returned no results."})
            
        results = task_data["results"]
        processing_time = task_data.get("processing_time")
        evaluation_metrics = task_data.get("evaluation_metrics")
        
        # Format the response
        response_data = []
        for res in results:
            image_base64 = None
            if "image_s3_key" in res:
                img_bytes = get_file_bytes_from_s3(res["image_s3_key"])
                if img_bytes:
                    image_base64 = base64.b64encode(img_bytes).decode("utf-8")
                    
            response_data.append({
                "page": res["page"],
                "text": res["result_data"]["text"],
                "confidence": res["result_data"]["confidence"],
                "needs_review": res["result_data"]["needs_review"],
                "psm_mode": res["result_data"]["psm_mode"],
                "image_base64": image_base64
            })
            
        return JSONResponse(content={
            "status": "success", 
            "task_id": task_id, 
            "results": response_data,
            "processing_time": processing_time,
            "evaluation_metrics": evaluation_metrics
        })
    else:
        return JSONResponse(content={"status": task_result.state.lower(), "task_id": task_id})

from pydantic import BaseModel

class ChatRequest(BaseModel):
    question: str

class RetrieveRequest(BaseModel):
    query: str

@app.post("/ocr/{task_id}/retrieve")
async def retrieve_document_context(task_id: str, request: RetrieveRequest):
    try:
        from rag import retrieve_context
        contexts = retrieve_context(task_id, request.query)
        return JSONResponse(content={
            "status": "success",
            "task_id": task_id,
            "contexts": contexts
        })
    except Exception as e:
        logger.error(f"Error retrieving context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ocr/{task_id}/chat")
async def chat_with_document(task_id: str, request: ChatRequest):
    try:
        from rag import evaluate_answer
        import httpx
        
        # Forward request to agent_service asynchronously to prevent deadlock
        agent_url = os.getenv("AGENT_SERVICE_URL", "http://agent_service:8001/chat")
        payload = {
            "task_id": task_id,
            "question": request.question
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(agent_url, json=payload, timeout=60.0)
            response.raise_for_status()
            agent_result = response.json()
        
        answer = agent_result.get("answer", "")
        contexts = agent_result.get("contexts", [])
        
        # Evaluate the answer (reusing existing ragas-style evaluation)
        metrics = evaluate_answer(request.question, answer, contexts)
        
        return JSONResponse(content={
            "status": "success", 
            "task_id": task_id, 
            "answer": answer,
            "metrics": metrics
        })
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
