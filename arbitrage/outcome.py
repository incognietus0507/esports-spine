"""Outcome CLI: record what an item ACTUALLY sold for.

    python -m arbitrage.outcome https://link.marktplaats.nl/m123 --sold 78.50

Feeds the calibration section of ``python -m arbitrage.report`` so you learn
whether the valuations run hot or cold — the difference between a tool you
trust and one you second-guess.
"""
from __future__ import annotations

import argparse
import sys

from .config import config
from .store import Store


def main() -> None:
    parser = argparse.ArgumentParser(description="Record the real sale price")
    parser.add_argument("url", help="the ORIGINAL listing URL the alert linked to")
    parser.add_argument("--sold", type=float, required=True, help="actual sale price")
    args = parser.parse_args()

    if args.sold < 0:
        sys.exit("--sold must be >= 0")

    store = Store(config.db_path)
    if store.record_outcome(args.url, args.sold):
        print(f"recorded: sold {config.currency_symbol}{args.sold:,.2f}")
    else:
        sys.exit(f"no logged opportunity found for {args.url}")


if __name__ == "__main__":
    main()
