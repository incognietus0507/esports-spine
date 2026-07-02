"""Feed loaders for the Marktplaats adapter.

A feed loader is any callable returning ``list[dict]`` from a source you are
AUTHORIZED to use (official partner API, business CSV/JSON export, licensed
feed). This module ships the simplest compliant option: a local JSON file you
maintain yourself — e.g. an export you are permitted to download, or listings
you copy over manually from your own saved searches.

File format (either shape works)::

    [ {"title": "...", "price": "€ 1.250,00", "url": "https://...", "city": "..."} ]
    { "listings": [ ... ] }
"""
from __future__ import annotations

import json
from pathlib import Path

from .marktplaats import FeedLoader


def json_file_loader(path: str) -> FeedLoader:
    """Return a loader that reads listing dicts from a local JSON file."""

    def load() -> list[dict]:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw = raw.get("listings", [])
        if not isinstance(raw, list):
            raise ValueError(f"Feed file {path} must contain a list of listings")
        return [item for item in raw if isinstance(item, dict)]

    return load
