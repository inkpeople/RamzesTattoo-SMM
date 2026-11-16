import unittest

from analytics_engine import publication_analytics, funnel_analytics, build_analytics_snapshot
from business_data import parse_lead, parse_booking, parse_publication


class AnalyticsEngineTests(unittest.TestCase):
    def test_publication_engagement_uses_views_denominator(self):
        result = publication_analytics([{
            "platform": "threads", "views": 1000, "likes": 20,
            "comments": 5, "reposts": 3, "saves": 2
        }])
        self.assertEqual(result["totals"]["engagement_rate"], 0.03)

    def test_missing_views_does_not_invent_rate(self):
        result = publication_analytics([{"platform": "vk", "likes": 10}])
        self.assertIsNone(result["totals"]["engagement_rate"])

    def test_funnel_rates_and_revenue(self):
        result = funnel_analytics(
            [{"stage": "new"}, {"stage": "qualified"}],
            [{"status": "completed", "amount": 12000}, {"status": "cancelled", "amount": 5000}],
        )
        self.assertEqual(result["lead_to_booking_rate"], 0.5)
        self.assertEqual(result["completed_revenue"], 12000.0)

    def test_lead_parser_rejects_empty(self):
        with self.assertRaises(ValueError):
            parse_lead("неструктурированный текст")

    def test_lead_parser_normalizes_russian_fields(self):
        result = parse_lead("стиль: графика; зона: бедро; бюджет: 15000; источник: Threads")
        self.assertEqual(result["budget"], 15000)
        self.assertEqual(result["source_platform"], "threads")

    def test_booking_parser_validates_date_and_status(self):
        result = parse_booking("дата: 2026-11-20; сумма: 15000; статус: completed; источник: vk")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["amount"], 15000)
        with self.assertRaises(ValueError):
            parse_booking("дата: завтра; статус: booked")

    def test_snapshot_keeps_limitations_and_empty_totals(self):
        result = build_analytics_snapshot([], [], [])
        self.assertTrue(result["data_limitations"])
        self.assertEqual(result["publications"]["totals"]["views"], 0)
        self.assertIsNone(result["publications"]["totals"]["engagement_rate"])

    def test_publication_ranking_requires_linked_metrics(self):
        result = publication_analytics(
            [{"platform": "threads", "publication_id": 7, "views": 100, "likes": 10}],
            [{"id": 7, "platform": "threads", "topic": "Графика"}],
        )
        self.assertEqual(result["by_publication"][0]["publication_id"], "7")
        self.assertEqual(result["by_publication"][0]["engagement_rate"], 0.1)

    def test_booking_conversion_requires_explicit_lead_link(self):
        result = funnel_analytics(
            [{"id": 1, "stage": "new"}],
            [{"status": "booked", "amount": 10000}],
        )
        self.assertIsNone(result["lead_to_booking_rate"])

    def test_publication_parser(self):
        result = parse_publication(
            "platform=Threads; topic=Графика; hook=Почему; url=https://threads.net/p/abc; date=2026-11-17"
        )
        self.assertEqual(result["platform"], "threads")
        self.assertEqual(result["topic"], "Графика")
        with self.assertRaises(ValueError):
            parse_publication("platform=Threads; topic=Test; url=javascript:alert(1)")


if __name__ == "__main__":
    unittest.main()
