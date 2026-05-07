"""
HotelBench Graph Module
LangGraph state machine for agent orchestration
"""

from typing import TypedDict, List, Optional, Any
from langgraph.graph import StateGraph, END
import uuid
import asyncio

from config import MAX_ITERATIONS_PER_TASK
from agent.memory import memory_store, MemoryStore
from agent.executor import PlaywrightExecutor, get_executor, shutdown_executor
from agent.vision import VisionReasoner, get_vision_reasoner


class AgentState(TypedDict):
    """State schema for the agent."""
    task: str
    intent: dict
    screenshots: List[str]
    action_history: List[dict]
    iteration: int
    max_iterations: int
    run_id: str
    status: str  # running | complete | failed
    result: Optional[dict]
    error: Optional[str]


class HotelBenchAgent:
    """LangGraph-based agent for hotel PMS automation."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.executor: Optional[PlaywrightExecutor] = None
        self.vision: Optional[VisionReasoner] = None
        self.memory: MemoryStore = memory_store
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("parse_request", self.parse_request)
        workflow.add_node("observe", self.observe)
        workflow.add_node("reason", self.reason)
        workflow.add_node("execute", self.execute)
        workflow.add_node("verify", self.verify)
        workflow.add_node("check_complete", self.check_complete)
        workflow.add_node("handle_failure", self.handle_failure)
        workflow.add_node("done", self.done)
        
        # Add edges
        workflow.add_edge("parse_request", "observe")
        workflow.add_edge("observe", "reason")
        workflow.add_edge("reason", "execute")
        workflow.add_edge("execute", "verify")
        workflow.add_edge("verify", "check_complete")
        
        # Conditional edges from check_complete
        workflow.add_conditional_edges(
            "check_complete",
            self.route_from_check_complete,
            {
                "done": "done",
                "continue": "observe",
                "failure": "handle_failure"
            }
        )
        
        workflow.add_edge("handle_failure", "done")
        
        # Set entry point
        workflow.set_entry_point("parse_request")
        
        return workflow.compile()
    
    async def parse_request(self, state: AgentState) -> AgentState:
        """Parse the natural language request into structured intent."""
        # Simple intent parsing - in production, this would use an LLM
        task = state["task"].lower()
        
        intent = {
            "action_type": None,
            "room_number": None,
            "guest_name": None,
            "request_id": None,
            "params": {}
        }
        
        # Extract room number (simple pattern matching)
        import re
        room_match = re.search(r'room\s*(\d+)', task)
        if room_match:
            intent["room_number"] = room_match.group(1)
        
        # Extract request ID
        req_match = re.search(r'(REQ-\d+)', task.upper())
        if req_match:
            intent["request_id"] = req_match.group(1)
        
        # Determine action type
        if "extend checkout" in task or "checkout time" in task:
            intent["action_type"] = "extend_checkout"
        elif "do not disturb" in task or "dnd" in task:
            intent["action_type"] = "toggle_dnd"
        elif "housekeeping request" in task or "create" in task and "housekeeping" in task:
            intent["action_type"] = "create_housekeeping_request"
        elif "maintenance request" in task:
            intent["action_type"] = "create_maintenance_request"
        elif "concierge request" in task:
            intent["action_type"] = "create_concierge_request"
        elif "status" in task and ("resolved" in task or "update" in task):
            intent["action_type"] = "update_request_status"
        elif "note" in task and "add" in task:
            intent["action_type"] = "add_note"
        elif "mark" in task and "clean" in task:
            intent["action_type"] = "mark_clean"
        elif "what" in task or "which" in task or "how many" in task:
            intent["action_type"] = "query"
        elif "find" in task or "lookup" in task:
            intent["action_type"] = "lookup"
        
        state["intent"] = intent
        return state
    
    async def observe(self, state: AgentState) -> AgentState:
        """Take a screenshot of the current UI state."""
        if self.executor is None:
            self.executor = await get_executor(headless=self.headless)
        
        screenshot = await self.executor.take_screenshot()
        state["screenshots"].append(screenshot)
        
        # Store screenshot in Redis
        self.memory.append_screenshot(state["run_id"], screenshot)
        
        return state
    
    async def reason(self, state: AgentState) -> AgentState:
        """Call Claude Vision to analyze screenshot and plan next action."""
        if self.vision is None:
            self.vision = get_vision_reasoner()
        
        if self.executor is None:
            self.executor = await get_executor(headless=self.headless)
        
        current_tab = await self.executor.get_current_tab()
        latest_screenshot = state["screenshots"][-1]
        
        plan = await self.vision.analyze_screenshot(
            screenshot_base64=latest_screenshot,
            task_description=state["task"],
            current_tab=current_tab,
            action_history=state["action_history"]
        )
        
        # Store the plan in state for execution
        state["_current_plan"] = plan
        
        return state
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the planned action via Playwright."""
        if self.executor is None:
            self.executor = await get_executor(headless=self.headless)
        
        plan = state.get("_current_plan", {})
        action = plan.get("action", {})
        
        action_type = action.get("type", "")
        target = action.get("target", "")
        value = action.get("value", "")
        
        # Check idempotency
        action_hash = MemoryStore.hash_action(action)
        if self.memory.check_idempotency(state["run_id"], action_hash):
            state["_action_result"] = {"success": False, "error": "duplicate_action"}
            return state
        
        result = await self.executor.execute_action(action_type, target, value)
        
        # Mark action as done for idempotency
        if result.get("success"):
            self.memory.mark_action_done(state["run_id"], action_hash)
        
        state["_action_result"] = result
        
        # Record action in history
        action_record = {
            "iteration": state["iteration"],
            "action": action,
            "result": result,
            "observation": plan.get("observation", ""),
            "reasoning": plan.get("reasoning", ""),
            "confidence": plan.get("confidence", 0)
        }
        state["action_history"].append(action_record)
        self.memory.append_action_history(state["run_id"], action_record)
        
        return state
    
    async def verify(self, state: AgentState) -> AgentState:
        """Take a post-action screenshot to verify state change."""
        if self.executor is None:
            self.executor = await get_executor(headless=self.headless)
        
        # Wait a bit for UI to settle
        await asyncio.sleep(0.5)
        
        screenshot = await self.executor.take_screenshot()
        state["screenshots"].append(screenshot)
        self.memory.append_screenshot(state["run_id"], screenshot)
        
        # Simple verification: check if action was successful
        action_result = state.get("_action_result", {})
        state["_verification_passed"] = action_result.get("success", False)
        
        return state
    
    async def check_complete(self, state: AgentState) -> AgentState:
        """Check if task is complete or max iterations reached."""
        plan = state.get("_current_plan", {})
        task_complete = plan.get("task_complete", False)
        
        state["iteration"] += 1
        
        if task_complete:
            state["status"] = "complete"
            state["result"] = {
                "action_taken": plan.get("completion_note", "Task completed"),
                "iterations": state["iteration"],
                "confidence": plan.get("confidence", 0),
                "final_observation": plan.get("observation", "")
            }
        elif state["iteration"] >= state["max_iterations"]:
            state["status"] = "failed"
            state["error"] = f"Max iterations ({state['max_iterations']}) reached"
        else:
            state["status"] = "running"
        
        return state
    
    def route_from_check_complete(self, state: AgentState) -> str:
        """Route based on completion status."""
        if state["status"] == "complete":
            return "done"
        elif state["status"] == "failed":
            return "failure"
        else:
            return "continue"
    
    async def handle_failure(self, state: AgentState) -> AgentState:
        """Handle failure cases and log error."""
        # Log failure mode
        error = state.get("error", "Unknown error")
        print(f"Task failed: {state['task']} - Error: {error}")
        
        # Try to extract useful info from action history
        if state["action_history"]:
            last_action = state["action_history"][-1]
            state["error"] = f"{error}. Last action: {last_action.get('action', {})}"
        
        return state
    
    async def done(self, state: AgentState) -> AgentState:
        """Finalize the run and save results."""
        # Save final state to Redis
        final_state = {
            "run_id": state["run_id"],
            "task": state["task"],
            "status": state["status"],
            "result": state["result"],
            "error": state["error"],
            "iteration": state["iteration"],
            "action_history": state["action_history"]
        }
        self.memory.save_run(state["run_id"], final_state)
        
        return state
    
    async def run(self, task: str, session_id: Optional[str] = None) -> str:
        """Run the agent on a task and return run_id."""
        run_id = session_id or str(uuid.uuid4())
        
        initial_state: AgentState = {
            "task": task,
            "intent": {},
            "screenshots": [],
            "action_history": [],
            "iteration": 0,
            "max_iterations": MAX_ITERATIONS_PER_TASK,
            "run_id": run_id,
            "status": "running",
            "result": None,
            "error": None,
            "_current_plan": {},
            "_action_result": {},
            "_verification_passed": False
        }
        
        # Save initial state
        self.memory.save_run(run_id, {
            "run_id": run_id,
            "task": task,
            "status": "running"
        })
        
        # Run the graph
        try:
            final_state = await self.graph.ainvoke(initial_state)
            return run_id
        except Exception as e:
            # Handle unexpected errors
            self.memory.update_status(run_id, "failed")
            raise e
    
    async def cleanup(self):
        """Cleanup resources."""
        await shutdown_executor()


# Global agent instance
_agent: Optional[HotelBenchAgent] = None


async def get_agent(headless: bool = True) -> HotelBenchAgent:
    """Get or create the global agent instance."""
    global _agent
    if _agent is None:
        _agent = HotelBenchAgent(headless=headless)
    return _agent


async def run_task(task: str, session_id: Optional[str] = None, headless: bool = True) -> str:
    """Convenience function to run a single task."""
    agent = await get_agent(headless=headless)
    return await agent.run(task, session_id)
