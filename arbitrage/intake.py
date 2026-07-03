"""Intake CLI: log a listing from a Marktplaats notification into the feed.

The compliant manual workflow is: Marktplaats saved-search notification →
you glance at it → one command here → the pipeline values it and alerts if it
clears the profit gate. Keeps the human data-entry step to ~5 seconds.

Usage::

    python -m arbitrage.intake "Miles Davis Kind of Blue LP" "€ 25" \
        https://link.marktplaats.nl/m2153... --location Utrecht

    python -m arbitrage.intake ... --run   # also run the pipeline once

Appends to the JSON feed file (``MARKTPLAATS_FEED_FILE``), creating it if
needed. Duplicate URLs are skipped.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import config


def append_listing(
    feed_file: str,
    title: str,
    price: str,
    url: str,
    location: str | None = None,
) -> bool:
    """Append one listing dict to the feed file. Returns False on duplicate URL."""
    path = Path(feed_file)
    listings: list[dict] = []
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        listings = raw.get("listings", []) if isinstance(raw, dict) else raw
        if not isinstance(listings, list):
            raise ValueError(f"{feed_file} does not contain a listing array")

    if any(item.get("url") == url for item in listings if isinstance(item, dict)):
        return False

    entry: dict = {"title": title, "price": price, "url": url}
    if location:
        entry["location"] = location
    listings.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(listings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Log a Marktplaats listing into the local feed file"
    )
    parser.add_argument("title", help="listing title")
    parser.add_argument("price", help="asking price, e.g. '€ 25' or '25,00'")
    parser.add_argument("url", help="listing URL")
    parser.add_argument("--location", default=None, help="city/neighbourhood")
    parser.add_argument(
        "--feed-file",
        default=config.marktplaats_feed_file,
        help="feed file (default: MARKTPLAATS_FEED_FILE)",
    )
    parser.add_argument(
        "--run", action="store_true", help="run one pipeline pass after adding"
    )
    args = parser.parse_args()

    if not args.feed_file:
        sys.exit("No feed file: set MARKTPLAATS_FEED_FILE or pass --feed-file")
    if not (args.url.startswith("http://") or args.url.startswith("https://")):
        sys.exit(f"URL must be http(s): {args.url}")

    added = append_listing(
        args.feed_file, args.title, args.price, args.url, args.location
    )
    print("added" if added else "skipped (duplicate url)")

    if added and args.run:
        from .main import build_pipeline

        pipeline = build_pipeline(config)
        try:
            for opp in pipeline.run_once():
                print("\n" + opp.summary())
        finally:
            pipeline.valuator.close()


if __name__ == "__main__":
    main()
