from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent_service.agentic_rag import run_agentic_chat

app = FastAPI(title="Agentic RAG Service")

class ChatRequest(BaseModel):
    task_id: str
    question: str

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        agent_result = run_agentic_chat(request.task_id, request.question)
        return {
            "status": "success",
            "task_id": request.task_id,
            "answer": agent_result.get("answer", ""),
            "contexts": agent_result.get("contexts", [])
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
