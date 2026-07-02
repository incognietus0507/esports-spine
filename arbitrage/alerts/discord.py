"""Discord webhook alerter."""
from __future__ import annotations

import httpx

from ..models import Opportunity
from .base import Alerter


class DiscordAlerter(Alerter):
    name = "discord"

    def __init__(self, webhook_url: str, symbol: str = "€") -> None:
        self.webhook_url = webhook_url
        self.symbol = symbol

    def send(self, opp: Opportunity) -> None:
        l = opp.listing
        s = self.symbol
        embed = {
            "title": f"💰 Arbitrage: {l.title[:240]}",
            "url": l.url,
            "color": 0x2ECC71,
            "fields": [
                {"name": "Buy price", "value": f"{s}{opp.buy_price:,.2f}", "inline": True},
                {"name": "Resale (est.)", "value": f"{s}{opp.resale_value:,.2f}", "inline": True},
                {"name": "Net profit", "value": f"{s}{opp.net_profit:,.2f}", "inline": True},
                {"name": "Margin", "value": f"{opp.margin:.0%}", "inline": True},
                {"name": "Location", "value": l.location or "—", "inline": True},
                {"name": "Comps", "value": f"{opp.valuation.comp_count} "
                                           f"({opp.valuation.sold_count} sold)", "inline": True},
                {"name": "Source listing", "value": l.url, "inline": False},
                {"name": "eBay comps", "value": opp.valuation.sample_url or "—", "inline": False},
            ],
            "footer": {"text": f"{l.source} · confidence {opp.valuation.confidence:.0%}"},
        }
        resp = httpx.post(self.webhook_url, json={"embeds": [embed]}, timeout=15.0)
        resp.raise_for_status()
