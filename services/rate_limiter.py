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


def _key_id(api_key: str) -> str:
    """Return a short identifier for an API key (last 6 chars)."""
    return api_key[-6:]


def _get_key_usage(data: dict, month: str) -> dict:
    """Return the per-key usage dict for the current month."""
    if data.get("month") != month:
        return {}
    return data.get("keys", {})


def get_available_key(keys: list[str]) -> str | None:
    """Return the first key with remaining requests, or None if all exhausted."""
    data = _load_usage()
    month = _current_month_key()
    key_usage = _get_key_usage(data, month)

    for key in keys:
        kid = _key_id(key)
        used = key_usage.get(kid, 0)
        if used < config.MONTHLY_API_LIMIT:
            return key
    return None


def get_remaining_requests() -> int:
    """Return total remaining API requests across all keys this month."""
    data = _load_usage()
    month = _current_month_key()
    keys = config.SILVER_API_KEYS

    if not keys:
        return 0

    if data.get("month") != month:
        return config.MONTHLY_API_LIMIT * len(keys)

    key_usage = data.get("keys", {})
    total_used = sum(key_usage.get(_key_id(k), 0) for k in keys)
    return max(0, config.MONTHLY_API_LIMIT * len(keys) - total_used)


def get_total_limit() -> int:
    """Return the total monthly limit across all keys."""
    return config.MONTHLY_API_LIMIT * len(config.SILVER_API_KEYS)


def can_make_request() -> bool:
    """Check if any API key has remaining requests this month."""
    return get_available_key(config.SILVER_API_KEYS) is not None


def record_request(api_key: str) -> None:
    """Record that one API request was used for a specific key.

    Automatically resets the counter if a new month has started.
    """
    data = _load_usage()
    month = _current_month_key()
    kid = _key_id(api_key)

    if data.get("month") != month:
        # New month — reset all counters
        data = {"month": month, "keys": {kid: 1}}
    else:
        keys = data.setdefault("keys", {})
        keys[kid] = keys.get(kid, 0) + 1

    _save_usage(data)
