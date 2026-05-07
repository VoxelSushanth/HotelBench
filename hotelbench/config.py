"""
HotelBench Configuration
Environment variables, timeouts, and retry limits
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Anthropic API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_TTL = 3600  # 1 hour TTL for run data

# Playwright/Browser Configuration
BROWSER_VIEWPORT_WIDTH = 1280
BROWSER_VIEWPORT_HEIGHT = 800
BROWSER_HEADLESS_FOR_EVALS = True
SCREENSHOT_TIMEOUT = 10000  # 10 seconds
ACTION_TIMEOUT = 3000  # 3 seconds per action
NETWORK_IDLE_TIMEOUT = 5000  # 5 seconds
ACTION_SETTLE_WAIT = 800  # 800ms wait after action before screenshot

# Agent Configuration
MAX_ITERATIONS_PER_TASK = 8
MIN_CONFIDENCE_THRESHOLD = 0.6
SCROLL_PIXELS = 400

# FastAPI Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))

# PMS UI Configuration
PMS_UI_URL = os.getenv("PMS_UI_URL", "http://localhost:8080")

# Evals Configuration
EVAL_OUTPUT_DIR = "evals"
EVAL_RESULTS_FILE = "evals/results.json"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
