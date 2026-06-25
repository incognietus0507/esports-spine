"""Domain models shared across the pipeline stages."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from pydantic import BaseModel, Field, HttpUrl


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Listing(BaseModel):
    """A normalized marketplace listing emitted by a Source adapter."""

    source: str                       # "craigslist", "facebook", ...
    title: str
    price: float                      # asking/buy price in USD
    location: str | None = None
    url: str
    category: str | None = None
    discovered_at: datetime = Field(default_factory=_now)

    @property
    def fingerprint(self) -> str:
        """Stable id for dedupe. Prefer the URL; fall back to a content hash."""
        basis = self.url or f"{self.source}|{self.title}|{self.price}"
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()


class Comparable(BaseModel):
    """A single eBay comp (active or sold) used for valuation."""

    title: str
    price: float
    sold: bool
    url: str | None = None


class Valuation(BaseModel):
    """Result of cross-referencing a listing against eBay."""

    market_value: float               # robust resale estimate (USD)
    comp_count: int
    sold_count: int
    confidence: float                 # 0..1, higher = more/closer comps
    sample_url: str | None = None     # a representative eBay search/listing link


class Opportunity(BaseModel):
    """A listing that cleared the profit threshold — ready to alert on."""

    listing: Listing
    valuation: Valuation
    buy_price: float
    resale_value: float
    fees: float
    shipping: float
    acquisition: float
    net_profit: float
    margin: float                     # net_profit / buy_price

    def summary(self) -> str:
        l = self.listing
        return (
            f"{l.title}\n"
            f"  buy ${self.buy_price:,.2f} → resale ~${self.resale_value:,.2f} "
            f"| net ${self.net_profit:,.2f} ({self.margin:.0%})\n"
            f"  source: {l.url}"
        )
