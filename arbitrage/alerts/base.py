"""Alerter contract + fan-out wrapper."""
from __future__ import annotations

import abc

import structlog

from ..models import Opportunity

log = structlog.get_logger(__name__)


class Alerter(abc.ABC):
    name: str

    @abc.abstractmethod
    def send(self, opp: Opportunity) -> None: ...


class MultiAlerter(Alerter):
    """Sends each opportunity to every configured channel; one failing channel
    never blocks the others."""

    name = "multi"

    def __init__(self, channels: list[Alerter]) -> None:
        self.channels = channels

    def send(self, opp: Opportunity) -> None:
        failures = 0
        for ch in self.channels:
            try:
                ch.send(opp)
            except Exception as exc:  # noqa: BLE001 — isolate channel failures
                failures += 1
                log.warning(
                    "alert.channel_failed",
                    channel=ch.name,
                    error=str(exc),
                    exc_info=True,
                )
        if self.channels and failures == len(self.channels):
            # Total delivery outage: one loud, greppable event (the deal is
            # still recorded in the store, but the operator never saw it).
            log.error(
                "alert.all_channels_failed",
                title=opp.listing.title,
                net_profit=opp.net_profit,
                url=opp.listing.url,
            )

    def __bool__(self) -> bool:
        return bool(self.channels)
