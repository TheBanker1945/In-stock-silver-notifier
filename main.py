import time

import config
from services.dashboard_sync import sync_deals
from services.gist_sync import sync_state_to_gist
from scrapers.goldsilver import scrape_site as scrape_goldsilver
from scrapers.argentorshop import scrape_site as scrape_argentorshop
from scrapers.hollandgold import scrape_site as scrape_hollandgold

SCRAPERS = [
    ("goldsilver.be", "goldsilver_be", scrape_goldsilver),
    ("argentorshop.be", "argentorshop_be", scrape_argentorshop),
    ("hollandgold.nl", "hollandgold_nl", scrape_hollandgold),
]


def run():
    print("=" * 50)
    print("SilverScout - Live Run")
    print("=" * 50)

    # --- Validate config ---
    missing = []
    if not config.SILVERSTACK_URL:
        missing.append("SILVERSTACK_URL")
    if not config.SILVERSTACK_API_KEY:
        missing.append("SILVERSTACK_API_KEY")

    if missing:
        print(f"[Config] Missing env vars: {', '.join(missing)}")
        print("[Config] Copy .env.example to .env and fill in your values.")
        return

    # --- Scrape all dealer sites ---
    all_products = []
    for site_name, source_id, scrape_fn in SCRAPERS:
        print(f"\nScraping {site_name}...")
        try:
            products = scrape_fn()
            # Tag each product with its source for the dashboard
            for p in products:
                p["_source"] = source_id
            print(f"[{site_name}] {len(products)} in-stock product(s)")
            all_products.extend(products)
        except Exception as e:
            print(f"[{site_name}] Scrape failed: {e}")

        # Rate-limit delay between scrapers
        time.sleep(5)

    if not all_products:
        print("\nNo in-stock products found across any site.")
    else:
        print(f"\nTotal: {len(all_products)} in-stock product(s) across {len(SCRAPERS)} site(s).")

    # --- POST products to SilverStack dashboard ---
    if all_products:
        print("\nSyncing to SilverStack dashboard...")

        # Group products by source and sync each batch
        by_source = {}
        for p in all_products:
            source = p.pop("_source")
            by_source.setdefault(source, []).append(p)

        total_sent = 0
        total_accepted = 0
        total_errors = []
        for source_id, products in by_source.items():
            result = sync_deals(products, source_id)
            total_sent += result["sent"]
            total_accepted += result["accepted"]
            total_errors.extend(result["errors"])

        print(f"\n[Dashboard] Summary: {total_sent} sent, {total_accepted} accepted, {len(total_errors)} error(s)")
        if total_errors:
            for err in total_errors:
                print(f"[Dashboard] Error: {err}")

    # --- Sync state to Gist for Telegram bot (fallback) ---
    sync_state_to_gist()

    print(f"\n{'=' * 50}")
    print(f"Done. {len(all_products)} product(s) scraped.")


if __name__ == "__main__":
    run()
