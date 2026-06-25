"""Craigslist source — uses the public RSS search feeds Craigslist publishes.

Craigslist has no official API, but it *does* expose RSS for search results
(``&format=rss``). That is data offered for machine consumption, so we restrict
ourselves to it and stay polite: descriptive UA, caching, backoff, hard caps.

See COMPLIANCE.md before increasing volume or adding regions.
"""
from __future__ import annotations

import time

import feedparser
import httpx
import structlog

from ..models import Listing
from .base import Source

log = structlog.get_logger(__name__)

# Craigslist category codes (see craigslist.org category pages):
#   ata = antiques, vgc = video gaming, sga = general for sale (fallback)
_CATEGORY_NAMES = {"ata": "antiques", "vgc": "video games", "sga": "for sale"}

# Be a good citizen: identify the bot and give a contact path.
_UA = "retail-arbitrage-tool/0.1 (personal use; +https://example.com/contact)"


class CraigslistSource(Source):
    name = "craigslist"

    def __init__(
        self,
        region: str,
        categories: list[str],
        search_terms: list[str] | None = None,
        request_delay: float = 3.0,
    ) -> None:
        self.region = region
        self.categories = categories
        self.search_terms = search_terms or []
        self.request_delay = request_delay
        self._client = httpx.Client(
            headers={"User-Agent": _UA},
            timeout=20.0,
            follow_redirects=True,
        )

    def _feed_url(self, category: str) -> str:
        query = "+".join(self.search_terms) if self.search_terms else ""
        base = f"https://{self.region}.craigslist.org/search/{category}"
        params = "format=rss" + (f"&query={query}" if query else "")
        return f"{base}?{params}"

    def fetch(self, limit: int) -> list[Listing]:
        listings: list[Listing] = []
        for category in self.categories:
            if len(listings) >= limit:
                break
            listings.extend(self._fetch_category(category, limit - len(listings)))
            time.sleep(self.request_delay)  # throttle between categories
        return listings[:limit]

    def _fetch_category(self, category: str, limit: int) -> list[Listing]:
        url = self._feed_url(category)
        try:
            resp = self._get_with_backoff(url)
        except httpx.HTTPError as exc:
            log.warning("craigslist.fetch_failed", category=category, error=str(exc))
            return []

        feed = feedparser.parse(resp.text)
        out: list[Listing] = []
        for entry in feed.entries[:limit]:
            price = _extract_price(entry)
            if price is None:
                continue  # can't value an item with no price
            out.append(
                Listing(
                    source=self.name,
                    title=entry.get("title", "").strip(),
                    price=price,
                    location=_extract_location(entry),
                    url=entry.get("link", ""),
                    category=_CATEGORY_NAMES.get(category, category),
                )
            )
        log.info("craigslist.fetched", category=category, count=len(out))
        return out

    def _get_with_backoff(self, url: str, attempts: int = 4) -> httpx.Response:
        delay = 2.0
        last: Exception | None = None
        for _ in range(attempts):
            resp = self._client.get(url)
            if resp.status_code in (403, 429):
                # Block / rate-limit signal: back off, do NOT hammer or rotate IPs.
                log.warning("craigslist.throttled", status=resp.status_code, sleep=delay)
                time.sleep(delay)
                delay *= 2
                last = httpx.HTTPStatusError(
                    "throttled", request=resp.request, response=resp
                )
                continue
            resp.raise_for_status()
            return resp
        raise last or httpx.HTTPError("craigslist request failed")


def _extract_price(entry) -> float | None:
    """Craigslist RSS puts the price in the title as e.g. '$120 ...'."""
    title = entry.get("title", "")
    for token in title.replace(",", "").split():
        if token.startswith("$"):
            try:
                return float(token[1:])
            except ValueError:
                continue
    return None


def _extract_location(entry) -> str | None:
    # Location is often in a trailing "(neighborhood)" in the title.
    title = entry.get("title", "")
    if "(" in title and title.rstrip().endswith(")"):
        return title[title.rfind("(") + 1 : -1].strip()
    return None
