"""SMTP email alerter."""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

from ..models import Opportunity
from .base import Alerter


class EmailAlerter(Alerter):
    name = "email"

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        sender: str,
        recipient: str,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sender = sender
        self.recipient = recipient

    def send(self, opp: Opportunity) -> None:
        l = opp.listing
        body = (
            f"{l.title}\n\n"
            f"Buy price:      ${opp.buy_price:,.2f}\n"
            f"Resale (est.):  ${opp.resale_value:,.2f}\n"
            f"Platform fees:  ${opp.fees:,.2f}\n"
            f"Shipping:       ${opp.shipping:,.2f}\n"
            f"Acquisition:    ${opp.acquisition:,.2f}\n"
            f"VAT (margin):   ${opp.vat:,.2f}\n"
            f"Net profit:     ${opp.net_profit:,.2f}  ({opp.margin:.0%} margin)\n\n"
            f"Location:       {l.location or '—'}\n"
            f"Comps:          {opp.valuation.comp_count} "
            f"({opp.valuation.sold_count} sold), "
            f"confidence {opp.valuation.confidence:.0%}\n\n"
            f"Source listing: {l.url}\n"
            f"eBay comps:     {opp.valuation.sample_url or '—'}\n"
        )
        msg = MIMEText(body)
        msg["Subject"] = f"💰 Arbitrage ({opp.margin:.0%}): {l.title[:80]}"
        msg["From"] = self.sender
        msg["To"] = self.recipient

        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls()
            if self.user:
                server.login(self.user, self.password)
            server.send_message(msg)
