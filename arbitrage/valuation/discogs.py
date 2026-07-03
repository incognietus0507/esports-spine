"""Discogs valuation via the OFFICIAL Discogs API.

Discogs is the global vinyl/CD marketplace and — unlike Catawiki — exposes a
documented API with real price data, so it is fully compliant to automate:

  * Database search            -> resolve a listing title to a release id
  * Marketplace price suggestions (auth) -> suggested price per condition
  * Marketplace stats          -> lowest current price + number for sale

We derive a robust market value from the per-condition price suggestions
(trimmed median), falling back to the lowest current marketplace price. Without
a token the valuator runs in MOCK mode so the pipeline stays exercisable.

Auth: a personal access token (https://www.discogs.com/settings/developers),
sent as ``Authorization: Discogs token=...``. Discogs requires a descriptive
User-Agent (else 403) and rate-limits to ~60 req/min — we throttle and back off.
"""
from __future__ import annotations

import re
import statistics
from urllib.parse import quote_plus

import httpx
import structlog

from ..config import DiscogsConfig
from ..httputil import get_with_backoff
from ..models import Listing, Valuation
from ..textutil import fold_text

log = structlog.get_logger(__name__)


class DiscogsValuator:
    def __init__(self, cfg: DiscogsConfig) -> None:
        self.cfg = cfg
        self._client = httpx.Client(
            timeout=25.0,
            headers={"User-Agent": cfg.user_agent},
        )

    def close(self) -> None:
        self._client.close()

    # -- public API ---------------------------------------------------------

    def value(self, listing: Listing) -> Valuation | None:
        if not self.cfg.enabled:
            return self._mock_value(listing)
        try:
            release_id = self._search_release(listing.title)
            if release_id is None:
                log.info("discogs.no_release", title=listing.title)
                return None
            suggestions = self._price_suggestions(release_id)
            lowest, num_for_sale = self._stats(release_id)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            # ValueError covers .json() on non-JSON bodies (WAF/CDN error
            # pages); KeyError covers changed API shapes. Returning None
            # leaves the listing unseen so it retries next run.
            log.warning(
                "discogs.failed", title=listing.title, error=str(exc), exc_info=True
            )
            return None
        return _aggregate(release_id, suggestions, lowest, num_for_sale)

    # -- HTTP ---------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Discogs token={self.cfg.token}"}

    def _get(self, url: str) -> httpx.Response:
        return get_with_backoff(self._client, url, headers=self._headers())

    def _search_release(self, title: str) -> int | None:
        """Resolve a listing title to a release id — but only when the match is
        plausible. Taking the first search hit blindly turns a mismatched
        release into a confidently wrong valuation, which is worse than none.

        A catalog number in the listing (e.g. "SHVL 804") is tried first: it is
        the most precise key Discogs has, so its top hit is trusted directly."""
        catno = _extract_catno(title)
        if catno:
            url = (
                f"{self.cfg.base_url}/database/search"
                f"?catno={quote_plus(catno)}&type=release&per_page=3"
            )
            results = self._get(url).json().get("results", []) or []
            rid = _pick_catno_result(catno, results)
            if rid is not None:
                log.debug("discogs.catno_hit", catno=catno, release=rid)
                return rid

        url = (
            f"{self.cfg.base_url}/database/search"
            f"?q={quote_plus(title)}&type=release&per_page=5"
        )
        results = self._get(url).json().get("results", []) or []
        return _best_release_match(title, results)

    def _price_suggestions(self, release_id: int) -> list[float]:
        """Per-condition suggested prices (Mint, NM, VG+, ...) for the currency."""
        url = f"{self.cfg.base_url}/marketplace/price_suggestions/{release_id}"
        try:
            data = self._get(url).json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                # Documented degrade: endpoint needs seller auth.
                log.debug("discogs.suggestions_unavailable", status=403)
                return []
            raise  # real outage — surface through value()'s handler
        prices: list[float] = []
        for entry in (data or {}).values():
            if isinstance(entry, dict):
                val = entry.get("value")
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    prices.append(float(val))
        return prices

    def _stats(self, release_id: int) -> tuple[float | None, int]:
        url = f"{self.cfg.base_url}/marketplace/stats/{release_id}?curr_abbr={self.cfg.currency}"
        try:
            data = self._get(url).json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                log.debug("discogs.stats_unavailable", status=403)
                return None, 0
            raise  # real outage — surface through value()'s handler
        num = data.get("num_for_sale") or 0
        lowest = (data.get("lowest_price") or {}).get("value")
        lowest_f = float(lowest) if isinstance(lowest, (int, float)) else None
        return lowest_f, int(num) if isinstance(num, (int, float)) else 0

    # -- mock ---------------------------------------------------------------

    def _mock_value(self, listing: Listing) -> Valuation:
        """Demo stand-in (no token). NOT a real valuation — set DISCOGS_TOKEN."""
        return Valuation(
            market_value=round(listing.price * 1.8 + 4, 2),
            comp_count=0,
            sold_count=0,
            confidence=0.0,
            sample_url="https://www.discogs.com/search/?q="
            + quote_plus(listing.title)
            + "&type=release",
        )


