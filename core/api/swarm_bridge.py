from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import os
import sys
import asyncio

# Ensure project root is in path
sys.path.append('/home/yahwehatwork/human-ai')

from core.agents.ant_farm.orchestrator import AntFarmOrchestrator
from core.utils.master_log import SwarmMasterLog

app = FastAPI(title="Human-AI Swarm Command Center Bridge")
orchestrator = AntFarmOrchestrator()
master_log = SwarmMasterLog()

class TaskRequest(BaseModel):
    description: str
    priority: Optional[int] = 1
    apply_changes: Optional[bool] = True

class StatusResponse(BaseModel):
    status: str
    active_tasks: int
    last_event: str

@app.get("/")
async def root():
    return {"message": "Swarm Command Center Bridge Active", "version": "1.0"}

@app.post("/run")
async def run_pipeline(request: TaskRequest, background_tasks: BackgroundTasks):
    """Triggers the AntFarm pipeline in the background."""
    async def execute():
        try:
            await orchestrator.execute_pipeline({"description": request.description})
        except Exception as e:
            print(f"Pipeline Execution Error: {e}")

    background_tasks.add_task(execute)
    return {"status": "queued", "task": request.description}

@app.get("/status")
async def get_status():
    """Retrieves the current state of the swarm."""
    # In a full implementation, we'd track active PIDs
    return {
        "status": "operational",
        "core_version": "v4.0",
        "active_agents": ["Researcher", "Developer", "Reviewer", "NotebookLM"],
        "memory_status": "synced"
    }

@app.get("/logs")
async def get_logs(lines: int = 50):
    """Tails the master log."""
    try:
        with open("/home/yahwehatwork/human-ai/docs/outcome_log.md", "r") as f:
            content = f.readlines()
            return {"logs": content[-lines:]}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Run on a local port for the Gateway to connect to
    uvicorn.run(app, host="0.0.0.0", port=8000)
