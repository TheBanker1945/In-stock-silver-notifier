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

SilverScout is a "dumb scraper" that monitors silver bullion dealer websites and sends raw product data to the SilverStack dashboard, which handles deal evaluation, spot price tracking, and notifications. Currency is EUR throughout.

**Data flow:** `main.py` orchestrates: validate env vars → scrape dealer sites (sequentially, 5s delay) → POST all raw products to SilverStack dashboard → sync state to Gist (fallback for Telegram bot) → log summary.

**Deployment:** GitHub Actions runs hourly via `.github/workflows/scrape.yml`. State files (`api_usage.json`, `notified_deals.json`, `spot_price_cache.json`) are persisted between runs using Actions cache. After each run, state is synced to a GitHub Gist for the Telegram bot.

**Telegram Bot:** A Cloudflare Worker (`worker/`) acts as a Telegram webhook, providing instant command responses (`/status`, `/price`, `/deals`, `/keys`, `/force`). It reads state from the GitHub Gist and replies via the Telegram API. `/force` triggers a `workflow_dispatch` on the scraper workflow.

### Key modules

- **`config.py`** — All env vars and constants. Primary config: `SILVERSTACK_URL` and `SILVERSTACK_API_KEY` for the dashboard integration. Legacy constants (`MAX_PREMIUM`, `HARD_CAP`, `MONTHLY_API_LIMIT`, `SPOT_PRICE_CACHE_HOURS`) and GoldAPI keys are kept for fallback modules.
- **`services/dashboard_sync.py`** — SilverStack dashboard integration. `sync_deals(products, source)` POSTs products in batches of 50. Uses `X-API-Key` header auth. Returns `{sent, accepted, errors}` summary. Logs errors but never crashes the scraper.
- **`services/gist_sync.py`** — Uploads state files to a GitHub Gist after each run. Uses `GITHUB_TOKEN` and `GIST_ID` env vars. Silently skips if either is missing.
- **`worker/src/index.js`** — Cloudflare Worker that handles Telegram webhook commands. Reads state from Gist, validates chat ID, supports `/status`, `/price`, `/deals`, `/keys`, `/force`.

### Legacy modules (kept as fallback, not used in main flow)

- **`core/calculator.py`** — `is_good_deal()` deal evaluation. Now handled by SilverStack dashboard.
- **`services/silver_price.py`** — GoldAPI.io spot price fetching. Dashboard has its own live spot price.
- **`services/rate_limiter.py`** — Per-key monthly API usage tracking. No longer needed without GoldAPI calls.
- **`services/notifier.py`** — Direct Telegram notifications. Dashboard handles notifications now.
- **`services/deal_tracker.py`** — Deal deduplication via `notified_deals.json`. Dashboard handles dedup now.

### Scrapers

- **`scrapers/goldsilver.py`** — BeautifulSoup scraper for goldsilver.be. Paginates automatically. Assumes 1 oz per product. Stock filtering: "In voorraad" and "Product is beschikbaar met verschillende opties" are treated as in-stock; "Binnenkort in voorraad" is skipped.
- **`scrapers/argentorshop.py`** — BeautifulSoup scraper for argentorshop.be. Single-page, no pagination. Parses quantity from product name via regex (supports "N x 1 troy ounce", "N troy ounce", "N kilogram" patterns; skips unrecognized). Stock filtering: only `"Op voorraad"` is treated as in-stock.
- **`scrapers/hollandgold.py`** — JSON-LD scraper for hollandgold.nl. Single-page, no pagination. Extracts product data from embedded `<script type="application/ld+json">` `ItemList`. Prices come as standard decimals (not European format). Parses quantity from product name ("N troy ounce"). URL pre-filters to 1 oz coins (`selectie=508`) and in-stock only (`instock=1`).

### Adding a new scraper

Create `scrapers/<dealer>.py` with a `scrape_site() -> list[dict]` function returning:
```python
{"name": str, "price_per_oz": float, "total_price": float, "quantity_oz": float, "url": str, "in_stock": bool}
```
Only return in-stock products. Register it in the `SCRAPERS` list in `main.py` with a tuple of `(display_name, source_id, scrape_fn)` where `source_id` is sent to the dashboard (e.g. `"dealer_tld"`).

### Dashboard API contract

Each scraper's products are POSTed to `POST {SILVERSTACK_URL}/api/deals` as:
```json
[{"title": "...", "price_eur": 123.45, "url": "...", "source": "goldsilver_be", "image_url": null}]
```
The dashboard calculates spot price, premium, and deal quality — the scraper does NOT send these fields.

### Important details

- **European price format** — Both scrapers parse European-format prices: dots are thousands separators, commas are decimal separators (e.g., `€ 2.725,24`). Each scraper has its own `_parse_euro()` helper.
- **Whitespace normalization** — Dealer sites include non-breaking spaces (`\xa0`) in stock status and price text. Both scrapers use a `_normalize()` helper to collapse all whitespace before comparison.
- **`api_usage.json`**, **`notified_deals.json`**, **`spot_price_cache.json`** — Gitignored, created at runtime in the project root.
- **All HTTP requests use 10-second timeouts.**
- Services return `None` on API errors; scrapers raise exceptions caught by `main.py`.
- **Telegram Bot setup** — Deploy worker with `cd worker && npm install && npx wrangler deploy`. Set secrets via `wrangler secret put` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GITHUB_TOKEN`, `GIST_ID`, `GITHUB_REPO`). Register webhook: `https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WORKER_URL>`. Add `GH_PAT` and `GIST_ID` as GitHub Actions secrets.
