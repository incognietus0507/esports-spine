"""CLI entrypoint + scheduler.

    python -m arbitrage.main --once     # single pass, then exit
    python -m arbitrage.main            # run forever on POLL_INTERVAL_MINUTES
"""
from __future__ import annotations

import argparse
import logging
import sys

import structlog
from apscheduler.schedulers.blocking import BlockingScheduler

from .alerts import DiscordAlerter, EmailAlerter, MultiAlerter, TelegramAlerter
from .alerts.base import Alerter
from .config import Config, config
from .pipeline import Pipeline
from .sources import CraigslistSource
from .store import Store
from .valuation import EbayValuator

log = structlog.get_logger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )


def build_alerter(cfg: Config) -> MultiAlerter:
    channels: list[Alerter] = []
    if cfg.discord_webhook_url:
        channels.append(DiscordAlerter(cfg.discord_webhook_url))
    if cfg.telegram_bot_token and cfg.telegram_chat_id:
        channels.append(TelegramAlerter(cfg.telegram_bot_token, cfg.telegram_chat_id))
    if cfg.smtp_host and cfg.smtp_to:
        channels.append(
            EmailAlerter(
                cfg.smtp_host, cfg.smtp_port, cfg.smtp_user,
                cfg.smtp_password, cfg.smtp_from or cfg.smtp_user, cfg.smtp_to,
            )
        )
    if not channels:
        log.warning("alerts.none_configured", note="opportunities will only be logged")
    return MultiAlerter(channels)


def build_pipeline(cfg: Config) -> Pipeline:
    sources = [
        CraigslistSource(
            region=cfg.craigslist_region,
            categories=cfg.craigslist_categories,
            search_terms=cfg.search_terms,
        ),
        # FacebookMarketplaceSource is intentionally NOT wired in — it is a
        # ToS-prohibited stub. See COMPLIANCE.md.
    ]
    valuator = EbayValuator(cfg.ebay)
    if not cfg.ebay.enabled:
        log.warning("ebay.mock_mode", note="no eBay credentials — using MOCK valuations")
    store = Store(cfg.db_path)
    alerter = build_alerter(cfg)
    return Pipeline(cfg, sources, valuator, store, alerter)


def main() -> None:
    parser = argparse.ArgumentParser(description="Retail arbitrage automation")
    parser.add_argument("--once", action="store_true", help="run a single pass and exit")
    args = parser.parse_args()

    _configure_logging()
    pipeline = build_pipeline(config)

    if args.once:
        opps = pipeline.run_once()
        for o in opps:
            print("\n" + o.summary())
        return

    scheduler = BlockingScheduler()
    scheduler.add_job(
        pipeline.run_once,
        "interval",
        minutes=config.poll_interval_minutes,
        next_run_time=None,  # also run immediately on start
    )
    log.info("scheduler.start", interval_minutes=config.poll_interval_minutes)
    pipeline.run_once()  # kick off immediately, then on the interval
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("scheduler.stop")


if __name__ == "__main__":
    main()