# Filler words that carry no identity signal when matching listing titles to
# Discogs release titles (EN + NL marketplace noise).
_MATCH_STOPWORDS = frozenset({
    "lp", "vinyl", "vinyl2", "record", "album", "cd", "ep", "12", "7",
    "nieuw", "nieuwe", "zgan", "nst", "seal", "sealed", "in", "the", "a",
    "de", "het", "een", "met", "en", "of", "and", "plaat", "elpee",
})
# A result must cover this share of its own tokens in the listing title, and
# share at least this many tokens, to count as the same release.
_MATCH_MIN_SCORE = 0.6
_MATCH_MIN_SHARED = 2


def _match_tokens(text: str) -> set[str]:
    return {
        tok
        for tok in re.findall(r"[a-z0-9]+", fold_text(text))
        if tok not in _MATCH_STOPWORDS
    }


# Catalog numbers ("SHVL 804", "BLP-1577") are the highest-precision Discogs
# lookup key a listing can contain. Letters then digits; excludes bare years
# and weights like "180 gram" (no letter prefix).
_CATNO_RE = re.compile(r"\b([A-Z]{2,6})([- ]?)(\d{2,6})\b")

# Uppercase abbreviations that precede numbers in ordinary vinyl-listing
# boilerplate but are never catalog-number prefixes: Record Store Day tags,
# country codes, condition grades, format tags.
_CATNO_PREFIX_BLOCKLIST = frozenset({
    "RSD", "EU", "UK", "US", "USA", "NL", "DE", "FR", "BE", "JP",
    "VG", "EX", "NM", "VA", "LP", "EP", "CD", "OBI",
})


def _looks_like_year(digits: str) -> bool:
    return len(digits) == 4 and digits[:2] in ("19", "20")


def _extract_catno(title: str) -> str | None:
    """Extract a plausible catalog number, rejecting boilerplate like
    "RSD 2020", "EU 1973", "VG 1985" that would hijack the catno search."""
    for m in _CATNO_RE.finditer(title):
        prefix, sep, digits = m.groups()
        if prefix in _CATNO_PREFIX_BLOCKLIST:
            continue
        # "ABC 1975" (space + year-shaped digits) is almost always
        # "<something> <year>", not a catalog number; dashed forms are kept.
        if sep != "-" and _looks_like_year(digits):
            continue
        return f"{prefix}{sep}{digits}"
    return None


def _normalize_catno(catno: str) -> str:
    return re.sub(r"[\s-]", "", catno).upper()


def _pick_catno_result(catno: str, results: list[dict]) -> int | None:
    """Trust a catno search hit only when the result's own catno field
    actually equals the extracted one — never blindly take the top hit."""
    want = _normalize_catno(catno)
    for r in results:
        rid = r.get("id")
        if not isinstance(rid, int):
            continue
        if _normalize_catno(str(r.get("catno", ""))) == want:
            return rid
    return None


def _best_release_match(listing_title: str, results: list[dict]) -> int | None:
    """Pick the search result whose title tokens are best covered by the
    listing title; reject everything below the plausibility threshold.

    Discogs result titles are "Artist - Title": the artist segment must share
    at least one token with the listing, so a same-titled album by a different
    artist can't win on title overlap alone."""
    listing_tokens = _match_tokens(listing_title)
    if not listing_tokens:
        return None

    best_id: int | None = None
    best_score = 0.0
    for r in results:
        rid = r.get("id")
        if not isinstance(rid, int):
            continue
        result_title = str(r.get("title", ""))
        result_tokens = _match_tokens(result_title)
        if not result_tokens:
            continue
        if " - " in result_title:
            artist_tokens = _match_tokens(result_title.split(" - ", 1)[0])
            # "Various (Artists)" compilations have no artist identity to
            # cross-check — sellers rarely write "various" in the title.
            is_compilation = artist_tokens <= {"various", "artists", "va"}
            if artist_tokens and not is_compilation and not (
                artist_tokens & listing_tokens
            ):
                continue  # artist mismatch — same title is not enough
        shared = listing_tokens & result_tokens
        score = len(shared) / len(result_tokens)
        if len(shared) >= _MATCH_MIN_SHARED and score > best_score:
            best_score = score
            best_id = rid

    if best_score < _MATCH_MIN_SCORE:
        return None
    return best_id


# Discogs stats are ASKING prices (suggestions + lowest-for-sale), not realized
# sales, so confidence never reaches the level of true sold comps.
_ASKING_PRICE_CONFIDENCE_CAP = 0.7


def _aggregate(
    release_id: int,
    suggestions: list[float],
    lowest: float | None,
    num_for_sale: int,
) -> Valuation | None:
    """Prefer per-condition price suggestions (trimmed median); else the lowest
    current marketplace price. Confidence scales with the number for sale."""
    if suggestions:
        market_value = _trimmed_median(sorted(suggestions))
    elif lowest is not None:
        market_value = lowest
    else:
        return None

    confidence = min(1.0, num_for_sale / 20.0)
    if suggestions:
        confidence = min(1.0, confidence + 0.3)
    confidence = min(confidence, _ASKING_PRICE_CONFIDENCE_CAP)

    return Valuation(
        market_value=round(market_value, 2),
        comp_count=num_for_sale,
        sold_count=0,  # Discogs exposes for-sale stats, not sold counts via this path
        confidence=round(confidence, 2),
        sample_url=f"https://www.discogs.com/release/{release_id}",
    )


def _trimmed_median(prices: list[float]) -> float:
    if len(prices) >= 6:
        prices = prices[1:-1]  # drop the Mint-sealed high and the Poor low
    return statistics.median(prices)
