"""Telegram bot alerter (sendMessage)."""
from __future__ import annotations

import httpx

from ..models import Opportunity
from .base import Alerter


class TelegramAlerter(Alerter):
    name = "telegram"

    def __init__(self, bot_token: str, chat_id: str, symbol: str = "€") -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.symbol = symbol

    def send(self, opp: Opportunity) -> None:
        l = opp.listing
        s = self.symbol
        text = (
            f"💰 <b>Arbitrage opportunity</b>\n"
            f"<b>{_esc(l.title)}</b>\n\n"
            f"Buy: <b>{s}{opp.buy_price:,.2f}</b>  →  "
            f"Resale: <b>{s}{opp.resale_value:,.2f}</b>\n"
            f"Net profit: <b>{s}{opp.net_profit:,.2f}</b>  "
            f"(<b>{opp.margin:.0%}</b> margin)\n"
            f"Location: {_esc(l.location or '—')}\n"
            f"Comps: {opp.valuation.comp_count} ({opp.valuation.sold_count} sold)\n\n"
            f'<a href="{l.url}">Source listing</a>'
        )
        if opp.valuation.sample_url:
            text += f' · <a href="{opp.valuation.sample_url}">eBay comps</a>'

        resp = httpx.post(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15.0,
        )
        resp.raise_for_status()


    def send_text(self, subject: str, body: str) -> None:
        text = f"<b>{_esc(subject)}</b>\n{_esc(body)}"[:4090]  # Telegram limit
        resp = httpx.post(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15.0,
        )
        resp.raise_for_status()


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
