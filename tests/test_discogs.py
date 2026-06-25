"""Tests for Discogs valuation aggregation (pure logic, no network)."""
import unittest

from arbitrage.config import DiscogsConfig
from arbitrage.models import Listing
from arbitrage.valuation.discogs import DiscogsValuator, _aggregate, _trimmed_median


class TrimmedMedianTests(unittest.TestCase):
    def test_small_list_plain_median(self) -> None:
        self.assertEqual(_trimmed_median([10.0, 20.0, 30.0]), 20.0)

    def test_large_list_drops_extremes(self) -> None:
        # high "Mint sealed" and low "Poor" trimmed before median
        prices = sorted([1.0, 8.0, 9.0, 10.0, 11.0, 200.0])
        self.assertEqual(_trimmed_median(prices), 9.5)


class AggregateTests(unittest.TestCase):
    def test_prefers_price_suggestions(self) -> None:
        v = _aggregate(123, suggestions=[8.0, 10.0, 12.0], lowest=4.0, num_for_sale=10)
        self.assertEqual(v.market_value, 10.0)        # median of suggestions, not lowest
        self.assertIn("release/123", v.sample_url)

    def test_falls_back_to_lowest_price(self) -> None:
        v = _aggregate(99, suggestions=[], lowest=7.5, num_for_sale=3)
        self.assertEqual(v.market_value, 7.5)

    def test_none_when_no_data(self) -> None:
        self.assertIsNone(_aggregate(1, suggestions=[], lowest=None, num_for_sale=0))

    def test_confidence_higher_with_suggestions(self) -> None:
        with_sugg = _aggregate(1, [10.0], lowest=None, num_for_sale=10)
        without = _aggregate(2, [], lowest=10.0, num_for_sale=10)
        self.assertGreater(with_sugg.confidence, without.confidence)


class MockModeTests(unittest.TestCase):
    def test_mock_when_no_token(self) -> None:
        valuator = DiscogsValuator(DiscogsConfig(token=""))
        listing = Listing(source="marktplaats", title="Miles Davis Kind of Blue",
                          price=10.0, url="https://x/1")
        v = valuator.value(listing)
        self.assertIsNotNone(v)
        self.assertEqual(v.confidence, 0.0)           # mock => zero confidence
        self.assertIn("discogs.com", v.sample_url)


if __name__ == "__main__":
    unittest.main()
