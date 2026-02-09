import time

import config
from services.silver_price import SilverPriceService
from services.notifier import TelegramNotifier
from services.rate_limiter import get_remaining_requests
from core.calculator import is_good_deal


# Dummy products for Phase 1 testing.
# Each entry: (name, price_eur_per_oz)
DUMMY_PRODUCTS = [
    ("1 oz Silver Maple Leaf", 30.50),
    ("1 oz Silver Philharmonic", 45.00),
    ("1 oz Silver Bar (Generic)", 28.00),
    ("1 oz Silver Krugerrand", 3000.00),  # Over HARD_CAP
]


def run():
    print("=" * 50)
    print("SilverScout - Phase 1 Test Run")
    print("=" * 50)

    # --- Validate config ---
    missing = []
    if not config.SILVER_API_KEY:
        missing.append("SILVER_API_KEY")
    if not config.TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not config.TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")

    if missing:
        print(f"[Config] Missing env vars: {', '.join(missing)}")
        print("[Config] Copy .env.example to .env and fill in your values.")
        return

    # --- Show rate limit status ---
    remaining = get_remaining_requests()
    print(f"\n[Rate Limit] API requests remaining this month: {remaining}/{config.MONTHLY_API_LIMIT}")

    if remaining == 0:
        print("[Rate Limit] No requests left. Exiting.")
        return

    # --- Fetch spot price ---
    price_service = SilverPriceService()
    print("\nFetching silver spot price (EUR, XAG only)...")
    spot_price = price_service.get_spot_price_eur()

    if spot_price is None:
        print("Failed to fetch spot price. Exiting.")
        return

    remaining = get_remaining_requests()
    print(f"Current silver spot price: EUR {spot_price:.2f}/oz")
    print(f"Max acceptable price:      EUR {spot_price + config.MAX_PREMIUM:.2f}/oz")
    print(f"Hard cap:                  EUR {config.HARD_CAP:.2f}")
    print(f"[Rate Limit] API requests remaining after fetch: {remaining}/{config.MONTHLY_API_LIMIT}")

    # --- Evaluate dummy products ---
    notifier = TelegramNotifier()
    deals_found = 0

    for name, price in DUMMY_PRODUCTS:
        print(f"\nChecking: {name} @ EUR {price:.2f}")
        time.sleep(config.REQUEST_DELAY)

        if is_good_deal(price, spot_price):
            deals_found += 1
            premium = price - spot_price
            print(f"  -> DEAL! Premium: EUR {premium:.2f}")

            message = (
                f"<b>SilverScout Deal Found!</b>\n\n"
                f"Product: {name}\n"
                f"Price: EUR {price:.2f}\n"
                f"Spot: EUR {spot_price:.2f}\n"
                f"Premium: EUR {premium:.2f}\n"
            )
            notifier.send(message)
        else:
            print(f"  -> Skip (too expensive or over cap)")

    print(f"\n{'=' * 50}")
    print(f"Done. {deals_found} deal(s) found out of {len(DUMMY_PRODUCTS)} products.")


if __name__ == "__main__":
    run()
