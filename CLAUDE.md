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

**Data flow:** `main.py` orchestrates: validate env vars → check API rate limit → fetch spot price (cached for 3h) → scrape dealer sites (sequentially, 5s delay) → evaluate each product → deduplicate against previous notifications → send Telegram alerts for new deals.

**Deployment:** GitHub Actions runs hourly via `.github/workflows/scrape.yml`. State files (`api_usage.json`, `notified_deals.json`, `spot_price_cache.json`) are persisted between runs using Actions cache. After each run, state is synced to a GitHub Gist for the Telegram bot.

**Telegram Bot:** A Cloudflare Worker (`worker/`) acts as a Telegram webhook, providing instant command responses (`/status`, `/price`, `/deals`, `/keys`, `/force`). It reads state from the GitHub Gist and replies via the Telegram API. `/force` triggers a `workflow_dispatch` on the scraper workflow.

### Key modules

- **`config.py`** — All env vars and constants. Thresholds: `MAX_PREMIUM` (15 EUR above spot per oz), `HARD_CAP` (2500 EUR absolute max). `MONTHLY_API_LIMIT = 100` (per key). `SPOT_PRICE_CACHE_HOURS = 3`. Supports up to 2 GoldAPI.io keys (`SILVER_API_KEY`, `SILVER_API_KEY_2`) for key rotation.
- **`core/calculator.py`** — `is_good_deal(price_per_oz, spot_price_per_oz, total_price)` — a product is a deal only if `price_per_oz <= spot + MAX_PREMIUM` AND `total_price <= HARD_CAP`.
- **`services/silver_price.py`** — GoldAPI.io integration (XAG/EUR). Uses `x-access-token` header. Supports key rotation: picks the first key with remaining budget via `get_available_key()`. Caches spot price in `spot_price_cache.json` for 3 hours (~8 calls/day with 2 keys).
- **`services/rate_limiter.py`** — Tracks per-key monthly API usage in `api_usage.json` (format: `{month, keys: {key_id: count}}`; auto-resets on new calendar month). Key IDs are the last 6 chars of each API key. Provides `get_available_key()` for rotation and `get_total_limit()` for combined budget. Request is counted even if the API call fails.
- **`services/notifier.py`** — Telegram Bot API with HTML parse mode.
- **`services/deal_tracker.py`** — Deduplication tracker using `notified_deals.json`. Keyed by product URL; re-notifies if price changes.
- **`scrapers/goldsilver.py`** — BeautifulSoup scraper for goldsilver.be. Paginates automatically. Assumes 1 oz per product. Stock filtering: "In voorraad" and "Product is beschikbaar met verschillende opties" are treated as in-stock; "Binnenkort in voorraad" is skipped.
- **`scrapers/argentorshop.py`** — BeautifulSoup scraper for argentorshop.be. Single-page, no pagination. Parses quantity from product name via regex (supports "N x 1 troy ounce", "N troy ounce", "N kilogram" patterns; skips unrecognized). Stock filtering: only `"Op voorraad"` is treated as in-stock.
- **`services/gist_sync.py`** — Uploads state files to a GitHub Gist after each run. Uses `GITHUB_TOKEN` and `GIST_ID` env vars. Silently skips if either is missing.
- **`worker/src/index.js`** — Cloudflare Worker that handles Telegram webhook commands. Reads state from Gist, validates chat ID, supports `/status`, `/price`, `/deals`, `/keys`, `/force`.
- **`scrapers/hollandgold.py`** — JSON-LD scraper for hollandgold.nl. Single-page, no pagination. Extracts product data from embedded `<script type="application/ld+json">` `ItemList`. Prices come as standard decimals (not European format). Parses quantity from product name ("N troy ounce"). URL pre-filters to 1 oz coins (`selectie=508`) and in-stock only (`instock=1`).

### Adding a new scraper

Create `scrapers/<dealer>.py` with a `scrape_site() -> list[dict]` function returning:
```python
{"name": str, "price_per_oz": float, "total_price": float, "quantity_oz": float, "url": str, "in_stock": bool}
```
Only return in-stock products. Register it in the `SCRAPERS` list in `main.py`.

### Important details

- **European price format** — Both scrapers parse European-format prices: dots are thousands separators, commas are decimal separators (e.g., `€ 2.725,24`). Each scraper has its own `_parse_euro()` helper.
- **Whitespace normalization** — Dealer sites include non-breaking spaces (`\xa0`) in stock status and price text. Both scrapers use a `_normalize()` helper to collapse all whitespace before comparison.
- **`api_usage.json`**, **`notified_deals.json`**, **`spot_price_cache.json`** — Gitignored, created at runtime in the project root.
- **All HTTP requests use 10-second timeouts.**
- Services return `None` on API errors; scrapers raise exceptions caught by `main.py`.
- **Telegram Bot setup** — Deploy worker with `cd worker && npm install && npx wrangler deploy`. Set secrets via `wrangler secret put` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GITHUB_TOKEN`, `GIST_ID`, `GITHUB_REPO`). Register webhook: `https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WORKER_URL>`. Add `GH_PAT` and `GIST_ID` as GitHub Actions secrets.
