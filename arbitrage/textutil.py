"""Shared text normalization for matching across NL/EU listings."""
from __future__ import annotations

import unicodedata


def fold_text(text: str) -> str:
    """Lowercase and strip diacritics (Motörhead -> motorhead) so accented and
    plain spellings — common in Dutch listings — compare equal."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
