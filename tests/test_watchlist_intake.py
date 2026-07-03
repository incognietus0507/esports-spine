"""Tests for the watchlist filter and the intake CLI helper."""
import json
import os
import tempfile
import unittest

from arbitrage.intake import append_listing
from arbitrage.sources import MarktplaatsSource, json_file_loader
from arbitrage.watchlist import load_watchlist, matches


class WatchlistTests(unittest.TestCase):
    def _write(self, text: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        self.addCleanup(os.unlink, path)
        return path

    def test_loads_terms_skipping_comments_and_blanks(self) -> None:
        path = self._write("# jazz\nMiles Davis\n\nBlue Note  # label\n")
        self.assertEqual(load_watchlist(path), ["Miles Davis", "Blue Note"])

    def test_missing_file_disables_filtering(self) -> None:
        self.assertEqual(load_watchlist("/nonexistent/watch.txt"), [])
        self.assertTrue(matches("anything", []))

    def test_case_insensitive_substring_match(self) -> None:
        terms = ["Miles Davis"]
        self.assertTrue(matches("MILES DAVIS - kind of blue LP", terms))
        self.assertFalse(matches("ABBA Gold", terms))


class IntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.feed = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(self.feed)  # append_listing must create it
        self.addCleanup(lambda: os.path.exists(self.feed) and os.unlink(self.feed))

    def test_append_creates_file_and_roundtrips_through_source(self) -> None:
        added = append_listing(
            self.feed, "Miles Davis Kind of Blue LP", "€ 25", "https://x/1", "Utrecht"
        )
        self.assertTrue(added)
        out = MarktplaatsSource(feed_loader=json_file_loader(self.feed)).fetch(10)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].price, 25.0)
        self.assertEqual(out[0].location, "Utrecht")

    def test_duplicate_url_skipped(self) -> None:
        append_listing(self.feed, "a", "10", "https://x/1")
        added = append_listing(self.feed, "a again", "12", "https://x/1")
        self.assertFalse(added)
        data = json.loads(open(self.feed, encoding="utf-8").read())
        self.assertEqual(len(data), 1)

    def test_corrupt_feed_raises_cleanly_not_silently(self) -> None:
        with open(self.feed, "w", encoding="utf-8") as f:
            f.write("{not json")
        with self.assertRaises(json.JSONDecodeError):
            append_listing(self.feed, "x", "5", "https://x/9")
        # and the corrupt original is untouched (no truncation)
        self.assertEqual(open(self.feed, encoding="utf-8").read(), "{not json")

    def test_no_tmp_file_left_behind(self) -> None:
        append_listing(self.feed, "a", "10", "https://x/1")
        self.assertFalse(os.path.exists(self.feed + ".tmp"))

    def test_appends_to_wrapped_format(self) -> None:
        with open(self.feed, "w", encoding="utf-8") as f:
            json.dump({"listings": [{"title": "x", "price": 5, "url": "https://x/0"}]}, f)
        added = append_listing(self.feed, "y", "7", "https://x/1")
        self.assertTrue(added)
        out = MarktplaatsSource(feed_loader=json_file_loader(self.feed)).fetch(10)
        self.assertEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()
