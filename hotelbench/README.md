# HotelBench - Computer-Use Agent for Hotel PMS

A production-quality, demo-ready computer-use agent that navigates a mock Hotel Property Management System (PMS) UI using screenshots and LLM reasoning to fulfill natural language guest requests end-to-end.

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   FastAPI API   │────▶│  LangGraph Agent │────▶│  Playwright     │
│   /request      │     │  State Machine   │     │  Browser Ctrl   │
│   /status       │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │                        │
                              ▼                        ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │    Redis Store   │     │  Claude Vision  │
                        │  Session/History │     │  (Anthropic)    │
                        └──────────────────┘     └─────────────────┘
                                                      ▲
                                                      │
                                                ┌─────────────────┐
                                                │   Mock PMS UI   │
                                                │   (HTML/CSS/JS) │
                                                └─────────────────┘
```

## Directory Structure

```
hotelbench/
├── pms_ui/
│   ├── index.html          # Mock PMS - fully interactive hotel admin UI
│   ├── style.css           # Styling for PMS
│   └── app.js              # UI state: rooms, guests, requests, checkout times
├── agent/
│   ├── graph.py            # LangGraph state machine
│   ├── vision.py           # Screenshot → Claude vision → action plan
│   ├── executor.py         # Playwright action executor
│   ├── memory.py           # Redis session + history store
│   └── prompts.py          # All system + user prompts (versioned)
├── api/
│   └── main.py             # FastAPI: POST /request, GET /status/{run_id}
├── evals/
│   ├── test_cases.json     # 20 golden test cases with expected actions
│   └── eval_harness.py     # Headless eval runner with pass/fail scoring
├── config.py               # Env vars, timeouts, retry limits
└── README.md               # This file
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js (optional, for serving PMS UI)
- Redis server
- Anthropic API key

### Installation

1. **Install Python dependencies:**
```bash
cd hotelbench
pip install -r requirements.txt
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your Anthropic API key
```

3. **Start Redis:**
```bash
redis-server
```

4. **Serve the PMS UI:**
```bash
cd pms_ui
python -m http.server 8080
```

5. **Start the FastAPI backend:**
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Running the Agent

1. **Submit a request:**
```bash
curl -X POST http://localhost:8000/request \
  -H "Content-Type: application/json" \
  -d '{"task": "Extend checkout for room 204 to 2pm"}'
```

2. **Check status:**
```bash
curl http://localhost:8000/status/{run_id}
```

### Running Evaluations

```bash
python -m evals.eval_harness --headless --output evals/results.json
```

## Test Cases

The eval harness runs 20 golden test cases:

1. Extend checkout for room 204 to 2pm
2. Mark room 108 as Do Not Disturb
3. Create a housekeeping request for room 312 — extra towels, high priority
4. What is the checkout time for room 205?
5. Update request #REQ-007 status to Resolved
6. Add a note to room 101 guest profile: VIP, prefers quiet room
7. Which rooms are currently dirty?
8. Create a maintenance request for room 416 — broken AC, urgent
9. Extend checkout for Sarah Johnson to 4pm
10. Mark room 220 as clean and available
11. How many guests are checking out today?
12. Create a concierge request for room 303 — restaurant reservation at 7pm
13. What room is John Smith in?
14. Cancel the housekeeping request for room 108
15. Extend all checkouts on floor 2 by one hour
16. Update room 502 status to maintenance
17. Find all high-priority pending requests
18. Add a note that guest in room 401 has a 6am flight
19. What is the current occupancy rate?
20. Mark rooms 101, 102, 103 as clean

## Quality Gates

Before considering the project complete, verify:

- ✅ Eval harness passes >= 15/20 tasks (75% success rate minimum)
- ✅ avg_confidence >= 0.80 across all runs
- ✅ No Playwright selector errors on the 5 most common task types
- ✅ Redis keys clean up properly after TTL
- ✅ FastAPI /health returns ok for all components

## API Endpoints

### POST /request
Submit a new task to the agent.

**Request:**
```json
{
  "task": "Extend checkout for room 204 to 2pm",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "run_id": "uuid-here",
  "status": "running"
}
```

### GET /status/{run_id}
Get the status and results of a task.

**Response:**
```json
{
  "run_id": "...",
  "status": "running|complete|failed",
  "task": "...",
  "result": {
    "action_taken": "...",
    "iterations": 3,
    "confidence": 0.94
  },
  "error": null,
  "screenshots": ["base64_png_1", ...],
  "action_history": [...]
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "redis": "ok",
  "browser": "ok"
}
```

### POST /demo/reset
Reset the PMS UI to initial state (for clean demo recordings).

## Agent Loop

The agent follows this loop for each task:

1. **OBSERVE**: Take a full-page screenshot of the PMS UI
2. **REASON**: Send screenshot + task to Claude Vision API
3. **PLAN**: Parse Claude's JSON response for next action
4. **EXECUTE**: Execute the action via Playwright
5. **VERIFY**: Take a new screenshot, confirm state changed
6. **LOOP or TERMINATE**: Repeat until task complete or max iterations reached

## Action Types

The agent can perform these actions:

- `click`: Click an element by selector
- `type`: Fill an input field with text
- `select`: Select an option from a dropdown
- `scroll`: Scroll the page down
- `navigate_tab`: Switch between PMS tabs

## Demo Recording

For a 90-second demo recording:

1. Start the PMS UI and FastAPI backend
2. Run browser in headless=False mode
3. Use OBS/Loom to record
4. Demonstrate these scenarios:
   - (a) Checkout extension
   - (b) Housekeeping request creation
   - (c) Guest profile lookup

## License

MIT License
