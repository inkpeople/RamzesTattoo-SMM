import os
import tempfile
import unittest
import market_monitor_worker as worker


class MarketMonitorHelpersTests(unittest.TestCase):
    def test_normalize_url_removes_tracking_parameters(self):
        self.assertEqual(
            worker.normalize_url("https://Example.com/post?utm_source=x&id=7&fbclid=abc"),
            "https://example.com/post?id=7",
        )

    def test_invalid_url_is_rejected(self):
        self.assertEqual(worker.normalize_url("javascript:alert(1)"), "")

    def test_digest_ignores_case_and_whitespace(self):
        self.assertEqual(worker.digest("A  B"), worker.digest("a b"))

    def test_store_new_sources_deduplicates_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_path = worker.DB_PATH
            worker.DB_PATH = os.path.join(tmp, "market.sqlite")
            try:
                worker.init_db()
                row = {
                    "url": "https://example.com/post",
                    "source_type": "threads",
                    "title": "Test",
                    "snippet": "Fragment",
                    "published_at": "",
                }
                self.assertEqual(len(worker.store_new_sources([row, row])), 1)
                self.assertEqual(len(worker.store_new_sources([row])), 0)
            finally:
                worker.DB_PATH = old_path


if __name__ == "__main__":
    unittest.main()
