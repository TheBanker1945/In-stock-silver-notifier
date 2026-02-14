# LEGACY: Kept as fallback. Primary deal evaluation is now handled by SilverStack dashboard.
import json
import os
import time

import requests

import config
from services.rate_limiter import can_make_request, record_request, get_remaining_requests, get_available_key


CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "spot_price_cache.json")


def _load_cached_price() -> float | None:
    """Return cached spot price if fresh (within SPOT_PRICE_CACHE_HOURS), else None."""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
        fetched_at = data["fetched_at"]
        max_age = config.SPOT_PRICE_CACHE_HOURS * 3600
        if time.time() - fetched_at < max_age:
            return data["price"]
    except (json.JSONDecodeError, KeyError, IOError):
        pass
    return None


def _save_cached_price(price: float) -> None:
    """Write spot price and timestamp to cache file."""
    with open(CACHE_FILE, "w") as f:
        json.dump({"price": price, "fetched_at": time.time()}, f, indent=2)


class SilverPriceService:
    """Fetches the current silver spot price in EUR from GoldAPI.io."""

    BASE_URL = "https://www.goldapi.io/api/XAG/EUR"

    def get_spot_price_eur(self) -> float | None:
        """Return the current silver spot price per troy ounce in EUR.

        Uses a local cache to avoid burning API requests when the cached
        value is less than SPOT_PRICE_CACHE_HOURS old.
        Returns None if the request fails or the monthly limit is reached.
        """
        cached = _load_cached_price()
        if cached is not None:
            print(f"[SilverPrice] Using cached spot price: EUR {cached:.2f} (cache < {config.SPOT_PRICE_CACHE_HOURS}h old)")
            return cached

        api_key = get_available_key(config.SILVER_API_KEYS)
        if api_key is None:
            print(f"[SilverPrice] All API keys exhausted ({config.MONTHLY_API_LIMIT} requests/key).")
            print(f"[SilverPrice] Limit resets at the start of next month.")
            return None

        remaining = get_remaining_requests()
        print(f"[SilverPrice] API requests remaining this month: {remaining}")

        headers = {
            "x-access-token": api_key,
        }

        try:
            resp = requests.get(self.BASE_URL, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Count the request regardless of API-level success/failure,
            # because the HTTP request was made and counted by the provider.
            record_request(api_key)

            if "error" in data:
                print(f"[SilverPrice] API error: {data['error']}")
                return None

            spot_price = round(data["price"], 2)
            _save_cached_price(spot_price)
            return spot_price

        except requests.RequestException as e:
            print(f"[SilverPrice] Request failed: {e}")
            return None
        except (KeyError, TypeError) as e:
            print(f"[SilverPrice] Failed to parse response: {e}")
            return None
