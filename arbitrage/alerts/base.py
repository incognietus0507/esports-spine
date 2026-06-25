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
        for ch in self.channels:
            try:
                ch.send(opp)
            except Exception as exc:  # noqa: BLE001 — isolate channel failures
                log.warning("alert.channel_failed", channel=ch.name, error=str(exc))

    def __bool__(self) -> bool:
        return bool(self.channels)
