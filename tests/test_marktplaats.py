"""Tests for the Marktplaats adapter: price coercion, normalization, ToS gate."""
import sys
import types
import unittest

# Stub the unbuildable optional dep so importing the sources package works.
sys.modules.setdefault("feedparser", types.ModuleType("feedparser"))

from arbitrage.sources.marktplaats import (  # noqa: E402
    MarktplaatsDisabled,
    MarktplaatsSource,
    _coerce_price,
    _normalize,
)


class CoercePriceTests(unittest.TestCase):
    def test_nl_thousands_and_decimal(self) -> None:
        self.assertEqual(_coerce_price("€ 1.250,00"), 1250.00)

    def test_nl_decimal_only(self) -> None:
        self.assertEqual(_coerce_price("40,00"), 40.00)

    def test_plain_decimal_not_destroyed(self) -> None:
        # Regression: "1.0" must stay 1.0, not become 10.0.
        self.assertEqual(_coerce_price("1.0"), 1.0)

    def test_price_cents_dict(self) -> None:
        self.assertEqual(_coerce_price({"priceCents": 3500}), 35.00)

    def test_zero_cents_is_free_not_dropped(self) -> None:
        self.assertEqual(_coerce_price({"priceCents": 0}), 0.0)

    def test_bool_rejected(self) -> None:
        self.assertIsNone(_coerce_price(True))

    def test_oversized_string_rejected(self) -> None:
        self.assertIsNone(_coerce_price("9" * 100))

    def test_deeply_nested_dict_bounded(self) -> None:
        evil: dict = {}
        cur = evil
        for _ in range(50):
            cur["amount"] = {}
            cur = cur["amount"]
        self.assertIsNone(_coerce_price(evil))  # no RecursionError


class NormalizeTests(unittest.TestCase):
    def test_drops_record_without_price(self) -> None:
        self.assertIsNone(_normalize({"title": "x", "url": "https://x/1"}))

    def test_rejects_non_web_url(self) -> None:
        bad = {"title": "x", "price": 5, "url": "javascript:alert(1)"}
        self.assertIsNone(_normalize(bad))  # model validator rejects scheme

    def test_normalizes_nl_record(self) -> None:
        out = _normalize({"title": "Pastoe kast", "price": "€ 1.250,00",
                          "url": "https://x/1", "city": "Utrecht"})
        self.assertIsNotNone(out)
        self.assertEqual(out.price, 1250.00)
        self.assertEqual(out.location, "Utrecht")


class GateTests(unittest.TestCase):
    def test_disabled_without_feed(self) -> None:
        with self.assertRaises(MarktplaatsDisabled):
            MarktplaatsSource().fetch(10)


if __name__ == "__main__":
    unittest.main()
