"""SQLite-backed state: dedupe, opportunity log, run history, sale outcomes.

Kept deliberately tiny (stdlib ``sqlite3``) so the tool is zero-ops. Swap for
Postgres behind the same methods if you outgrow a single process.
"""
from __future__ import annotations

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
    fingerprint  TEXT PRIMARY KEY,
    payload      TEXT NOT NULL,
    net_profit   REAL,
    margin       REAL,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at    TEXT NOT NULL,
    fetched       INTEGER NOT NULL,
    valued        INTEGER NOT NULL,
    opportunities INTEGER NOT NULL,
    errors        INTEGER NOT NULL
);
"""

# Additive migrations for existing databases: (table, column, type).
_MIGRATIONS = [
    ("opportunities", "url", "TEXT"),
    ("opportunities", "title", "TEXT"),
    ("opportunities", "actual_price", "REAL"),
    ("opportunities", "sold_at", "TEXT"),
]


class Store:
    def __init__(self, path: str) -> None:
        self.path = path
        with closing(self._conn()) as c:
            c.executescript(_SCHEMA)
            self._migrate(c)
            c.commit()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    @staticmethod
    def _migrate(c: sqlite3.Connection) -> None:
        """Add columns introduced after a database was first created."""
        for table, column, sqltype in _MIGRATIONS:
            existing = {row[1] for row in c.execute(f"PRAGMA table_info({table})")}
            if column not in existing:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sqltype}")

    # -- dedupe ---------------------------------------------------------------

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

    # -- opportunities & outcomes ----------------------------------------------

    def record_opportunity(self, opp: Opportunity) -> None:
        with closing(self._conn()) as c:
            c.execute(
                "INSERT OR REPLACE INTO opportunities "
                "(fingerprint, payload, net_profit, margin, url, title) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    opp.listing.fingerprint,
                    opp.model_dump_json(),
                    opp.net_profit,
                    opp.margin,
                    opp.listing.url,
                    opp.listing.title,
                ),
            )
            c.commit()

    def record_outcome(self, url: str, actual_price: float) -> bool:
        """Attach the real sale price to a logged opportunity (by listing URL).
        Returns False when no opportunity matches that URL."""
        with closing(self._conn()) as c:
            cur = c.execute(
                "UPDATE opportunities SET actual_price = ?, "
                "sold_at = CURRENT_TIMESTAMP WHERE url = ?",
                (actual_price, url),
            )
            c.commit()
            return cur.rowcount > 0

    # -- run history & digest queries -------------------------------------------

    def record_run(
        self, started_at: str, fetched: int, valued: int, opportunities: int, errors: int
    ) -> None:
        with closing(self._conn()) as c:
            c.execute(
                "INSERT INTO runs (started_at, fetched, valued, opportunities, errors) "
                "VALUES (?, ?, ?, ?, ?)",
                (started_at, fetched, valued, opportunities, errors),
            )
            c.commit()

    def run_stats(self, days: int) -> dict:
        """Aggregated run counters over the last N days."""
        with closing(self._conn()) as c:
            row = c.execute(
                "SELECT COUNT(*), COALESCE(SUM(fetched),0), COALESCE(SUM(valued),0), "
                "COALESCE(SUM(opportunities),0), COALESCE(SUM(errors),0) "
                "FROM runs WHERE started_at >= datetime('now', ?)",
                (f"-{int(days)} days",),
            ).fetchone()
        return {
            "runs": row[0], "fetched": row[1], "valued": row[2],
            "opportunities": row[3], "errors": row[4],
        }

    def recent_opportunities(self, days: int, limit: int = 10) -> list[dict]:
        """Top recent opportunities by net profit, including any outcome."""
        with closing(self._conn()) as c:
            rows = c.execute(
                "SELECT title, url, net_profit, margin, actual_price "
                "FROM opportunities WHERE created_at >= datetime('now', ?) "
                "ORDER BY net_profit DESC LIMIT ?",
                (f"-{int(days)} days", limit),
            ).fetchall()
        return [
            {"title": r[0], "url": r[1], "net_profit": r[2],
             "margin": r[3], "actual_price": r[4]}
            for r in rows
        ]

    def calibration(self) -> dict | None:
        """Estimate-vs-outcome stats over all opportunities with a recorded
        sale. Returns None until at least one outcome exists."""
        with closing(self._conn()) as c:
            rows = c.execute(
                "SELECT payload, actual_price FROM opportunities "
                "WHERE actual_price IS NOT NULL"
            ).fetchall()
        if not rows:
            return None
        import json as _json

        errors = []
        for payload, actual in rows:
            estimated = _json.loads(payload)["resale_value"]
            if estimated > 0:
                errors.append((actual - estimated) / estimated)
        if not errors:
            return None
        return {
            "count": len(errors),
            "avg_error_pct": round(100 * sum(errors) / len(errors), 1),
        }
