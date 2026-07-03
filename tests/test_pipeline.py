"""Pipeline + store semantics: retry-on-failure dedupe, confidence gating."""
import os
import tempfile
import unittest

from arbitrage.config import Config
from arbitrage.models import Listing, Valuation
from arbitrage.pipeline import Pipeline
from arbitrage.store import Store


def _listing(n: int, price: float = 40.0) -> Listing:
    return Listing(source="test", title=f"item {n}", price=price, url=f"https://x/{n}")


class FakeSource:
    name = "test"

    def __init__(self, listings):
        self.listings = listings

    def fetch(self, limit):
        return self.listings[:limit]


class FakeValuator:
    """Returns None (failure) until `fail_times` runs out, then a valuation."""

    def __init__(self, market_value=200.0, confidence=0.5, fail_times=0):
        self.market_value = market_value
        self.confidence = confidence
        self.fail_times = fail_times
        self.calls = 0

    def value(self, listing):
        self.calls += 1
        if self.fail_times > 0:
            self.fail_times -= 1
            return None
        return Valuation(
            market_value=self.market_value,
            comp_count=5,
            sold_count=0,
            confidence=self.confidence,
        )


class CollectingAlerter:
    name = "collect"

    def __init__(self):
        self.sent = []

    def send(self, opp):
        self.sent.append(opp)


def _pipeline(store, valuator, listings, **cfg_overrides):
    cfg = Config(**cfg_overrides)
    alerter = CollectingAlerter()
    p = Pipeline(cfg, [FakeSource(listings)], valuator, store, alerter)
    return p, alerter


class PipelineTests(unittest.TestCase):
    def setUp(self):
        fd, self.db = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = Store(self.db)

    def tearDown(self):
        os.unlink(self.db)

    def test_failed_valuation_retries_next_run(self):
        # First run: valuator fails -> listing must NOT be marked seen.
        valuator = FakeValuator(fail_times=1)
        p, alerter = _pipeline(self.store, valuator, [_listing(1)])
        self.assertEqual(p.run_once(), [])
        # Second run: valuation succeeds -> the deal is recovered, not lost.
        opps = p.run_once()
        self.assertEqual(len(opps), 1)
        self.assertEqual(len(alerter.sent), 1)

    def test_processed_listing_not_reprocessed(self):
        valuator = FakeValuator()
        p, alerter = _pipeline(self.store, valuator, [_listing(1)])
        p.run_once()
        p.run_once()
        self.assertEqual(valuator.calls, 1)      # second run skipped it
        self.assertEqual(len(alerter.sent), 1)   # and no duplicate alert

    def test_below_threshold_marked_seen_no_alert(self):
        # resale 50 on buy 40 -> negative margin, but still a completed eval.
        valuator = FakeValuator(market_value=50.0)
        p, alerter = _pipeline(self.store, valuator, [_listing(1)])
        p.run_once()
        p.run_once()
        self.assertEqual(valuator.calls, 1)
        self.assertEqual(alerter.sent, [])

    def test_watchlist_filters_out_of_lane_listings(self):
        import tempfile as tf

        with tf.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("Miles Davis\n")
            watch = f.name
        self.addCleanup(os.unlink, watch)
        valuator = FakeValuator()
        listings = [
            Listing(source="test", title="ABBA Gold LP", price=40.0, url="https://x/a"),
            Listing(source="test", title="Miles Davis Kind of Blue LP",
                    price=40.0, url="https://x/b"),
        ]
        p, alerter = _pipeline(self.store, valuator, listings, watchlist_file=watch)
        opps = p.run_once()
        self.assertEqual(len(opps), 1)
        self.assertEqual(valuator.calls, 1)  # off-lane item never valued
        self.assertIn("Miles Davis", opps[0].listing.title)

    def test_low_confidence_filtered_when_gate_set(self):
        valuator = FakeValuator(confidence=0.0)  # e.g. mock valuation
        p, alerter = _pipeline(
            self.store, valuator, [_listing(1)], min_comp_confidence=0.2
        )
        self.assertEqual(p.run_once(), [])
        self.assertEqual(alerter.sent, [])


if __name__ == "__main__":
    unittest.main()
