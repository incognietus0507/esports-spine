"""Environment-driven configuration.

All tunables live here so the rest of the code never reads ``os.environ``
directly. Loaded once at import time.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _f(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Config error: {name}={raw!r} is not a valid number") from exc


def _i(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Config error: {name}={raw!r} is not a valid integer") from exc


def _list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [p.strip() for p in raw.split(",") if p.strip()]


@dataclass(frozen=True)
class ProfitModel:
    """Baseline cost assumptions used to turn a resale value into net profit."""

    ebay_fee_rate: float = field(default_factory=lambda: _f("EBAY_FEE_RATE", 0.1335))
    ebay_fixed_fee: float = field(default_factory=lambda: _f("EBAY_FIXED_FEE", 0.30))
    shipping_cost: float = field(default_factory=lambda: _f("SHIPPING_COST", 12.00))
    acquisition_cost: float = field(default_factory=lambda: _f("ACQUISITION_COST", 8.00))

    # Margin-scheme VAT (NL "margeregeling"): VAT is owed only on the gross
    # margin (resale - buy), not the full sale price, and is extracted from
    # within the margin: vat = margin * rate / (1 + rate).
    # 0.0 disables it (default / US). NL secondhand margin scheme: 0.21.
    vat_margin_rate: float = field(default_factory=lambda: _f("VAT_MARGIN_RATE", 0.0))


@dataclass(frozen=True)
class EbayConfig:
    client_id: str = field(default_factory=lambda: os.getenv("EBAY_CLIENT_ID", ""))
    client_secret: str = field(default_factory=lambda: os.getenv("EBAY_CLIENT_SECRET", ""))
    marketplace_id: str = field(default_factory=lambda: os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US"))
    env: str = field(default_factory=lambda: os.getenv("EBAY_ENV", "production"))

    @property
    def enabled(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @property
    def base_url(self) -> str:
        return (
            "https://api.sandbox.ebay.com"
            if self.env == "sandbox"
            else "https://api.ebay.com"
        )


@dataclass(frozen=True)
class DiscogsConfig:
    """Discogs has an official API with marketplace price suggestions — the one
    fully-compliant automated resale-value source for vinyl/CDs in the NL plan."""

    token: str = field(default_factory=lambda: os.getenv("DISCOGS_TOKEN", ""))
    # Discogs REQUIRES a descriptive User-Agent or it returns 403.
    user_agent: str = field(
        default_factory=lambda: os.getenv(
            "DISCOGS_USER_AGENT", "RetailArbitrageTool/0.1 (+https://example.com/contact)"
        )
    )
    currency: str = field(default_factory=lambda: os.getenv("DISCOGS_CURRENCY", "EUR"))
    base_url: str = "https://api.discogs.com"

    @property
    def enabled(self) -> bool:
        return bool(self.token)


@dataclass(frozen=True)
class Config:
    poll_interval_minutes: int = field(default_factory=lambda: _i("POLL_INTERVAL_MINUTES", 15))
    min_profit_margin: float = field(default_factory=lambda: _f("MIN_PROFIT_MARGIN", 0.30))
    max_listings_per_run: int = field(default_factory=lambda: _i("MAX_LISTINGS_PER_RUN", 40))

    craigslist_region: str = field(default_factory=lambda: os.getenv("CRAIGSLIST_REGION", "sfbay"))
    craigslist_categories: list[str] = field(default_factory=lambda: _list("CRAIGSLIST_CATEGORIES") or ["ata", "vgc"])
    search_terms: list[str] = field(default_factory=lambda: _list("SEARCH_TERMS"))

    profit: ProfitModel = field(default_factory=ProfitModel)
    ebay: EbayConfig = field(default_factory=EbayConfig)
    discogs: DiscogsConfig = field(default_factory=DiscogsConfig)
    # Which valuator to use: "ebay" (default) or "discogs" (vinyl/CDs).
    valuation_source: str = field(default_factory=lambda: os.getenv("VALUATION_SOURCE", "ebay"))

    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "arbitrage.db"))

    # --- alert channel config (presence == enabled) ---
    discord_webhook_url: str = field(default_factory=lambda: os.getenv("DISCORD_WEBHOOK_URL", ""))
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", ""))
    smtp_port: int = field(default_factory=lambda: _i("SMTP_PORT", 587))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    smtp_from: str = field(default_factory=lambda: os.getenv("SMTP_FROM", ""))
    smtp_to: str = field(default_factory=lambda: os.getenv("SMTP_TO", ""))


config = Config()
