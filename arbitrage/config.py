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

    search_terms: list[str] = field(default_factory=lambda: _list("SEARCH_TERMS"))

    # Path to a local JSON feed file for the Marktplaats adapter (an export or
    # dataset you are AUTHORIZED to use — see COMPLIANCE.md). Empty = disabled.
    marktplaats_feed_file: str = field(
        default_factory=lambda: os.getenv("MARKTPLAATS_FEED_FILE", "")
    )

    # Path to a text watchlist (one saved-search term per line, # comments).
    # Doubles as the checklist of saved searches to create on Marktplaats.
    # Empty/missing file = no filtering.
    watchlist_file: str = field(default_factory=lambda: os.getenv("WATCHLIST_FILE", ""))

    # Minimum valuation confidence (0..1) required before alerting. Mock
    # valuations report confidence 0.0, so any positive value silences them —
    # set e.g. 0.2 in production so only real comp-backed estimates alert.
    min_comp_confidence: float = field(default_factory=lambda: _f("MIN_COMP_CONFIDENCE", 0.0))

    # Currency symbol used in alert formatting (NL default: EUR).
    currency_symbol: str = field(default_factory=lambda: os.getenv("CURRENCY_SYMBOL", "€"))

    profit: ProfitModel = field(default_factory=ProfitModel)
    ebay: EbayConfig = field(default_factory=EbayConfig)
    discogs: DiscogsConfig = field(default_factory=DiscogsConfig)
    # Which valuator to use: "ebay" (default) or "discogs" (vinyl/CDs).
    valuation_source: str = field(default_factory=lambda: os.getenv("VALUATION_SOURCE", "ebay"))

    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "arbitrage.db"))

    def validate(self) -> list[str]:
        """Return a list of fatal configuration problems (empty = valid).
        Called at startup so a mistyped rate fails loudly, not as wrong math."""
        problems: list[str] = []
        if self.valuation_source not in ("ebay", "discogs"):
            problems.append(
                f"VALUATION_SOURCE must be 'ebay' or 'discogs', got {self.valuation_source!r}"
            )
        for name, value in (
            ("EBAY_FEE_RATE", self.profit.ebay_fee_rate),
            ("VAT_MARGIN_RATE", self.profit.vat_margin_rate),
            ("MIN_COMP_CONFIDENCE", self.min_comp_confidence),
        ):
            if not 0.0 <= value <= 1.0:
                problems.append(f"{name} must be between 0 and 1, got {value}")
        for name, value in (
            ("EBAY_FIXED_FEE", self.profit.ebay_fixed_fee),
            ("SHIPPING_COST", self.profit.shipping_cost),
            ("ACQUISITION_COST", self.profit.acquisition_cost),
            ("MIN_PROFIT_MARGIN", self.min_profit_margin),
        ):
            if value < 0:
                problems.append(f"{name} must be >= 0, got {value}")
        if self.poll_interval_minutes < 1:
            problems.append(
                f"POLL_INTERVAL_MINUTES must be >= 1, got {self.poll_interval_minutes}"
            )
        if not 1 <= self.max_listings_per_run <= 1000:
            problems.append(
                f"MAX_LISTINGS_PER_RUN must be 1-1000, got {self.max_listings_per_run}"
            )
        return problems

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
