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
        symbol: str = "€",
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sender = sender
        self.recipient = recipient
        self.symbol = symbol

    def send(self, opp: Opportunity) -> None:
        l = opp.listing
        s = self.symbol
        body = (
            f"{l.title}\n\n"
            f"Buy price:      {s}{opp.buy_price:,.2f}\n"
            f"Resale (est.):  {s}{opp.resale_value:,.2f}\n"
            f"Platform fees:  {s}{opp.fees:,.2f}\n"
            f"Shipping:       {s}{opp.shipping:,.2f}\n"
            f"Acquisition:    {s}{opp.acquisition:,.2f}\n"
            f"VAT (margin):   {s}{opp.vat:,.2f}\n"
            f"Net profit:     {s}{opp.net_profit:,.2f}  ({opp.margin:.0%} margin)\n\n"
            f"Location:       {l.location or '—'}\n"
            f"Comps:          {opp.valuation.comp_count} "
            f"({opp.valuation.sold_count} sold), "
            f"confidence {opp.valuation.confidence:.0%}\n\n"
            f"Source listing: {l.url}\n"
            f"eBay comps:     {opp.valuation.sample_url or '—'}\n"
        )
        self._deliver(f"💰 Arbitrage ({opp.margin:.0%}): {l.title[:80]}", body)

    def send_text(self, subject: str, body: str) -> None:
        self._deliver(subject, body)

    def _deliver(self, subject: str, body: str) -> None:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = self.recipient

        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls()
            if self.user:
                server.login(self.user, self.password)
            server.send_message(msg)
