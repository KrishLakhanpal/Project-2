"""Central configuration, loaded from .env (see .env.example)."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()
LIVE_MONITOR_INTERVAL = float(os.getenv("LIVE_MONITOR_INTERVAL", "2.5"))
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "5"))

DB_PATH = BASE_DIR / "assistant.db"
HISTORY_DIR = BASE_DIR / "captures"
HISTORY_DIR.mkdir(exist_ok=True)

if not GEMINI_API_KEY:
    print(
        "[WARNING] GEMINI_API_KEY is not set. Copy .env.example to .env and "
        "add your key, or the AI reasoning steps will not work "
        "(OCR/detection will still run)."
    )
