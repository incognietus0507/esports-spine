"""Shared text normalization for matching across NL/EU listings."""
from __future__ import annotations

import unicodedata

# Letters with NO canonical decomposition — NFKD leaves them untouched, so we
# transliterate them explicitly (Røyksopp -> royksopp, Straße -> strasse).
_TRANSLITERATE = str.maketrans({
    "ø": "o", "Ø": "O",
    "æ": "ae", "Æ": "AE",
    "œ": "oe", "Œ": "OE",
    "ß": "ss",
    "đ": "d", "Đ": "D",
    "ð": "d", "Ð": "D",
    "þ": "th", "Þ": "TH",
    "ł": "l", "Ł": "L",
})


def fold_text(text: str) -> str:
    """Lowercase and strip diacritics/special letters (Motörhead -> motorhead,
    Røyksopp -> royksopp) so accented and plain spellings — common in Dutch
    listings — compare equal."""
    decomposed = unicodedata.normalize("NFKD", text.translate(_TRANSLITERATE))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
