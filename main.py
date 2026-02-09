import time

import config
from services.silver_price import SilverPriceService
from services.notifier import TelegramNotifier
from services.rate_limiter import get_remaining_requests
from core.calculator import is_good_deal
from scrapers.goldsilver import scrape_site


def run():
    print("=" * 50)
    print("SilverScout - Live Run")
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

    # --- Scrape goldsilver.be ---
    print("\nScraping goldsilver.be for in-stock 1 oz silver...")
    try:
        products = scrape_site()
    except Exception as e:
        print(f"[Scraper] Failed to scrape goldsilver.be: {e}")
        return

    print(f"Found {len(products)} in-stock product(s).")

    if not products:
        print("No in-stock products found. Exiting.")
        return

    # --- Evaluate products ---
    notifier = TelegramNotifier()
    deals_found = 0

    for product in products:
        name = product["name"]
        price = product["price"]
        url = product["url"]

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
                f"<a href=\"{url}\">View Product</a>"
            )
            notifier.send(message)
        else:
            print(f"  -> Skip (too expensive or over cap)")

    print(f"\n{'=' * 50}")
    print(f"Done. {deals_found} deal(s) found out of {len(products)} in-stock products.")


if __name__ == "__main__":
    run()
