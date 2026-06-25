"""Tests for the profit calculation — the core decision logic.

Run: python -m pytest   (or)   python -m unittest
"""
import unittest

from arbitrage.config import ProfitModel
from arbitrage.models import Listing, Valuation
from arbitrage import profit


def _listing(price: float) -> Listing:
    return Listing(source="test", title="thing", price=price, url="https://x/1")


def _valuation(mv: float) -> Valuation:
    return Valuation(market_value=mv, comp_count=5, sold_count=3, confidence=0.5)


class ProfitTests(unittest.TestCase):
    def setUp(self) -> None:
        # Zero out fees/shipping/gas so the arithmetic is easy to reason about.
        self.model = ProfitModel(
            ebay_fee_rate=0.0, ebay_fixed_fee=0.0,
            shipping_cost=0.0, acquisition_cost=0.0,
        )

    def test_basic_margin(self) -> None:
        opp = profit.evaluate(_listing(50), _valuation(100), self.model)
        self.assertEqual(opp.net_profit, 50.0)
        self.assertAlmostEqual(opp.margin, 1.0)

    def test_fees_reduce_profit(self) -> None:
        model = ProfitModel(
            ebay_fee_rate=0.10, ebay_fixed_fee=0.30,
            shipping_cost=10.0, acquisition_cost=5.0,
        )
        opp = profit.evaluate(_listing(40), _valuation(100), model)
        # 100 - 40 - (100*0.10 + 0.30) - 10 - 5 = 34.70
        self.assertAlmostEqual(opp.net_profit, 34.70, places=2)

    def test_free_item_no_div_by_zero(self) -> None:
        opp = profit.evaluate(_listing(0), _valuation(100), self.model)
        self.assertEqual(opp.margin, 0.0)  # guarded, not infinite

    def test_loss_makes_negative_margin(self) -> None:
        opp = profit.evaluate(_listing(100), _valuation(50), self.model)
        self.assertLess(opp.net_profit, 0)
        self.assertLess(opp.margin, 0)


if __name__ == "__main__":
    unittest.main()
