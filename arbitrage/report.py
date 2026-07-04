"""Digest report: what the tool found, how it's performing, how honest the
estimates are.

    python -m arbitrage.report              # last 7 days, printed
    python -m arbitrage.report --days 30
    python -m arbitrage.report --send       # also push through alert channels

Cron it daily (``0 8 * * *``) with ``--send`` for a morning digest.
"""
from __future__ import annotations

import argparse

from .config import config
from .store import Store


def build_digest(store: Store, days: int, symbol: str = "€") -> str:
    stats = store.run_stats(days)
    tops = store.recent_opportunities(days)
    calib = store.calibration()

    hit_rate = (
        f"{100 * stats['opportunities'] / stats['valued']:.1f}%"
        if stats["valued"]
        else "n/a"
    )
    lines = [
        f"Arbitrage digest — last {days} day(s)",
        f"Runs: {stats['runs']} | listings: {stats['fetched']} | "
        f"valued: {stats['valued']} | opportunities: {stats['opportunities']} "
        f"(hit rate {hit_rate}) | errors: {stats['errors']}",
    ]

    if tops:
        lines.append("")
        lines.append("Top opportunities:")
        for t in tops:
            outcome = (
                f" | SOLD {symbol}{t['actual_price']:,.2f}"
                if t["actual_price"] is not None
                else ""
            )
            lines.append(
                f"  • {t['title'][:60]} — net {symbol}{t['net_profit']:,.2f} "
                f"({t['margin']:.0%}){outcome}\n    {t['url']}"
            )
    else:
        lines.append("")
        lines.append("No opportunities in this window.")

    lines.append("")
    if calib:
        lines.append(
            f"Calibration: {calib['count']} sold — actual vs estimate "
            f"{calib['avg_error_pct']:+.1f}% "
            "(negative = estimates run high; adjust fees/threshold)"
        )
    else:
        lines.append(
            "Calibration: no outcomes yet — after each sale run "
            "`python -m arbitrage.outcome <listing-url> --sold <price>`"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Print/send the arbitrage digest")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument(
        "--send", action="store_true", help="also deliver via configured alert channels"
    )
    args = parser.parse_args()

    store = Store(config.db_path)
    digest = build_digest(store, args.days, config.currency_symbol)
    print(digest)

    if args.send:
        from .main import build_alerter

        build_alerter(config).send_text(
            f"Arbitrage digest ({args.days}d)", digest
        )


if __name__ == "__main__":
    main()
