import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Settings
SPORTMONKS_API_TOKEN = os.getenv("SPORTMONKS_API_TOKEN", "cQfuBoTCFt4bH4RbK4DWZtDMROR5J3A4sErDK1bivg1ZheU5TRbrqsL26UZj")
API_REQUEST_TIMEOUT = int(os.getenv("API_REQUEST_TIMEOUT", "30"))
API_RETRY_COUNT = int(os.getenv("API_RETRY_COUNT", "3"))
API_RETRY_DELAY = int(os.getenv("API_RETRY_DELAY", "5"))

# API Authentication Settings
SPORTMONKS_API_TOKEN = os.getenv("SPORTMONKS_API_TOKEN", "")
SPORTMONKS_API_KEY_PATH = os.getenv("SPORTMONKS_API_KEY_PATH", "keys/sportmonks_api_key.txt")

# API requests can use token from environment or file. Environment takes precedence.
if not SPORTMONKS_API_TOKEN and os.path.exists(SPORTMONKS_API_KEY_PATH):
    try:
        with open(SPORTMONKS_API_KEY_PATH, 'r') as f:
            SPORTMONKS_API_TOKEN = f.read().strip()
    except Exception as e:
        print(f"Warning: Failed to load API token from {SPORTMONKS_API_KEY_PATH}: {e}")

# API Cache Settings
API_CACHE_ENABLED = os.getenv("API_CACHE_ENABLED", "True").lower() == "true"
API_CACHE_DIR = os.getenv("API_CACHE_DIR", "cache")
API_CACHE_DURATION = int(os.getenv("API_CACHE_DURATION", "3600"))  # 1 hour default

# Database Settings
DB_TYPE = os.getenv("DB_TYPE", "postgresql")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "football_data")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Logging Settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "football_data.log")

# Default date ranges
DEFAULT_DAYS_BACK = int(os.getenv("DEFAULT_DAYS_BACK", "3"))
DEFAULT_DAYS_FORWARD = int(os.getenv("DEFAULT_DAYS_FORWARD", "7"))

def get_start_date():
    """Get default start date (today - DEFAULT_DAYS_BACK)"""
    return (datetime.now() - timedelta(days=DEFAULT_DAYS_BACK)).strftime("%Y-%m-%d")

def get_end_date():
    """Get default end date (today + DEFAULT_DAYS_FORWARD)"""
    return (datetime.now() + timedelta(days=DEFAULT_DAYS_FORWARD)).strftime("%Y-%m-%d")

# Scheduler Settings
SCHEDULE_INTERVAL_HOURS = int(os.getenv("SCHEDULE_INTERVAL_HOURS", "4"))
