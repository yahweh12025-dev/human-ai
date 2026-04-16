from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv

# Import swarm components
from agents.ant_farm.orchestrator import AntFarmOrchestrator
from utils.dify_brain import DifyBrain

load_dotenv('/home/ubuntu/human-ai/.env')

app = FastAPI(title="Human-AI Swarm Command Center")
orchestrator = AntFarmOrchestrator()
brain = DifyBrain()

class TaskRequest(BaseModel):
    description: str

@app.get("/status")
async def get_status():
    return {
        "status": "online",
        "agents": ["Researcher", "Navigator", "NativeWorker", "Critic"],
        "infrastructure": {
            "supabase": "connected",
            "dify": "connected" if os.getenv("DIFY_API_KEY") else "missing_key",
            "sandbox": "ready"
        }
    }

@app.post("/execute")
async def execute_task(req: TaskRequest):
    try:
        result = await orchestrator.execute_pipeline({"description": req.description})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/brain/query")
async def query_brain(q: str):
    return {"answer": brain.query(q)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
