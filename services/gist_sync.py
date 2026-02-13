import json
import os

import requests

import config

STATE_FILES = ["api_usage.json", "spot_price_cache.json", "notified_deals.json"]


def sync_state_to_gist():
    """Upload state files to a GitHub Gist for the Telegram bot worker to read."""
    if not config.GITHUB_TOKEN or not config.GIST_ID:
        print("[Gist Sync] Skipped (GITHUB_TOKEN or GIST_ID not set)")
        return

    files = {}
    for filename in STATE_FILES:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                files[filename] = {"content": f.read()}

    if not files:
        print("[Gist Sync] No state files to sync")
        return

    try:
        resp = requests.patch(
            f"https://api.github.com/gists/{config.GIST_ID}",
            headers={
                "Authorization": f"token {config.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
            json={"files": files},
            timeout=10,
        )
        resp.raise_for_status()
        print(f"[Gist Sync] Uploaded {len(files)} state file(s)")
    except Exception as e:
        print(f"[Gist Sync] Failed: {e}")
