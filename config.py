import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys & Tokens ---
SILVER_API_KEY = os.getenv("SILVER_API_KEY", "")
SILVER_API_KEY_2 = os.getenv("SILVER_API_KEY_2", "")
SILVER_API_KEYS = [k for k in [SILVER_API_KEY, SILVER_API_KEY_2] if k]
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- GitHub Gist Sync (for Telegram bot worker) ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GIST_ID = os.getenv("GIST_ID", "")

# --- Buying Thresholds ---
MAX_PREMIUM = 15.00  # Max EUR above spot price per oz to consider a deal
HARD_CAP = 2500.00   # Absolute max EUR price regardless of spot

# --- Rate Limiting ---
REQUEST_DELAY = 5  # Seconds between checks/actions
MONTHLY_API_LIMIT = 100  # Max silver API requests per calendar month

# --- Caching ---
SPOT_PRICE_CACHE_HOURS = 3  # Reuse cached spot price within this window
