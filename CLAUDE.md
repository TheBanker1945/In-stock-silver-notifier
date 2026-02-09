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

SilverScout monitors silver bullion dealer websites, compares prices to the live spot price, and sends Telegram alerts for good deals. Currency is EUR throughout.

**Data flow:** `main.py` orchestrates: validate env vars → check API rate limit → fetch spot price → scrape dealer sites (sequentially, 5s delay) → evaluate each product → send Telegram alerts for deals.

### Key modules

- **`config.py`** — All env vars and constants. Thresholds: `MAX_PREMIUM` (15 EUR above spot per oz), `HARD_CAP` (2500 EUR absolute max). `MONTHLY_API_LIMIT = 100`.
- **`core/calculator.py`** — `is_good_deal(price_per_oz, spot_price_per_oz, total_price)` — a product is a deal only if `price_per_oz <= spot + MAX_PREMIUM` AND `total_price <= HARD_CAP`.
- **`services/silver_price.py`** — GoldAPI.io integration (XAG/EUR). Uses `x-access-token` header. Rate-limited to 100 requests/month (free tier).
- **`services/rate_limiter.py`** — Tracks monthly API usage in `api_usage.json` (auto-resets on new calendar month). Request is counted even if the API call fails.
- **`services/notifier.py`** — Telegram Bot API with HTML parse mode.
- **`scrapers/goldsilver.py`** — BeautifulSoup scraper for goldsilver.be. Paginates automatically. Assumes 1 oz per product. Stock filtering: "In voorraad" and "Product is beschikbaar met verschillende opties" are treated as in-stock; "Binnenkort in voorraad" is skipped.
- **`scrapers/argentorshop.py`** — BeautifulSoup scraper for argentorshop.be. Single-page, no pagination. Parses quantity from product name via regex (supports "N x 1 troy ounce", "N troy ounce", "N kilogram" patterns; skips unrecognized). Stock filtering: only `"Op voorraad"` is treated as in-stock.

### Adding a new scraper

Create `scrapers/<dealer>.py` with a `scrape_site() -> list[dict]` function returning:
```python
{"name": str, "price_per_oz": float, "total_price": float, "quantity_oz": float, "url": str, "in_stock": bool}
```
Only return in-stock products. Register it in the `SCRAPERS` list in `main.py`.

### Important details

- **European price format** — Both scrapers parse European-format prices: dots are thousands separators, commas are decimal separators (e.g., `€ 2.725,24`). Each scraper has its own `_parse_euro()` helper.
- **Whitespace normalization** — Dealer sites include non-breaking spaces (`\xa0`) in stock status and price text. Both scrapers use a `_normalize()` helper to collapse all whitespace before comparison.
- **`api_usage.json`** — Gitignored, created at runtime in the project root.
- **All HTTP requests use 10-second timeouts.**
- Services return `None` on API errors; scrapers raise exceptions caught by `main.py`.
