"""Domain models shared across the pipeline stages."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Listing(BaseModel):
    """A normalized marketplace listing emitted by a Source adapter."""

    source: str                       # "craigslist", "marktplaats", ...
    title: str
    price: float = Field(ge=0)        # asking/buy price (>= 0; 0 = free listing)
    location: str | None = None
    url: str
    category: str | None = None
    discovered_at: datetime = Field(default_factory=_now)

    @field_validator("url")
    @classmethod
    def _require_web_url(cls, v: str) -> str:
        """Reject non-web schemes (javascript:, file:, data:, relative) coming
        from untrusted source feeds before they reach alert payloads."""
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(f"url must be http(s), got: {v[:40]!r}")
        return v

    @property
    def fingerprint(self) -> str:
        """Stable id for dedupe. Prefer the URL; fall back to a content hash."""
        basis = self.url or f"{self.source}|{self.title}|{self.price}"
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()


class Comparable(BaseModel):
    """A single eBay comp (active or sold) used for valuation."""

    title: str
    price: float
    sold: bool
    url: str | None = None


class Valuation(BaseModel):
    """Result of cross-referencing a listing against eBay."""

    market_value: float = Field(ge=0)  # robust resale estimate (>= 0)
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
    vat: float = 0.0                  # margin-scheme VAT (0 when disabled)

    def summary(self) -> str:
        lst = self.listing
        return (
            f"{lst.title}\n"
            f"  buy {self.buy_price:,.2f} → resale ~{self.resale_value:,.2f} "
            f"| net {self.net_profit:,.2f} ({self.margin:.0%})\n"
            f"  source: {lst.url}"
        )
