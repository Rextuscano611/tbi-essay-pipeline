import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "essay_sheet")
CREDENTIALS_FILE = "credentials.json"

BASE_URL = "https://www.tatabuildingindia.com/achievements"

# Folders
RAW_DIR = "data/raw"
JSON_DIR = "data/json"
LOGS_DIR = "data/logs"
PROGRESS_FILE = "data/logs/progress.json"

# Gemini settings
GEMINI_MODEL = "gemini-2.5-flash"
MAX_RETRIES = 3
RETRY_DELAY = 15  # seconds between retries

# Rate limiting — safe for free tier
REQUEST_DELAY = 30  # seconds between each essay

# Google Sheets columns
SHEET_HEADERS = [
    "Essay ID", "Year", "Filename",
    "Detected Language", "Original Text",
    "English Translation", "Source URL", "Status"
]