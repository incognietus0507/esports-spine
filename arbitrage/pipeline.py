"""Wires the stages together: collect → dedupe → value → cost → filter → alert."""
from __future__ import annotations

import structlog

from . import profit
from .alerts.base import Alerter
from .config import Config
from .models import Opportunity
from .sources.base import Source, SourceConfigurationError
from .store import Store
from .valuation.ebay import EbayValuator
from .watchlist import load_watchlist, matches

log = structlog.get_logger(__name__)


class Pipeline:
    def __init__(
        self,
        config: Config,
        sources: list[Source],
        valuator: EbayValuator,
        store: Store,
        alerter: Alerter,
    ) -> None:
        self.config = config
        self.sources = sources
        self.valuator = valuator
        self.store = store
        self.alerter = alerter

    def run_once(self) -> list[Opportunity]:
        opportunities: list[Opportunity] = []
        budget = self.config.max_listings_per_run
        # Reloaded each run so watchlist edits apply without a restart.
        watch_terms = load_watchlist(self.config.watchlist_file)

        for source in self.sources:
            if budget <= 0:
                break
            try:
                listings = source.fetch(limit=budget)
            except SourceConfigurationError:
                raise  # permanent misconfiguration — fail fast, don't warn-and-skip
            except Exception as exc:  # noqa: BLE001 — one source shouldn't sink the run
                log.warning(
                    "source.failed", source=source.name, error=str(exc), exc_info=True
                )
                continue

            for listing in listings:
                budget -= 1
                try:
                    opp = self._process_listing(listing, watch_terms)
                except Exception as exc:  # noqa: BLE001 — one listing shouldn't sink the run
                    # Not marked seen -> retried next run (e.g. transient
                    # "database is locked" must not discard a found deal).
                    log.error(
                        "listing.processing_failed",
                        title=listing.title,
                        error=str(exc),
                        exc_info=True,
                    )
                    continue
                if opp is not None:
                    opportunities.append(opp)

        log.info("run.complete", opportunities=len(opportunities))
        return opportunities

    def _process_listing(
        self, listing, watch_terms: list[str]
    ) -> Opportunity | None:
        """Handle one listing end to end. mark_seen ordering is deliberate:
        deliberate rejections are marked immediately; a found opportunity is
        marked only AFTER it has been recorded and alerted, so a store/alert
        crash leaves it unseen and it retries next run instead of vanishing."""
        if self.store.is_seen(listing):
            return None  # already processed in a prior run

        if not matches(listing.title, watch_terms):
            # Outside the lane — a deliberate rejection, so mark seen.
            # (Watchlist edits won't resurrect it; listings expire fast.)
            self.store.mark_seen(listing)
            return None

        valuation = self.valuator.value(listing)
        if valuation is None:
            # Do NOT mark seen: a transient valuation failure must retry on
            # the next run rather than lose the deal forever.
            return None

        if valuation.confidence < self.config.min_comp_confidence:
            log.debug(
                "listing.low_confidence",
                title=listing.title,
                confidence=valuation.confidence,
            )
            self.store.mark_seen(listing)
            return None

        opp = profit.evaluate(listing, valuation, self.config.profit)
        if opp.margin < self.config.min_profit_margin:
            log.debug("listing.below_threshold", title=listing.title, margin=opp.margin)
            self.store.mark_seen(listing)
            return None

        log.info(
            "opportunity.found",
            title=listing.title,
            net=opp.net_profit,
            margin=round(opp.margin, 3),
        )
        self.store.record_opportunity(opp)
        self.alerter.send(opp)  # MultiAlerter isolates per-channel failures
        self.store.mark_seen(listing)
        return opp
