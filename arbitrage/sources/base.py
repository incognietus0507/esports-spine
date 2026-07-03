"""Source adapter contract.

A Source knows how to pull *public* listings from one marketplace and yield
them as normalized ``Listing`` objects. Keep all platform-specific quirks
(URLs, parsing, throttling) inside the adapter.
"""
from __future__ import annotations

import abc

from ..models import Listing


class SourceConfigurationError(RuntimeError):
    """Permanent misconfiguration (not a transient failure): the pipeline
    fails fast on this instead of warn-and-skipping it forever."""


class Source(abc.ABC):
    name: str

    @abc.abstractmethod
    def fetch(self, limit: int) -> list[Listing]:
        """Return up to ``limit`` current public listings. Must be polite:
        respect rate limits, cache where possible, and never exceed ``limit``.
        """
        raise NotImplementedError
