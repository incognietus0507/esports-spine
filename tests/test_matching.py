"""Phase 2 matching quality: diacritics, catalog numbers, artist guard.

Written RED-first (TDD): these describe the behaviour before implementation.
"""
import unittest

from arbitrage.textutil import fold_text
from arbitrage.valuation.discogs import (
    _best_release_match,
    _extract_catno,
    _pick_catno_result,
)
from arbitrage.watchlist import matches


class FoldTextTests(unittest.TestCase):
    def test_strips_diacritics(self) -> None:
        self.assertEqual(fold_text("Motörhead"), "motorhead")
        self.assertEqual(fold_text("André Hazes"), "andre hazes")
        self.assertEqual(fold_text("Björk"), "bjork")

    def test_plain_ascii_untouched(self) -> None:
        self.assertEqual(fold_text("Miles Davis"), "miles davis")

    def test_non_decomposing_letters_transliterated(self) -> None:
        # NFKD alone leaves these untouched (review finding).
        self.assertEqual(fold_text("Røyksopp"), "royksopp")
        self.assertEqual(fold_text("Straße"), "strasse")
        self.assertEqual(fold_text("Ærø"), "aero")


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

    def test_rejects_boilerplate_abbreviations(self) -> None:
        # Review finding: these hijacked the catno search as false positives.
        self.assertIsNone(_extract_catno("Pink Floyd LP RSD 2020 limited"))
        self.assertIsNone(_extract_catno("Various EU 1973 pressing gatefold"))
        self.assertIsNone(_extract_catno("Queen Greatest Hits EX 1980 vinyl"))
        self.assertIsNone(_extract_catno("Nirvana Nevermind US 1991 first press"))

    def test_rejects_space_separated_year_keeps_dashed(self) -> None:
        self.assertIsNone(_extract_catno("Golden Earring MOON 1973 repress"))
        self.assertEqual(_extract_catno("Impulse AS-2010 stereo"), "AS-2010")


class CatnoVerificationTests(unittest.TestCase):
    def test_only_trusts_result_with_matching_catno(self) -> None:
        results = [
            {"id": 1, "catno": "TOTALLY-DIFFERENT"},
            {"id": 2, "catno": "shvl 804"},  # normalized match
        ]
        self.assertEqual(_pick_catno_result("SHVL 804", results), 2)

    def test_none_when_no_result_carries_the_catno(self) -> None:
        results = [{"id": 1, "catno": "OTHER-1"}]
        self.assertIsNone(_pick_catno_result("SHVL 804", results))


class ArtistGuardTests(unittest.TestCase):
    def test_rejects_same_album_title_by_other_artist(self) -> None:
        # High title overlap but the artist segment shares nothing.
        # (A named artist — "Various" is a compilation wildcard, tested below.)
        results = [{"id": 9, "title": "Slade - Greatest Hits Live"}]
        self.assertIsNone(_best_release_match("Queen Greatest Hits Live LP", results))

    def test_accepts_when_artist_segment_shared(self) -> None:
        results = [{"id": 10, "title": "Queen - Greatest Hits Live"}]
        self.assertEqual(
            _best_release_match("Queen Greatest Hits Live LP", results), 10
        )

    def test_various_artists_compilation_not_falsely_rejected(self) -> None:
        # Review finding: sellers rarely write "Various" in a listing title.
        results = [{"id": 11, "title": "Various - Top Hits 2020"}]
        self.assertEqual(
            _best_release_match("Top Hits 2020 verzamel LP", results), 11
        )

    def test_scandinavian_name_matches_across_special_letters(self) -> None:
        results = [{"id": 12, "title": "Røyksopp - Melody A.M."}]
        self.assertEqual(
            _best_release_match("Royksopp Melody AM 2LP", results), 12
        )


class WatchlistFoldingTests(unittest.TestCase):
    def test_watchlist_matches_across_accents(self) -> None:
        self.assertTrue(matches("Andre Hazes - Gewoon Andre LP", ["André Hazes"]))
        self.assertTrue(matches("MOTÖRHEAD lp bomb", ["Motorhead"]))


if __name__ == "__main__":
    unittest.main()
