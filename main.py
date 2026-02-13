import time

import config
from services.silver_price import SilverPriceService
from services.notifier import TelegramNotifier
from services.rate_limiter import get_remaining_requests, get_total_limit
from services.deal_tracker import load as load_deals, save as save_deals, is_already_notified, mark_notified
from core.calculator import is_good_deal
from services.gist_sync import sync_state_to_gist
from scrapers.goldsilver import scrape_site as scrape_goldsilver
from scrapers.argentorshop import scrape_site as scrape_argentorshop
from scrapers.hollandgold import scrape_site as scrape_hollandgold

SCRAPERS = [
    ("goldsilver.be", scrape_goldsilver),
    ("argentorshop.be", scrape_argentorshop),
    ("hollandgold.nl", scrape_hollandgold),
]


def run():
    print("=" * 50)
    print("SilverScout - Live Run")
    print("=" * 50)

    # --- Validate config ---
    missing = []
    if not config.SILVER_API_KEYS:
        missing.append("SILVER_API_KEY (or SILVER_API_KEY_2)")
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
    total_limit = get_total_limit()
    print(f"\n[Rate Limit] API requests remaining this month: {remaining}/{total_limit} ({len(config.SILVER_API_KEYS)} key(s))")

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
    print(f"[Rate Limit] API requests remaining after fetch: {remaining}/{total_limit}")

    # --- Scrape all dealer sites ---
    all_products = []
    for site_name, scrape_fn in SCRAPERS:
        print(f"\nScraping {site_name}...")
        try:
            products = scrape_fn()
            print(f"[{site_name}] {len(products)} in-stock product(s)")
            all_products.extend(products)
        except Exception as e:
            print(f"[{site_name}] Scrape failed: {e}")

    if not all_products:
        print("\nNo in-stock products found across any site. Exiting.")
        return

    print(f"\nTotal: {len(all_products)} in-stock product(s) across {len(SCRAPERS)} site(s).")

    # --- Evaluate products ---
    notifier = TelegramNotifier()
    notified_deals = load_deals()
    deals_found = 0

    for product in all_products:
        name = product["name"]
        price_per_oz = product["price_per_oz"]
        total_price = product["total_price"]
        quantity_oz = product["quantity_oz"]
        url = product["url"]

        print(f"\nChecking: {name} @ EUR {price_per_oz:.2f}/oz ({quantity_oz:.2f} oz, total EUR {total_price:.2f})")

        if is_good_deal(price_per_oz, spot_price, total_price):
            deals_found += 1
            premium = price_per_oz - spot_price
            print(f"  -> DEAL! Premium: EUR {premium:.2f}/oz")

            if is_already_notified(notified_deals, url, price_per_oz, total_price):
                print(f"  -> Already notified, skipping.")
                continue

            message = (
                f"<b>SilverScout Deal Found!</b>\n\n"
                f"Product: {name}\n"
                f"Price/oz: EUR {price_per_oz:.2f}\n"
                f"Total: EUR {total_price:.2f} ({quantity_oz:.2f} oz)\n"
                f"Spot: EUR {spot_price:.2f}\n"
                f"Premium: EUR {premium:.2f}/oz\n"
                f"<a href=\"{url}\">View Product</a>"
            )
            if notifier.send(message):
                mark_notified(notified_deals, url, price_per_oz, total_price)
        else:
            print(f"  -> Skip (too expensive or over cap)")

    save_deals(notified_deals)

    print(f"\n{'=' * 50}")
    print(f"Done. {deals_found} deal(s) found out of {len(all_products)} in-stock products.")

    # --- Sync state to Gist for Telegram bot ---
    sync_state_to_gist()


if __name__ == "__main__":
    run()
