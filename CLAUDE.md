# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Project

```bash
pip install -r requirements.txt
cp .env.example .env  # then fill in API keys
python main.py
```

No test framework is configured yet. No linter/formatter is configured.

## Architecture

SilverScout monitors silver bullion dealer websites, compares prices to the live spot price, and sends Telegram alerts for good deals.

**Data flow:** `main.py` orchestrates: fetch spot price → scrape dealer sites → evaluate each product → notify on deals.

### Key modules

- **`config.py`** — All env vars and constants. Thresholds: `MAX_PREMIUM` (EUR above spot), `HARD_CAP` (absolute max EUR). Currency is EUR throughout.
- **`core/calculator.py`** — `is_good_deal(price, spot)` — a product is a deal only if price ≤ spot + MAX_PREMIUM AND price ≤ HARD_CAP.
- **`services/silver_price.py`** — GoldAPI.io integration (XAG/EUR). Uses `x-access-token` header. Rate-limited to 100 requests/month (free tier).
- **`services/rate_limiter.py`** — Tracks monthly API usage in `api_usage.json` (auto-resets on new calendar month). Request is counted even if the API call fails.
- **`services/notifier.py`** — Telegram Bot API with HTML parse mode.
- **`scrapers/goldsilver.py`** — BeautifulSoup scraper for goldsilver.be. Paginates automatically. Stock filtering: "In voorraad" and "Product is beschikbaar met verschillende opties" are treated as in-stock; "Binnenkort in voorraad" is skipped.

### Adding a new scraper

Create `scrapers/<dealer>.py` with a `scrape_site() -> list[dict]` function returning `{'name': str, 'price': float, 'url': str, 'in_stock': bool}`. Then call it from `main.py` alongside the existing scrapers.

### Important details

- Prices on goldsilver.be use European format (`85,80 €`) — dots are thousands separators, commas are decimal separators.
- The site uses `<span class="availability">` for stock status, with non-breaking spaces (`\xa0`) in some entries — text must be normalized before comparison.
- `api_usage.json` is gitignored and created at runtime in the project root.
