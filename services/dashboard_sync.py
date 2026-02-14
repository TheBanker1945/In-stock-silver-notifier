import requests

import config


def sync_deals(products: list[dict], source: str) -> dict:
    """POST products to the SilverStack dashboard API in batches of 50.

    Returns a summary dict: {sent: int, accepted: int, errors: list[str]}
    """
    if not config.SILVERSTACK_URL or not config.SILVERSTACK_API_KEY:
        print("[Dashboard] Skipped (SILVERSTACK_URL or SILVERSTACK_API_KEY not set)")
        return {"sent": 0, "accepted": 0, "errors": ["Missing dashboard config"]}

    url = f"{config.SILVERSTACK_URL.rstrip('/')}/api/deals"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": config.SILVERSTACK_API_KEY,
    }

    summary = {"sent": 0, "accepted": 0, "errors": []}

    # Process in batches of 50
    for i in range(0, len(products), 50):
        batch = products[i : i + 50]
        payload = [
            {
                "title": p["name"],
                "price_eur": p["total_price"],
                "url": p["url"],
                "source": source,
                "image_url": None,
            }
            for p in batch
        ]

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            batch_accepted = data.get("accepted", len(batch))
            summary["sent"] += len(batch)
            summary["accepted"] += batch_accepted
            print(f"[Dashboard] Batch {i // 50 + 1}: sent {len(batch)}, accepted {batch_accepted}")
        except requests.RequestException as e:
            summary["sent"] += len(batch)
            summary["errors"].append(str(e))
            print(f"[Dashboard] Batch {i // 50 + 1} failed: {e}")

    return summary
