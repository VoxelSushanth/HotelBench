"""
HotelBench FastAPI Backend
API endpoints for agent orchestration
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Any
import asyncio
import uuid

from config import API_HOST, API_PORT, PMS_UI_URL
from agent.memory import memory_store
from agent.executor import get_executor, shutdown_executor
from agent.graph import HotelBenchAgent


# Pydantic models
class RequestTask(BaseModel):
    task: str
    session_id: Optional[str] = None


class TaskStatus(BaseModel):
    run_id: str
    status: str
    task: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    screenshots: Optional[List[str]] = None
    action_history: Optional[List[dict]] = None


class HealthResponse(BaseModel):
    status: str
    redis: str
    browser: str


class ResetResponse(BaseModel):
    status: str
    message: str


# FastAPI app
app = FastAPI(
    title="HotelBench API",
    description="Computer-Use Agent for Hotel PMS",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance (lazy initialization)
_agent: Optional[HotelBenchAgent] = None
_running_tasks: dict = {}  # Track background tasks


def get_agent_instance() -> HotelBenchAgent:
    """Get or create the global agent instance (sync version)."""
    global _agent
    if _agent is None:
        _agent = HotelBenchAgent(headless=False)  # Non-headless for demo
    return _agent


async def run_task_background(task: str, run_id: str, session_id: Optional[str] = None):
    """Run a task in the background."""
    try:
        agent = get_agent_instance()
        await agent.run(task, session_id=run_id)
    except Exception as e:
        memory_store.update_status(run_id, "failed", {"error": str(e)})
    finally:
        if run_id in _running_tasks:
            del _running_tasks[run_id]


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    # Pre-initialize executor
    try:
        executor = await get_executor(headless=False)
        print("Browser initialized successfully")
    except Exception as e:
        print(f"Warning: Could not initialize browser on startup: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    await shutdown_executor()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    redis_status = "ok" if memory_store.health_check() else "error"
    
    browser_status = "ok"
    try:
        executor = await get_executor(headless=True)
        await executor.get_current_tab()
    except Exception:
        browser_status = "error"
    
    return HealthResponse(
        status="ok" if redis_status == "ok" and browser_status == "ok" else "degraded",
        redis=redis_status,
        browser=browser_status
    )


@app.post("/request")
async def submit_request(request: RequestTask, background_tasks: BackgroundTasks):
    """Submit a new task to the agent."""
    # Validate input
    if not request.task or len(request.task.strip()) == 0:
        raise HTTPException(status_code=400, detail="Task cannot be empty")
    
    # Generate run_id
    run_id = request.session_id or str(uuid.uuid4())
    
    # Initialize run in memory
    memory_store.save_run(run_id, {
        "run_id": run_id,
        "task": request.task,
        "status": "running",
        "intent": {},
        "screenshots": [],
        "action_history": [],
        "iteration": 0
    })
    
    # Start background task
    background_tasks.add_task(
        run_task_background,
        request.task,
        run_id,
        run_id
    )
    
    _running_tasks[run_id] = True
    
    return {"run_id": run_id, "status": "running"}


@app.get("/status/{run_id}", response_model=TaskStatus)
async def get_status(run_id: str):
    """Get the status of a task."""
    run_data = memory_store.get_run(run_id)
    
    if not run_data:
        raise HTTPException(status_code=404, detail="Run not found")
    
    screenshots = memory_store.get_screenshots(run_id)
    action_history = memory_store.get_action_history(run_id)
    
    return TaskStatus(
        run_id=run_id,
        status=run_data.get("status", "unknown"),
        task=run_data.get("task"),
        result=run_data.get("result"),
        error=run_data.get("error"),
        screenshots=screenshots,
        action_history=action_history
    )


@app.post("/demo/reset", response_model=ResetResponse)
async def reset_demo():
    """Reset the PMS UI to initial state."""
    try:
        executor = await get_executor(headless=False)
        await executor.reset_pms()
        
        return ResetResponse(
            status="ok",
            message="PMS UI has been reset to initial state"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset: {str(e)}")


@app.get("/runs")
async def list_runs(limit: int = 10):
    """List recent runs (simplified - in production would query Redis properly)."""
    # This is a simplified implementation
    # In production, you'd use Redis SCAN or maintain a separate index
    return {"runs": [], "message": "Run listing not fully implemented"}


@app.delete("/run/{run_id}")
async def delete_run(run_id: str):
    """Delete a run and its associated data."""
    success = memory_store.delete_run(run_id)
    if success:
        return {"status": "deleted", "run_id": run_id}
    else:
        raise HTTPException(status_code=404, detail="Run not found")


# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )
