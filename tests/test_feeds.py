"""Tests for the local JSON feed loader (the compliant Marktplaats input)."""
import json
import os
import tempfile
import unittest

from arbitrage.sources import MarktplaatsSource, json_file_loader


class JsonFileLoaderTests(unittest.TestCase):
    def _write(self, payload) -> str:
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        self.addCleanup(os.unlink, path)
        return path

    def test_bare_list(self) -> None:
        path = self._write(
            [{"title": "Pastoe kast", "price": "€ 1.250,00", "url": "https://x/1"}]
        )
        out = MarktplaatsSource(feed_loader=json_file_loader(path)).fetch(10)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].price, 1250.00)

    def test_wrapped_listings_key(self) -> None:
        path = self._write(
            {"listings": [{"title": "GB Color", "price": 35, "url": "https://x/2"}]}
        )
        out = MarktplaatsSource(feed_loader=json_file_loader(path)).fetch(10)
        self.assertEqual(len(out), 1)

    def test_non_dict_entries_skipped(self) -> None:
        path = self._write(["junk", {"title": "ok", "price": 5, "url": "https://x/3"}])
        out = MarktplaatsSource(feed_loader=json_file_loader(path)).fetch(10)
        self.assertEqual(len(out), 1)

    def test_invalid_shape_yields_empty_not_crash(self) -> None:
        path = self._write({"not_listings": True})
        out = MarktplaatsSource(feed_loader=json_file_loader(path)).fetch(10)
        self.assertEqual(out, [])

    def test_missing_file_yields_empty_not_crash(self) -> None:
        loader = json_file_loader("/nonexistent/feed.json")
        out = MarktplaatsSource(feed_loader=loader).fetch(10)
        self.assertEqual(out, [])  # adapter catches loader errors


if __name__ == "__main__":
    unittest.main()
