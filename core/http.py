"""Shared HTTP client for scrapers.

Some dealer sites (e.g. goldsilver.be) block the default ``python-requests``
User-Agent with HTTP 403. Routing every scraper through a single session that
sends realistic browser headers avoids that and keeps connections pooled.
"""

import requests

# Headers a real Chrome browser sends. A genuine User-Agent is the key field —
# goldsilver.be returns 403 for the default python-requests UA but 200 for this.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.8",
}

DEFAULT_TIMEOUT = 15

_session = requests.Session()
_session.headers.update(BROWSER_HEADERS)


def get(url: str, *, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    """GET ``url`` with browser headers and raise on HTTP errors."""
    resp = _session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp
