import json
import re

import requests
from bs4 import BeautifulSoup

URL = (
    "https://www.hollandgold.nl/zilver-kopen/zilveren-munten-kopen.html"
    "?selectie=508&instock=1&sort=price.asc"
)


def _parse_quantity_oz(name: str) -> float | None:
    """Extract troy ounce quantity from product name.

    Examples:
      "Britannia 1 troy ounce zilveren munt" → 1.0
      "10 troy ounce zilveren munt"          → 10.0
    """
    m = re.search(r"(\d+)\s*troy ounce", name, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def scrape_site() -> list[dict]:
    """Scrape hollandgold.nl for in-stock silver coin products via JSON-LD.

    Returns a list of dicts with keys:
        name, price_per_oz, total_price, quantity_oz, url, in_stock.
    """
    resp = requests.get(URL, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    products = []

    # Find JSON-LD ItemList in <script type="application/ld+json"> tags
    for script_tag in soup.find_all("script", type="application/ld+json"):
        try:
            raw = json.loads(script_tag.string)
        except (json.JSONDecodeError, TypeError):
            continue

        # JSON-LD may be a single object or a list of objects
        entries = raw if isinstance(raw, list) else [raw]
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("@type") != "ItemList":
                continue

            for item in entry.get("itemListElement", []):
                product = item if item.get("@type") == "Product" else item.get("item", {})
                if product.get("@type") != "Product":
                    continue

                offers = product.get("offers", {})
                if offers.get("availability") != "InStock":
                    continue

                name = product.get("name", "")
                product_url = offers.get("url", "")

                try:
                    total_price = float(offers.get("price", 0))
                except (ValueError, TypeError):
                    continue
                if total_price <= 0:
                    continue

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
