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
    vat = _margin_scheme_vat(buy, resale, model.vat_margin_rate)

    net = resale - buy - fees - shipping - acquisition - vat
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
        vat=round(vat, 2),
        net_profit=round(net, 2),
        margin=margin,
    )


def _margin_scheme_vat(buy: float, resale: float, rate: float) -> float:
    """NL margeregeling: VAT is owed only on a positive gross margin, and is
    extracted from within that margin (the margin is VAT-inclusive):

        vat = margin * rate / (1 + rate)

    Returns 0 when the rate is disabled (0.0) or there is no positive margin.
    """
    if rate <= 0:
        return 0.0
    gross_margin = resale - buy
    if gross_margin <= 0:
        return 0.0
    return gross_margin * rate / (1 + rate)
