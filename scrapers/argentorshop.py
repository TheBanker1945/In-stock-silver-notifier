import re

import requests
from bs4 import BeautifulSoup

URL = "https://www.argentorshop.be/nl/zilver-kopen/zilveren-munten-kopen/"

TROY_OZ_PER_KG = 32.1507


def _normalize(text: str) -> str:
    """Collapse all whitespace (including \xa0) into single regular spaces."""
    return re.sub(r"\s+", " ", text).strip()


def _parse_euro(text: str) -> float | None:
    """Parse European price string like '€ 2.725,24' into a float."""
    try:
        return float(
            text.replace("\xa0", "")
            .replace("€", "")
            .replace(".", "")   # thousands separator
            .replace(",", ".")  # decimal separator
            .strip()
        )
    except ValueError:
        return None


def _parse_quantity_oz(name: str) -> float | None:
    """Extract troy ounce quantity from product name.

    Patterns:
      "500 x 1 troy ounce" / "250 x 1 once troy" → 500 / 250
      "10 troy ounce"                              → 10
      "1 kilogram"                                 → 32.15
    """
    # "N x 1 troy ounce" or "N x 1 once troy"
    m = re.search(r"(\d+)\s*x\s*1\s*(?:troy ounce|once troy)", name, re.IGNORECASE)
    if m:
        return float(m.group(1))

    # "N troy ounce"
    m = re.search(r"(\d+)\s*troy ounce", name, re.IGNORECASE)
    if m:
        return float(m.group(1))

    # "N kilogram"
    m = re.search(r"(\d+)\s*kilogram", name, re.IGNORECASE)
    if m:
        return float(m.group(1)) * TROY_OZ_PER_KG

    return None


def scrape_site() -> list[dict]:
    """Scrape argentorshop.be for in-stock silver coin products.

    Returns a list of dicts with keys:
        name, price_per_oz, total_price, quantity_oz, url, in_stock.
    Only products marked "Op voorraad" are included.
    """
    resp = requests.get(URL, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    products = []

    for card in soup.select(".product-item"):
        # --- Stock status ---
        stock_tag = card.select_one("span.text-green-700")
        if not stock_tag:
            continue
        stock_text = _normalize(stock_tag.get_text())
        if stock_text != "Op voorraad":
            continue

        # --- Product name & URL ---
        link_tag = card.select_one("a.product-item-link")
        if not link_tag:
            continue
        name = link_tag.get_text(strip=True)
        product_url = link_tag.get("href", "")

        # --- Total price ---
        price_tag = card.select_one("span.price")
        if not price_tag:
            continue
        total_price = _parse_euro(price_tag.get_text(strip=True))
        if total_price is None:
            continue

        # --- Quantity from product name ---
        quantity_oz = _parse_quantity_oz(name)
        if not quantity_oz:
            continue

        price_per_oz = total_price / quantity_oz

        products.append({
            "name": name,
            "price_per_oz": round(price_per_oz, 2),
            "total_price": total_price,
            "quantity_oz": round(quantity_oz, 2),
            "url": product_url,
            "in_stock": True,
        })

    return products
