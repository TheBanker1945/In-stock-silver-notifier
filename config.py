import os
from dotenv import load_dotenv

load_dotenv()

# --- SilverStack Dashboard ---
SILVERSTACK_URL = os.getenv("SILVERSTACK_URL", "")
SILVERSTACK_API_KEY = os.getenv("SILVERSTACK_API_KEY", "")

# --- Telegram Bot (used by Gist sync / worker fallback) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- GitHub Gist Sync (for Telegram bot worker) ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GIST_ID = os.getenv("GIST_ID", "")

# --- Legacy: GoldAPI.io keys (no longer used in main flow, kept for fallback) ---
SILVER_API_KEY = os.getenv("SILVER_API_KEY", "")
SILVER_API_KEY_2 = os.getenv("SILVER_API_KEY_2", "")
SILVER_API_KEYS = [k for k in [SILVER_API_KEY, SILVER_API_KEY_2] if k]

# --- Legacy: Deal evaluation constants (filtering now handled by SilverStack dashboard) ---
MAX_PREMIUM = 15.00  # Max EUR above spot price per oz to consider a deal
HARD_CAP = 2500.00   # Absolute max EUR price regardless of spot

# --- Legacy: Rate Limiting (no longer used in main flow) ---
REQUEST_DELAY = 5  # Seconds between checks/actions
MONTHLY_API_LIMIT = 100  # Max silver API requests per calendar month

# --- Legacy: Caching (spot price now provided by SilverStack dashboard) ---
SPOT_PRICE_CACHE_HOURS = 3  # Reuse cached spot price within this window
