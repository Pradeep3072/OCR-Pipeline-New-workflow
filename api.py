import os
import shutil
import base64
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from worker import celery_app, process_ocr_task
from celery.result import AsyncResult
from s3_utils import upload_file_to_s3, get_file_bytes_from_s3

app = FastAPI(title="OCR Pipeline API", description="Distributed API for OCR Pipeline using Celery")

# Local shared dir is no longer needed since we use S3

@app.post("/ocr")
async def process_ocr(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
        
    file_id = str(uuid.uuid4())
    s3_key = f"uploads/{file_id}{ext}"
    
    try:
        # Upload uploaded file to S3
        upload_file_to_s3(file.file, s3_key)
            
        # Determine poppler path
        local_poppler = os.path.join(os.path.dirname(__file__), "poppler", "poppler-24.08.0", "Library", "bin")
        poppler_path = local_poppler if os.path.exists(local_poppler) else None
        
        # Send task to Celery
        task = process_ocr_task.delay(s3_key, poppler_path)
        
        return JSONResponse(content={"status": "processing", "task_id": task.id})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ocr/{task_id}")
async def get_ocr_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.state == "PENDING":
        return JSONResponse(content={"status": "processing", "task_id": task_id})
    elif task_result.state == "FAILURE":
        return JSONResponse(content={"status": "failed", "task_id": task_id, "error": str(task_result.info)})
    elif task_result.state == "SUCCESS":
        results = task_result.result
        
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
            
        return JSONResponse(content={"status": "success", "task_id": task_id, "results": response_data})
    else:
        return JSONResponse(content={"status": task_result.state.lower(), "task_id": task_id})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
