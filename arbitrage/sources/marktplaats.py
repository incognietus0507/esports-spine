"""Marktplaats source — the dominant NL marketplace.

Marktplaats has **no public scraping-friendly feed**. Automated collection of
its public pages is prohibited by its Terms of Service, and it is protected by
bot detection. It *does* offer official access for professional sellers/partners
(the Admarkt / Marktplaats API programs) and CSV/feed exports for business
accounts.

So this adapter follows the same stance as the Craigslist one's *intent*
(compliant data only) but the *mechanism* must be an authorized source — it does
NOT scrape marktplaats.nl. You provide a ``feed_loader`` callable that returns
raw item dicts from a source you are permitted to use (official API response,
a business CSV export, or a licensed data feed); the adapter normalizes them
into ``Listing`` objects.

See COMPLIANCE.md and STRATEGY-NL.md. If you have no authorized feed, the
adapter stays disabled and raises, rather than scraping.
"""
from __future__ import annotations

from collections.abc import Callable

import structlog

from ..models import Listing
from .base import Source, SourceConfigurationError

log = structlog.get_logger(__name__)

# Raw item -> ((title, price, url) extracted). A loader returns a list of dicts;
# we map them defensively so a malformed record never crashes the run.
FeedLoader = Callable[[], list[dict]]


class MarktplaatsDisabled(SourceConfigurationError):
    """Raised when no authorized feed is configured, to keep the ToS boundary
    explicit instead of silently falling back to scraping. As a
    SourceConfigurationError it fails the run fast rather than being demoted
    to a per-run warning."""


class MarktplaatsSource(Source):
    name = "marktplaats"

    def __init__(
        self,
        feed_loader: FeedLoader | None = None,
        categories: list[str] | None = None,
    ) -> None:
        self.feed_loader = feed_loader
        self.categories = categories or []

    def fetch(self, limit: int) -> list[Listing]:
        if self.feed_loader is None:
            raise MarktplaatsDisabled(
                "MarktplaatsSource has no authorized feed_loader. Marktplaats "
                "prohibits scraping in its ToS; supply an official API/CSV/"
                "licensed-feed loader instead. See COMPLIANCE.md / STRATEGY-NL.md."
            )

        try:
            raw = self.feed_loader()
        except Exception as exc:  # noqa: BLE001 — never let a feed crash the run
            log.warning("marktplaats.feed_failed", error=str(exc), exc_info=True)
            return []

        listings: list[Listing] = []
        for item in raw:
            listing = _normalize(item)
            if listing is not None:
                listings.append(listing)
            if len(listings) >= limit:
                break
        log.info("marktplaats.fetched", count=len(listings))
        return listings


# Defensive caps for untrusted feed data (oversized strings would bloat logs
# and overflow alert payload limits; deep dicts could exhaust the stack).
_MAX_TITLE = 500
_MAX_LOCATION = 200
_MAX_PRICE_STR = 64
_MAX_PRICE_DEPTH = 3


def _normalize(item: dict) -> Listing | None:
    """Map an authorized-feed record into a Listing. Returns None if the record
    lacks the minimum fields (title, price, valid url) — we can't value those."""
    title = (item.get("title") or item.get("name") or "").strip()[:_MAX_TITLE]
    url = item.get("url") or item.get("link") or ""
    price_raw = item.get("price")
    if price_raw is None:
        price_raw = item.get("priceInfo")
    price = _coerce_price(price_raw)
    location = item.get("location") or item.get("city")
    if location is not None:
        location = str(location)[:_MAX_LOCATION]

    if not title or not url or price is None:
        log.debug("marktplaats.dropped_record", has_title=bool(title),
                  has_url=bool(url), has_price=price is not None)
        return None
    try:
        return Listing(
            source=MarktplaatsSource.name,
            title=title,
            price=price,
            location=location,
            url=url,
            category=item.get("category"),
        )
    except ValueError as exc:  # e.g. non-web url or negative price rejected by model
        log.debug("marktplaats.invalid_listing", error=str(exc))
        return None


def _coerce_price(value: object, _depth: int = 0) -> float | None:
    """Accept floats, ints, '€ 40,00'/'1.0' strings, or {'priceCents': 4000}
    dicts. Returns None on anything unparseable. Bounded against deep/huge
    inputs from an untrusted feed."""
    if value is None or _depth > _MAX_PRICE_DEPTH:
        return None
    if isinstance(value, bool):  # bool is an int subclass — reject explicitly
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        cents = value.get("priceCents")
        if cents is None:
            cents = value.get("amountCents")
        if isinstance(cents, (int, float)) and not isinstance(cents, bool):
            return float(cents) / 100.0
        nested = value.get("amount")
        if nested is None:
            nested = value.get("value")
        return _coerce_price(nested, _depth + 1)
    if isinstance(value, str):
        if len(value) > _MAX_PRICE_STR:
            return None
        cleaned = value.replace("€", "").replace("EUR", "").strip()
        # Disambiguate separators: NL "1.234,56" vs plain decimal "1.0".
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")  # NL thousands+decimal
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")                   # NL decimal only
        # else: already a standard decimal/integer — leave dots intact
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None
