"""SQLite-backed state: dedupe seen listings + log fired opportunities.

Kept deliberately tiny (stdlib ``sqlite3``) so the tool is zero-ops. Swap for
Postgres via the same two methods if you outgrow a single process.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing

from .models import Listing, Opportunity

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_listings (
    fingerprint TEXT PRIMARY KEY,
    source      TEXT NOT NULL,
    title       TEXT,
    url         TEXT,
    first_seen  TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS opportunities (
    fingerprint TEXT PRIMARY KEY,
    payload     TEXT NOT NULL,
    net_profit  REAL,
    margin      REAL,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


class Store:
    def __init__(self, path: str) -> None:
        self.path = path
        with closing(self._conn()) as c:
            c.executescript(_SCHEMA)
            c.commit()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def is_seen(self, listing: Listing) -> bool:
        """True if this listing was already fully processed in a prior run."""
        with closing(self._conn()) as c:
            row = c.execute(
                "SELECT 1 FROM seen_listings WHERE fingerprint = ?",
                (listing.fingerprint,),
            ).fetchone()
            return row is not None

    def mark_seen(self, listing: Listing) -> None:
        """Record a listing as processed. Call this only AFTER evaluation
        completes — a failed valuation must stay unseen so it retries next run
        instead of being silently lost."""
        with closing(self._conn()) as c:
            c.execute(
                "INSERT OR IGNORE INTO seen_listings (fingerprint, source, title, url) "
                "VALUES (?, ?, ?, ?)",
                (listing.fingerprint, listing.source, listing.title, listing.url),
            )
            c.commit()

    def record_opportunity(self, opp: Opportunity) -> None:
        with closing(self._conn()) as c:
            c.execute(
                "INSERT OR REPLACE INTO opportunities "
                "(fingerprint, payload, net_profit, margin) VALUES (?, ?, ?, ?)",
                (
                    opp.listing.fingerprint,
                    opp.model_dump_json(),
                    opp.net_profit,
                    opp.margin,
                ),
            )
            c.commit()
