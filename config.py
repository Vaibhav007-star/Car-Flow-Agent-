"""Configuration module for Google Flow Video Automation System.
Loads environment variables and sets sensible defaults for browser, paths, and timeouts.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

# Google Flow target URL
# Official Google Flow studio: https://flow.google.com/
FLOW_URL = os.getenv("FLOW_URL", "https://flow.google.com/")

# Browser & Execution settings
HEADLESS = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")
USER_DATA_DIR = BASE_DIR / os.getenv("USER_DATA_DIR", ".browser_data")

# Timeouts & Polling (seconds)
PAGE_TIMEOUT_SEC = int(os.getenv("PAGE_TIMEOUT_SEC", "60"))
GENERATION_TIMEOUT_SEC = int(os.getenv("GENERATION_TIMEOUT_SEC", "360"))
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "3"))

# Optional Viral Trend Hunter APIs
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Directories
OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "output_videos")
LOGS_DIR = BASE_DIR / os.getenv("LOGS_DIR", "logs")

# Prompt management
PROMPTS_FILE = BASE_DIR / os.getenv("PROMPTS_FILE", "prompts.txt")
STATE_FILE = BASE_DIR / "prompts_state.json"

# Ensure runtime directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

