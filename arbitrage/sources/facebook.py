"""Facebook Marketplace source — INTENTIONALLY DISABLED.

There is no public Marketplace API, and Facebook's Terms of Service expressly
prohibit automated collection of its data. Marketplace also sits behind a login
wall and aggressive bot detection. Scraping it means impersonating a logged-in
human, which is a clear ToS violation with real legal exposure.

This adapter therefore refuses to run. It exists to document the boundary and to
keep the Source interface symmetric. See COMPLIANCE.md for legitimate
alternatives (Facebook's own saved-search notifications, API-backed platforms,
or a licensed data provider).

If you have your OWN compliant, authorized source of Marketplace-equivalent data
(e.g. a signed agreement or an export you are permitted to use), implement
``fetch`` to read from THAT source — not by scraping facebook.com.
"""
from __future__ import annotations

from ..models import Listing
from .base import Source


class FacebookMarketplaceDisabled(RuntimeError):
    """Raised to make the ToS boundary explicit and un-bypassable by accident."""


class FacebookMarketplaceSource(Source):
    name = "facebook"

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def fetch(self, limit: int) -> list[Listing]:  # noqa: ARG002
        raise FacebookMarketplaceDisabled(
            "Facebook Marketplace scraping is disabled: it violates Facebook's "
            "Terms of Service and requires bypassing a login wall and bot "
            "detection. See COMPLIANCE.md for compliant alternatives. To use "
            "Marketplace data, supply your own authorized data source here."
        )
