import unittest

from analytics_engine import publication_analytics, funnel_analytics, build_analytics_snapshot
from business_data import parse_lead, parse_booking


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

    def test_snapshot_keeps_limitations(self):
        result = build_analytics_snapshot([], [], [])
        self.assertTrue(result["data_limitations"])


if __name__ == "__main__":
    unittest.main()
