"""Phase 4: run history, outcomes, calibration, digest."""
import os
import tempfile
import unittest

from arbitrage.models import Listing, Valuation, Opportunity
from arbitrage.report import build_digest
from arbitrage.store import Store


def _opportunity(url: str, resale: float = 100.0, net: float = 40.0) -> Opportunity:
    listing = Listing(source="test", title=f"item {url[-1]}", price=30.0, url=url)
    valuation = Valuation(market_value=resale, comp_count=5, sold_count=2, confidence=0.5)
    return Opportunity(
        listing=listing, valuation=valuation, buy_price=30.0, resale_value=resale,
        fees=10.0, shipping=10.0, acquisition=10.0, net_profit=net, margin=net / 30.0,
    )


class StoreObservabilityTests(unittest.TestCase):
    def setUp(self):
        fd, self.db = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = Store(self.db)
        self.addCleanup(os.unlink, self.db)

    def test_run_stats_aggregate(self):
        self.store.record_run("2026-07-03T10:00:00", 10, 8, 2, 1)
        self.store.record_run("2026-07-03T11:00:00", 5, 5, 1, 0)
        stats = self.store.run_stats(days=7)
        self.assertEqual(stats["runs"], 2)
        self.assertEqual(stats["fetched"], 15)
        self.assertEqual(stats["valued"], 13)
        self.assertEqual(stats["opportunities"], 3)
        self.assertEqual(stats["errors"], 1)

    def test_outcome_roundtrip_and_calibration(self):
        self.store.record_opportunity(_opportunity("https://x/1", resale=100.0))
        self.assertTrue(self.store.record_outcome("https://x/1", 90.0))
        self.assertFalse(self.store.record_outcome("https://x/nope", 50.0))
        calib = self.store.calibration()
        self.assertEqual(calib["count"], 1)
        self.assertAlmostEqual(calib["avg_error_pct"], -10.0)  # sold 10% under estimate

    def test_calibration_none_without_outcomes(self):
        self.store.record_opportunity(_opportunity("https://x/1"))
        self.assertIsNone(self.store.calibration())

    def test_migration_adds_columns_to_old_db(self):
        # Simulate a pre-Phase-4 database: opportunities without new columns.
        import sqlite3
        old = self.db + ".old"
        conn = sqlite3.connect(old)
        conn.execute(
            "CREATE TABLE opportunities (fingerprint TEXT PRIMARY KEY, "
            "payload TEXT NOT NULL, net_profit REAL, margin REAL, "
            "created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.commit()
        conn.close()
        self.addCleanup(os.unlink, old)
        store = Store(old)  # must not raise; must add url/actual_price/...
        store.record_opportunity(_opportunity("https://x/2"))
        self.assertTrue(store.record_outcome("https://x/2", 55.0))


class DigestTests(unittest.TestCase):
    def setUp(self):
        fd, self.db = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = Store(self.db)
        self.addCleanup(os.unlink, self.db)

    def test_digest_contains_stats_tops_and_calibration(self):
        self.store.record_run("2026-07-03T10:00:00", 10, 8, 1, 0)
        self.store.record_opportunity(_opportunity("https://x/1", resale=100.0, net=42.0))
        self.store.record_outcome("https://x/1", 95.0)
        digest = build_digest(self.store, days=7)
        self.assertIn("Runs: 1", digest)
        self.assertIn("42.00", digest)          # top opportunity net
        self.assertIn("SOLD", digest)
        self.assertIn("Calibration: 1 sold", digest)

    def test_digest_empty_store(self):
        digest = build_digest(self.store, days=7)
        self.assertIn("No opportunities", digest)
        self.assertIn("no outcomes yet", digest)


class SendTextFanoutTests(unittest.TestCase):
    def test_multi_alerter_fans_out_and_isolates_failures(self):
        from arbitrage.alerts.base import Alerter, MultiAlerter

        got: list[tuple[str, str]] = []

        class Ok(Alerter):
            name = "ok"
            def send(self, opp): ...
            def send_text(self, subject, body): got.append((subject, body))

        class Boom(Alerter):
            name = "boom"
            def send(self, opp): ...
            def send_text(self, subject, body): raise RuntimeError("down")

        MultiAlerter([Boom(), Ok()]).send_text("subj", "body")  # must not raise
        self.assertEqual(got, [("subj", "body")])


if __name__ == "__main__":
    unittest.main()
