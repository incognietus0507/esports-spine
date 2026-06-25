"""Profit calculation: resale value + cost assumptions → net profit & margin."""
from __future__ import annotations

from .config import ProfitModel
from .models import Listing, Opportunity, Valuation


def evaluate(
    listing: Listing,
    valuation: Valuation,
    model: ProfitModel,
) -> Opportunity:
    """Turn a listing + its eBay valuation into a fully costed Opportunity.

    net_profit = resale - buy - ebay_fees - shipping - acquisition
    margin     = net_profit / buy_price
    """
    buy = listing.price
    resale = valuation.market_value

    fees = resale * model.ebay_fee_rate + model.ebay_fixed_fee
    shipping = model.shipping_cost
    acquisition = model.acquisition_cost

    net = resale - buy - fees - shipping - acquisition
    # Guard against a $0 buy price (free listings) producing infinite margin.
    margin = net / buy if buy > 0 else 0.0

    return Opportunity(
        listing=listing,
        valuation=valuation,
        buy_price=buy,
        resale_value=resale,
        fees=round(fees, 2),
        shipping=shipping,
        acquisition=acquisition,
        net_profit=round(net, 2),
        margin=margin,
    )
