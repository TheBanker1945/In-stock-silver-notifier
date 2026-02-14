# LEGACY: Kept as fallback. Primary deal evaluation is now handled by SilverStack dashboard.
import json
import os


DEAL_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "notified_deals.json")


def load(filepath: str = DEAL_FILE) -> dict:
    """Read notified deals from JSON file. Returns empty dict if missing."""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def is_already_notified(deals: dict, url: str, price_per_oz: float, total_price: float) -> bool:
    """Return True if the same deal (URL + price) was already notified."""
    if url not in deals:
        return False
    prev = deals[url]
    return prev["price_per_oz"] == price_per_oz and prev["total_price"] == total_price


def mark_notified(deals: dict, url: str, price_per_oz: float, total_price: float) -> None:
    """Record a deal as notified (updates dict in-place)."""
    deals[url] = {"price_per_oz": price_per_oz, "total_price": total_price}


def save(deals: dict, filepath: str = DEAL_FILE) -> None:
    """Write notified deals dict to JSON file."""
    with open(filepath, "w") as f:
        json.dump(deals, f, indent=2)
