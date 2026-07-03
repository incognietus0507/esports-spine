"""Watchlist: the keyword terms you monitor via Marktplaats saved searches.

One term per line, ``#`` starts a comment. The same list serves two purposes:

1. It's your checklist for creating saved searches (*bewaarde zoekopdrachten*)
   on Marktplaats itself — Marktplaats then notifies you, compliantly.
2. The pipeline filters incoming feed listings against it, so only items in
   your lane get valued and alerted.

An empty/missing watchlist disables filtering (everything passes).
"""
from __future__ import annotations

from pathlib import Path

import structlog

from .textutil import fold_text

log = structlog.get_logger(__name__)


def load_watchlist(path: str) -> list[str]:
    """Load terms from a text file; missing file -> empty list (no filter)."""
    if not path:
        return []
    file = Path(path)
    if not file.exists():
        log.warning("watchlist.missing", path=path)
        return []
    terms: list[str] = []
    for line in file.read_text(encoding="utf-8").splitlines():
        term = line.split("#", 1)[0].strip()
        if term:
            terms.append(term)
    return terms


def matches(title: str, terms: list[str]) -> bool:
    """True when the title contains any watchlist term (case- and
    accent-insensitive). An empty watchlist matches everything."""
    if not terms:
        return True
    folded = fold_text(title)
    return any(fold_text(term) in folded for term in terms)
