"""eBay valuation via the OFFICIAL eBay REST APIs.

Two endpoints, both keyed and compliant:
  * Browse API               -> active listings / current asking prices
  * Marketplace Insights API -> SOLD comparable transactions (best for value)

We compute a robust market value from sold comps (trimmed median), falling back
to active asking prices when sold data is unavailable. If no eBay credentials
are configured the valuator drops into MOCK mode so the rest of the pipeline can
be exercised end-to-end without live API access.

Do NOT scrape ebay.com HTML — it violates the User Agreement and the markup is
deliberately churned. Register a free app at https://developer.ebay.com instead.
"""
from __future__ import annotations

import base64
import statistics
import time
from urllib.parse import quote_plus

import httpx
import structlog

from ..config import EbayConfig
from ..models import Comparable, Listing, Valuation

log = structlog.get_logger(__name__)


class EbayValuator:
    def __init__(self, cfg: EbayConfig) -> None:
        self.cfg = cfg
        self._token: str | None = None
        self._token_expiry: float = 0.0
        self._client = httpx.Client(timeout=25.0)

    # -- public API ---------------------------------------------------------

    def value(self, listing: Listing) -> Valuation | None:
        """Return a Valuation for the listing, or None if it can't be valued."""
        if not self.cfg.enabled:
            return self._mock_value(listing)
        try:
            sold = self._search(listing.title, sold=True)
            active = self._search(listing.title, sold=False)
        except httpx.HTTPError as exc:
            log.warning("ebay.search_failed", title=listing.title, error=str(exc))
            return None
        return self._aggregate(listing, sold, active)

    # -- auth ---------------------------------------------------------------

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        creds = f"{self.cfg.client_id}:{self.cfg.client_secret}".encode()
        auth = base64.b64encode(creds).decode()
        resp = self._client.post(
            f"{self.cfg.base_url}/identity/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._token_expiry = time.time() + int(body.get("expires_in", 7200))
        return self._token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token()}",
            "X-EBAY-C-MARKETPLACE-ID": self.cfg.marketplace_id,
            "Content-Type": "application/json",
        }

    # -- search -------------------------------------------------------------

    def _search(self, query: str, sold: bool, limit: int = 25) -> list[Comparable]:
        """Query Browse (active) or Marketplace Insights (sold) for comps."""
        q = quote_plus(query)
        if sold:
            url = (
                f"{self.cfg.base_url}/buy/marketplace_insights/v1_beta/item_sales/"
                f"search?q={q}&limit={limit}"
            )
        else:
            url = f"{self.cfg.base_url}/buy/browse/v1/item_summary/search?q={q}&limit={limit}"

        resp = self._client.get(url, headers=self._headers())
        if resp.status_code == 403 and sold:
            # Marketplace Insights requires extra approval; degrade gracefully.
            log.info("ebay.insights_unavailable", note="falling back to active comps")
            return []
        resp.raise_for_status()

        items = resp.json().get("itemSales" if sold else "itemSummaries", []) or []
        comps: list[Comparable] = []
        for it in items:
            price = _price_of(it)
            if price is None:
                continue
            comps.append(
                Comparable(
                    title=it.get("title", ""),
                    price=price,
                    sold=sold,
                    url=it.get("itemWebUrl"),
                )
            )
        return comps

    # -- aggregation --------------------------------------------------------

    def _aggregate(
        self,
        listing: Listing,
        sold: list[Comparable],
        active: list[Comparable],
    ) -> Valuation | None:
        # Prefer sold comps; they reflect realized value, not aspiration.
        basis = sold or active
        if not basis:
            log.info("ebay.no_comps", title=listing.title)
            return None

        prices = sorted(c.price for c in basis)
        market_value = _trimmed_median(prices)

        # Confidence: more comps + presence of sold data => higher.
        confidence = min(1.0, len(basis) / 15.0)
        if sold:
            confidence = min(1.0, confidence + 0.2)

        sample = next((c.url for c in basis if c.url), None) or _search_link(listing.title)
        return Valuation(
            market_value=round(market_value, 2),
            comp_count=len(active) + len(sold),
            sold_count=len(sold),
            confidence=round(confidence, 2),
            sample_url=sample,
        )

    # -- mock ---------------------------------------------------------------

    def _mock_value(self, listing: Listing) -> Valuation:
        """Deterministic stand-in so the pipeline is testable without keys.

        Pretends the market resells at ~1.9x the asking price. This is for
        DEMO ONLY — it is not a real valuation. Configure eBay credentials.
        """
        mv = round(listing.price * 1.9 + 5, 2)
        return Valuation(
            market_value=mv,
            comp_count=0,
            sold_count=0,
            confidence=0.0,
            sample_url=_search_link(listing.title),
        )


def _price_of(item: dict) -> float | None:
    node = item.get("price") or item.get("lastSoldPrice") or {}
    val = node.get("value")
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _trimmed_median(prices: list[float]) -> float:
    """Median after trimming the most extreme 10% on each side to kill outliers
    (mislabeled lots, parts-only, mint-sealed collector prices)."""
    if len(prices) >= 10:
        k = max(1, len(prices) // 10)
        prices = prices[k:-k]
    return statistics.median(prices)


def _search_link(title: str) -> str:
    return f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(title)}&LH_Sold=1&LH_Complete=1"
