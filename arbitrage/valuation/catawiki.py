"""Catawiki valuation — NOTE / placeholder, not a live scraper.

For the NL strategy, Catawiki is the best resale + valuation channel for
*antiques, design, watches, art, and collectibles* (its auctions attract
collector demand that pushes realized prices above generic marketplaces).

However, Catawiki does **not** expose a public price/comps API, and scraping its
site is prohibited by its Terms of Service. So there is no compliant automated
"average sold value" source here the way eBay's Marketplace Insights API
provides one.

Practical compliant options (in order):
  1. **eBay.de comps** as the automated baseline (see ``ebay.py``; set
     ``EBAY_MARKETPLACE_ID=EBAY_DE``). Good enough for games, electronics,
     cameras, tools, mainstream items.
  2. **Discogs API** for vinyl/CDs — it has an official, documented API with
     real price statistics. Worth a dedicated adapter if vinyl is your lane.
  3. **Manual Catawiki check** for high-value design/antiques/watches: the
     pipeline alerts you on the eBay.de-based estimate, and you confirm against
     recent Catawiki results by hand before buying. This keeps a human in the
     loop exactly where items are rarest and valuation is hardest.

This module deliberately raises rather than scraping, to keep that boundary
explicit. Wire in a Catawiki *seller* integration here only if you have one.
"""
from __future__ import annotations

from ..models import Listing, Valuation


class CatawikiValuationUnavailable(RuntimeError):
    pass


def value(listing: Listing) -> Valuation | None:  # noqa: ARG001
    """Placeholder. No compliant automated Catawiki comps source exists; use
    eBay.de/Discogs for automation and Catawiki manually for rare items."""
    raise CatawikiValuationUnavailable(
        "No compliant automated Catawiki comps source. Use the eBay.de "
        "valuator for automation (EBAY_MARKETPLACE_ID=EBAY_DE) and confirm "
        "high-value design/antiques against Catawiki manually. See module docs."
    )
