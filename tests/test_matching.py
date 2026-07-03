"""Phase 2 matching quality: diacritics, catalog numbers, artist guard.

Written RED-first (TDD): these describe the behaviour before implementation.
"""
import unittest

from arbitrage.textutil import fold_text
from arbitrage.valuation.discogs import _best_release_match, _extract_catno
from arbitrage.watchlist import matches


class FoldTextTests(unittest.TestCase):
    def test_strips_diacritics(self) -> None:
        self.assertEqual(fold_text("Motörhead"), "motorhead")
        self.assertEqual(fold_text("André Hazes"), "andre hazes")
        self.assertEqual(fold_text("Björk"), "bjork")

    def test_plain_ascii_untouched(self) -> None:
        self.assertEqual(fold_text("Miles Davis"), "miles davis")


class DiacriticsMatchingTests(unittest.TestCase):
    def test_listing_without_accents_matches_accented_release(self) -> None:
        results = [{"id": 1, "title": "Motörhead - Ace Of Spades"}]
        rid = _best_release_match("Motorhead Ace of Spades LP vinyl", results)
        self.assertEqual(rid, 1)

    def test_accented_listing_matches_plain_release(self) -> None:
        results = [{"id": 2, "title": "Andre Hazes - Gewoon Andre"}]
        rid = _best_release_match("André Hazes - Gewoon André LP zgan", results)
        self.assertEqual(rid, 2)


class CatnoExtractionTests(unittest.TestCase):
    def test_extracts_letters_digits_catno(self) -> None:
        self.assertEqual(
            _extract_catno("Pink Floyd Dark Side LP SHVL 804 eerste pers"),
            "SHVL 804",
        )
        self.assertEqual(_extract_catno("Blue Note BLP-1577 mono"), "BLP-1577")

    def test_ignores_years_and_formats(self) -> None:
        self.assertIsNone(_extract_catno("Pink Floyd LP uit 1973"))
        self.assertIsNone(_extract_catno("mooie plaat, 180 gram"))

    def test_none_when_absent(self) -> None:
        self.assertIsNone(_extract_catno("Miles Davis Kind of Blue"))


class ArtistGuardTests(unittest.TestCase):
    def test_rejects_same_album_title_by_other_artist(self) -> None:
        # High title overlap but the artist segment shares nothing.
        results = [{"id": 9, "title": "Various - Greatest Hits Live"}]
        self.assertIsNone(_best_release_match("Queen Greatest Hits Live LP", results))

    def test_accepts_when_artist_segment_shared(self) -> None:
        results = [{"id": 10, "title": "Queen - Greatest Hits Live"}]
        self.assertEqual(
            _best_release_match("Queen Greatest Hits Live LP", results), 10
        )


class WatchlistFoldingTests(unittest.TestCase):
    def test_watchlist_matches_across_accents(self) -> None:
        self.assertTrue(matches("Andre Hazes - Gewoon Andre LP", ["André Hazes"]))
        self.assertTrue(matches("MOTÖRHEAD lp bomb", ["Motorhead"]))


if __name__ == "__main__":
    unittest.main()
