"""Phase 3: startup config validation + shared HTTP retry/backoff policy."""
import unittest

import httpx

from arbitrage.config import Config, ProfitModel
from arbitrage.httputil import get_with_backoff


class ConfigValidateTests(unittest.TestCase):
    def test_default_config_is_valid(self) -> None:
        self.assertEqual(Config().validate(), [])

    def test_bad_valuation_source(self) -> None:
        problems = Config(valuation_source="scrape-everything").validate()
        self.assertTrue(any("VALUATION_SOURCE" in p for p in problems))

    def test_fee_rate_out_of_range(self) -> None:
        cfg = Config(profit=ProfitModel(ebay_fee_rate=1.5))
        self.assertTrue(any("EBAY_FEE_RATE" in p for p in cfg.validate()))

    def test_vat_out_of_range(self) -> None:
        cfg = Config(profit=ProfitModel(vat_margin_rate=21.0))  # meant 0.21
        self.assertTrue(any("VAT_MARGIN_RATE" in p for p in cfg.validate()))

    def test_negative_costs_rejected(self) -> None:
        cfg = Config(profit=ProfitModel(shipping_cost=-5.0))
        self.assertTrue(any("SHIPPING_COST" in p for p in cfg.validate()))

    def test_poll_interval_and_budget_bounds(self) -> None:
        self.assertTrue(any("POLL_INTERVAL" in p
                            for p in Config(poll_interval_minutes=0).validate()))
        self.assertTrue(any("MAX_LISTINGS" in p
                            for p in Config(max_listings_per_run=0).validate()))

    def test_multiple_problems_all_reported(self) -> None:
        cfg = Config(
            valuation_source="nope",
            profit=ProfitModel(ebay_fee_rate=2.0, shipping_cost=-1.0),
        )
        self.assertGreaterEqual(len(cfg.validate()), 3)


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


class BackoffTests(unittest.TestCase):
    def test_retries_429_then_succeeds(self) -> None:
        calls = {"n": 0}
        slept: list[float] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(429) if calls["n"] < 3 else httpx.Response(
                200, json={"ok": True}
            )

        resp = get_with_backoff(_client(handler), "https://x/api", sleep=slept.append)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(calls["n"], 3)
        self.assertEqual(slept, [2.0, 4.0])  # exponential

    def test_retries_transient_5xx(self) -> None:
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(503) if calls["n"] == 1 else httpx.Response(200)

        resp = get_with_backoff(_client(handler), "https://x", sleep=lambda s: None)
        self.assertEqual(resp.status_code, 200)

    def test_gives_up_after_attempts_with_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429)

        with self.assertRaises(httpx.HTTPStatusError):
            get_with_backoff(_client(handler), "https://x", sleep=lambda s: None)

    def test_non_retryable_status_raises_immediately(self) -> None:
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(404)

        with self.assertRaises(httpx.HTTPStatusError):
            get_with_backoff(_client(handler), "https://x", sleep=lambda s: None)
        self.assertEqual(calls["n"], 1)  # no retry on 404


if __name__ == "__main__":
    unittest.main()
