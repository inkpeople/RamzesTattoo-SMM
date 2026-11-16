import unittest

from agent_registry import AGENTS, plan_task
from agent_tools import (
    score_lead, calculate_offer_economics, find_repeated_topics,
    audit_metrics, check_publication,
)


class AgentRegistryTests(unittest.TestCase):
    def test_registry_contains_37_unique_agents(self):
        ids = [agent.agent_id for agent in AGENTS]
        self.assertEqual(len(ids), 37)
        self.assertEqual(len(ids), len(set(ids)))

    def test_content_request_selects_bounded_content_team(self):
        plan = plan_task("Напиши пост для Threads о первой татуировке", full_team=True)
        self.assertEqual(plan["task_type"], "content")
        self.assertIn("copywriter", plan["agents"])
        self.assertIn("platform_editor", plan["agents"])
        self.assertLessEqual(plan["llm_agent_count"], 16)

    def test_simple_request_uses_light_team(self):
        plan = plan_task("Напиши короткий пост", full_team=False)
        self.assertEqual(plan["agents"], ["orchestrator", "strategist", "copywriter"])

    def test_market_request_selects_research_roles(self):
        plan = plan_task("Изучи конкурентов и тренды тату Новосибирска")
        self.assertIn("market_researcher", plan["agents"])
        self.assertIn("competitor_watch", plan["agents"])
        self.assertIn("trend_radar", plan["agents"])

    def test_approval_is_required_for_outbound_communication_tasks(self):
        plan = plan_task("Подготовь ответ клиенту на комментарий")
        self.assertTrue(plan["approval_required"])


class DeterministicAgentTests(unittest.TestCase):
    def test_lead_score_is_explainable(self):
        result = score_lead({"asked_booking": True, "project_description": "рукав",
                             "placement": "рука", "style": "графика", "timeline_days": 14})
        self.assertEqual(result["score"], 90)
        self.assertEqual(result["priority"], "высокий")
        self.assertTrue(result["reasons"])

    def test_offer_economics(self):
        result = calculate_offer_economics(10000, 1500, 2000)
        self.assertEqual(result["revenue_after_discount"], 8500)
        self.assertEqual(result["gross_profit_before_overheads_and_taxes"], 6500)

    def test_offer_rejects_invalid_discount(self):
        with self.assertRaises(ValueError):
            calculate_offer_economics(1000, 1200, 100)

    def test_repeat_detection(self):
        result = find_repeated_topics(["Как выбрать тату-мастера"], ["Как выбрать тату мастера"])
        self.assertEqual(len(result), 1)

    def test_metrics_require_source_and_period(self):
        result = audit_metrics([{"value": 100, "source": "VK", "period": "7 дней"}, {"value": 20}])
        self.assertFalse(result["valid"])
        self.assertEqual(len(result["issues"]), 1)

    def test_publication_preflight_blocks_internal_notes(self):
        result = check_publication("Это достаточно длинный текст для тестовой публикации. ВНУТРЕННИЕ ЗАМЕЧАНИЯ", "threads")
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
