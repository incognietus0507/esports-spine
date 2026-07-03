"""Wires the stages together: collect → dedupe → value → cost → filter → alert."""
from __future__ import annotations

import structlog

from . import profit
from .alerts.base import Alerter
from .config import Config
from .models import Opportunity
from .sources.base import Source
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
            except Exception as exc:  # noqa: BLE001 — one source shouldn't sink the run
                log.warning("source.failed", source=source.name, error=str(exc))
                continue

            for listing in listings:
                budget -= 1
                if self.store.is_seen(listing):
                    continue  # already processed in a prior run

                if not matches(listing.title, watch_terms):
                    # Outside the lane — a deliberate rejection, so mark seen.
                    # (Watchlist edits won't resurrect it; listings expire fast.)
                    self.store.mark_seen(listing)
                    continue

                valuation = self.valuator.value(listing)
                if valuation is None:
                    # Do NOT mark seen: a transient valuation failure must
                    # retry on the next run rather than lose the deal forever.
                    continue

                # Evaluation completed — record it whatever the outcome below.
                self.store.mark_seen(listing)

                if valuation.confidence < self.config.min_comp_confidence:
                    log.debug(
                        "listing.low_confidence",
                        title=listing.title,
                        confidence=valuation.confidence,
                    )
                    continue

                opp = profit.evaluate(listing, valuation, self.config.profit)
                if opp.margin < self.config.min_profit_margin:
                    log.debug("listing.below_threshold", title=listing.title, margin=opp.margin)
                    continue

                log.info(
                    "opportunity.found",
                    title=listing.title,
                    net=opp.net_profit,
                    margin=round(opp.margin, 3),
                )
                self.store.record_opportunity(opp)
                self.alerter.send(opp)
                opportunities.append(opp)

        log.info("run.complete", opportunities=len(opportunities))
        return opportunities
