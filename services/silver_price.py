import requests
import config
from services.rate_limiter import can_make_request, record_request, get_remaining_requests


class SilverPriceService:
    """Fetches the current silver spot price in EUR from GoldAPI.io."""

    BASE_URL = "https://www.goldapi.io/api/XAG/EUR"

    def __init__(self):
        self.api_key = config.SILVER_API_KEY

    def get_spot_price_eur(self) -> float | None:
        """Return the current silver spot price per troy ounce in EUR.

        Returns None if the request fails or the monthly limit is reached.
        """
        remaining = get_remaining_requests()
        if not can_make_request():
            print(f"[SilverPrice] Monthly API limit reached ({config.MONTHLY_API_LIMIT} requests).")
            print(f"[SilverPrice] Limit resets at the start of next month.")
            return None

        print(f"[SilverPrice] API requests remaining this month: {remaining}")

        headers = {
            "x-access-token": self.api_key,
        }

        try:
            resp = requests.get(self.BASE_URL, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Count the request regardless of API-level success/failure,
            # because the HTTP request was made and counted by the provider.
            record_request()

            if "error" in data:
                print(f"[SilverPrice] API error: {data['error']}")
                return None

            spot_price = data["price"]
            return round(spot_price, 2)

        except requests.RequestException as e:
            print(f"[SilverPrice] Request failed: {e}")
            return None
        except (KeyError, TypeError) as e:
            print(f"[SilverPrice] Failed to parse response: {e}")
            return None
