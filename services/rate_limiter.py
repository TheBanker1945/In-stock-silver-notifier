import json
import os
from datetime import datetime

import config

USAGE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api_usage.json")


def _load_usage() -> dict:
    """Load the usage tracker from disk."""
    if not os.path.exists(USAGE_FILE):
        return {}
    with open(USAGE_FILE, "r") as f:
        return json.load(f)


def _save_usage(data: dict) -> None:
    """Persist the usage tracker to disk."""
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _current_month_key() -> str:
    """Return the current month as 'YYYY-MM' for tracking."""
    return datetime.now().strftime("%Y-%m")


def get_remaining_requests() -> int:
    """Return how many API requests are left this month."""
    data = _load_usage()
    month = _current_month_key()

    if data.get("month") != month:
        return config.MONTHLY_API_LIMIT

    return max(0, config.MONTHLY_API_LIMIT - data.get("count", 0))


def can_make_request() -> bool:
    """Check if we have API requests remaining this month."""
    return get_remaining_requests() > 0


def record_request() -> None:
    """Record that one API request was used.

    Automatically resets the counter if a new month has started.
    """
    data = _load_usage()
    month = _current_month_key()

    if data.get("month") != month:
        # New month — reset counter
        data = {"month": month, "count": 1}
    else:
        data["count"] = data.get("count", 0) + 1

    _save_usage(data)
