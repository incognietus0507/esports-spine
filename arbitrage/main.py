"""CLI entrypoint + scheduler.

    python -m arbitrage.main --once     # single pass, then exit
    python -m arbitrage.main            # run forever on POLL_INTERVAL_MINUTES
"""
from __future__ import annotations

import argparse
import logging
import sys

import structlog
from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.blocking import BlockingScheduler

from .alerts import DiscordAlerter, EmailAlerter, MultiAlerter, TelegramAlerter
from .alerts.base import Alerter
from .config import Config, config
from .pipeline import Pipeline
from .sources import MarktplaatsSource, json_file_loader
from .sources.base import Source
from .store import Store
from .valuation import DiscogsValuator, EbayValuator

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
    sym = cfg.currency_symbol
    if cfg.discord_webhook_url:
        channels.append(DiscordAlerter(cfg.discord_webhook_url, symbol=sym))
    if cfg.telegram_bot_token and cfg.telegram_chat_id:
        channels.append(
            TelegramAlerter(cfg.telegram_bot_token, cfg.telegram_chat_id, symbol=sym)
        )
    if cfg.smtp_host and cfg.smtp_to:
        channels.append(
            EmailAlerter(
                cfg.smtp_host, cfg.smtp_port, cfg.smtp_user,
                cfg.smtp_password, cfg.smtp_from or cfg.smtp_user, cfg.smtp_to,
                symbol=sym,
            )
        )
    if not channels:
        log.warning("alerts.none_configured", note="opportunities will only be logged")
    return MultiAlerter(channels)


def build_pipeline(cfg: Config) -> Pipeline:
    problems = cfg.validate()
    if problems:
        for p in problems:
            log.error("config.invalid", problem=p)
        raise SystemExit("Invalid configuration:\n  - " + "\n  - ".join(problems))

    sources: list[Source] = []
    if cfg.marktplaats_feed_file:
        sources.append(
            MarktplaatsSource(feed_loader=json_file_loader(cfg.marktplaats_feed_file))
        )
    else:
        log.warning(
            "sources.none_configured",
            note="set MARKTPLAATS_FEED_FILE to an authorized feed export; "
            "see COMPLIANCE.md / STRATEGY-NL.md",
        )
    # FacebookMarketplaceSource is intentionally NOT wired in — it is a
    # ToS-prohibited stub. See COMPLIANCE.md.
    if cfg.valuation_source == "discogs":
        valuator = DiscogsValuator(cfg.discogs)
        if not cfg.discogs.enabled:
            log.warning("discogs.mock_mode", note="no DISCOGS_TOKEN — using MOCK valuations")
    else:
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

    try:
        if args.once:
            opps = pipeline.run_once()
            for o in opps:
                print("\n" + o.summary())
            return

        scheduler = BlockingScheduler()
        # APScheduler swallows job exceptions into its own logger; without
        # this listener a deterministic crash repeats invisibly forever.
        scheduler.add_listener(
            lambda event: log.error(
                "scheduled_run.failed",
                error=str(event.exception),
                exc_info=event.exception,
            ),
            EVENT_JOB_ERROR,
        )
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
    finally:
        pipeline.valuator.close()


if __name__ == "__main__":
    main()
