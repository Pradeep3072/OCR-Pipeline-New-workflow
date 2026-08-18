import os
import tempfile
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import base64
from main import main as run_pipeline

app = FastAPI(title="OCR Pipeline API", description="API for OCR Pipeline using Tesseract and Dynamic PSM")

@app.post("/ocr")
async def process_ocr(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
        
    temp_dir = tempfile.mkdtemp()
    input_path = os.path.join(temp_dir, file.filename)
    
    try:
        # Save uploaded file
        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        output_dir = os.path.join(temp_dir, "output")
        
        # Determine poppler path (use local windows binary if running locally, otherwise None for Docker)
        local_poppler = os.path.join(os.path.dirname(__file__), "poppler", "poppler-24.08.0", "Library", "bin")
        poppler_path = local_poppler if os.path.exists(local_poppler) else None
        
        # Run OCR pipeline
        results = run_pipeline(input_path, output_dir, poppler_path=poppler_path)
        
        if not results:
            raise HTTPException(status_code=500, detail="Processing failed or returned no results.")
            
        # Format the response
        response_data = []
        for res in results:
            image_base64 = None
            if os.path.exists(res["image_path"]):
                with open(res["image_path"], "rb") as img_file:
                    image_base64 = base64.b64encode(img_file.read()).decode("utf-8")
                    
            response_data.append({
                "page": res["page"],
                "text": res["result_data"]["text"],
                "confidence": res["result_data"]["confidence"],
                "needs_review": res["result_data"]["needs_review"],
                "psm_mode": res["result_data"]["psm_mode"],
                "image_base64": image_base64
            })
            
        return JSONResponse(content={"status": "success", "results": response_data})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temporary directory to save space
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
