"""Marketplace source adapters (NL-focused)."""

from .base import Source
from .facebook import FacebookMarketplaceSource
from .feeds import json_file_loader
from .marktplaats import MarktplaatsSource

__all__ = [
    "Source",
    "FacebookMarketplaceSource",
    "MarktplaatsSource",
    "json_file_loader",
]
