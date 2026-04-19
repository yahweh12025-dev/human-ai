from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import os
import asyncio
from typing import Dict, Any, List
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Import swarm components
from agents.ant_farm.orchestrator import AntFarmOrchestrator
from utils.dify_brain import DifyBrain
from utils.master_log import SwarmMasterLog

load_dotenv('/home/ubuntu/human-ai/.env')

app = FastAPI(title="Human-AI Swarm Command Center API")

# Enable CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security: Simple API Key check
API_KEY = os.getenv("DASHBOARD_API_KEY", "swarm-secret-key")

async def verify_token(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

# Initialize Swarm Components
orchestrator = AntFarmOrchestrator()
brain = DifyBrain()
logger = SwarmMasterLog()

class TaskRequest(BaseModel):
    description: str

@app.get("/")
async def root():
    return {"message": "Human-AI Swarm Command Center API is online."}

@app.get("/status")
async def get_status(token: str = Depends(verify_token)):
    return {
        "status": "online",
        "agents": ["Researcher", "Navigator", "NativeWorker", "Critic"],
        "infrastructure": {
            "supabase": "connected",
            "dify": "connected" if os.getenv("DIFY_API_KEY") else "missing_key",
            "sandbox": "ready"
        }
    }

@app.get("/health")
async def system_health(token: str = Depends(verify_token)):
    sandbox_ok = os.path.exists("/home/ubuntu/human-ai/utils/sandbox.Dockerfile")
    try:
        from agents.researcher.researcher_agent import HumanAIResearcher
        agent = HumanAIResearcher()
        # we use a short timeout to prevent hanging
        await asyncio.wait_for(agent.ds_agent.start_browser(), timeout=5)
        browser_ok = True
    except:
        browser_ok = False

    return {
        "status": "healthy" if (sandbox_ok and browser_ok) else "degraded",
        "components": {
            "sandbox": "OK" if sandbox_ok else "FAIL",
            "browser_agents": "OK" if browser_ok else "FAIL",
            "api_bridge": "OK"
        }
    }

@app.post("/execute")
async def execute_task(req: TaskRequest, token: str = Depends(verify_token)):
    try:
        result = await orchestrator.execute_pipeline({"description": req.description})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs")
async def get_logs(limit: int = 50, token: str = Depends(verify_token)):
    try:
        with open('/home/ubuntu/human-ai/master_log.json', 'r') as f:
            import json
            logs = json.load(f)
            return logs[-limit:]
    except Exception as e:
        return {"error": str(e)}

@app.get("/brain/query")
async def query_brain(q: str, token: str = Depends(verify_token)):
    return {"answer": brain.query(q)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=50001)
