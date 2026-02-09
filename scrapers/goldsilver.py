import re

import requests
from bs4 import BeautifulSoup

BASE_URL = (
    "https://goldsilver.be/nl/84-1-oz-30-gr"
    "?orderby=price&orderway=asc&orderby1=quantity"
)

IN_STOCK_TEXTS = {
    "In voorraad",
    "Product is beschikbaar met verschillende opties",
}


def _normalize(text: str) -> str:
    """Collapse all whitespace (including \xa0) into single regular spaces."""
    return re.sub(r"\s+", " ", text).strip()


def _scrape_page(url: str) -> list[dict]:
    """Scrape a single page and return in-stock products."""
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    products = []

    for card in soup.select("li.ajax_block_product"):
        # --- Stock status (strict match) ---
        avail_tag = card.select_one("span.availability")
        if not avail_tag:
            continue
        stock_text = _normalize(avail_tag.get_text())
        if stock_text not in IN_STOCK_TEXTS:
            continue

        # --- Product name & URL ---
        link_tag = card.select_one("h5 a")
        if not link_tag:
            continue
        name = link_tag.get_text(strip=True)
        product_url = link_tag.get("href", "")

        # --- Price (European format: "85,80 €") ---
        price_tag = card.select_one("span.price.product-price")
        if not price_tag:
            continue
        price_text = price_tag.get_text(strip=True)
        try:
            price = float(
                price_text.replace("\xa0", "")
                .replace("€", "")
                .replace(".", "")   # thousands separator
                .replace(",", ".")  # decimal separator
                .strip()
            )
        except ValueError:
            continue

        products.append({
            "name": name,
            "price_per_oz": price,
            "total_price": price,
            "quantity_oz": 1.0,
            "url": product_url,
            "in_stock": True,
        })

    return products


def _get_last_page(url: str) -> int:
    """Detect the highest page number from pagination links."""
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()

    pages = {1}
    for match in re.finditer(r"[&?]p=(\d+)", resp.text):
        pages.add(int(match.group(1)))
    return max(pages)


def scrape_site() -> list[dict]:
    """Scrape all pages of goldsilver.be for in-stock 1 oz silver products.

    Returns a list of dicts with keys: name, price, url, in_stock.
    """
    last_page = _get_last_page(BASE_URL)
    print(f"[goldsilver.be] {last_page} page(s) detected.")

    all_products = []
    for page in range(1, last_page + 1):
        url = BASE_URL if page == 1 else f"{BASE_URL}&p={page}"
        products = _scrape_page(url)
        print(f"[goldsilver.be] Page {page}: {len(products)} product(s)")
        all_products.extend(products)

    return all_products
