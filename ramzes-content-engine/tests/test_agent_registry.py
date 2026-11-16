import unittest

from agent_registry import AGENTS, plan_task
from agents import run_specialist_team
from agent_tools import (
    score_lead, calculate_offer_economics, find_repeated_topics,
    audit_metrics, check_publication, analyze_booking_funnel,
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

    def test_research_request_executes_market_and_trend_specialists(self):
        calls = []

        def fake_model(messages, temperature, max_tokens, title, timeout=60, web_search=False):
            calls.append((title, web_search))
            return "Результат: " + title

        result = run_specialist_team(
            fake_model, "Изучи конкурентов и тренды тату Новосибирска",
            task_context="Исследуй открытый рынок и публичные предложения"
        )
        self.assertEqual(result["task_plan"]["task_type"], "research")
        self.assertIn("market_researcher", result["agent_outputs"])
        self.assertIn("competitor_watch", result["agent_outputs"])
        self.assertIn("trend_radar", result["agent_outputs"])
        self.assertTrue(calls[0][1])

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

    def test_publication_analytics_routes_to_analytics_team(self):
        plan = plan_task("Сделай аналитику публикаций и сравни результаты Threads")
        self.assertEqual(plan["task_type"], "analytics")
        self.assertIn("analytics", plan["agents"])
        self.assertIn("data_auditor", plan["agents"])
        self.assertIn("experiment_planner", plan["agents"])

    def test_plain_publication_analysis_is_not_misrouted_to_content(self):
        plan = plan_task("Сделай анализ публикаций")
        self.assertEqual(plan["task_type"], "analytics")
        self.assertIn("analytics", plan["agents"])

    def test_lead_and_booking_requests_route_to_funnel_tools(self):
        plan = plan_task("Проанализируй заявки и записи, найди потери в воронке")
        self.assertEqual(plan["task_type"], "sales")
        self.assertIn("lead_scorer", plan["agents"])
        self.assertIn("lead_qualifier", plan["agents"])
        self.assertIn("booking_funnel", plan["agents"])

    def test_portfolio_request_routes_to_archivist(self):
        plan = plan_task("Разбери портфолио и разложи фотографии по стилям")
        self.assertIn("portfolio_archivist", plan["agents"])


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

    def test_booking_funnel_calculates_only_provided_events(self):
        result = analyze_booking_funnel([
            {"stage": "inquiry"}, {"stage": "inquiry"},
            {"stage": "qualified"}, {"stage": "booked"},
        ])
        self.assertEqual(result["counts"]["inquiry"], 2)
        self.assertEqual(result["conversion_percent"]["inquiry_to_qualified"], 50.0)

    def test_publication_preflight_blocks_internal_notes(self):
        result = check_publication("Это достаточно длинный текст для тестовой публикации. ВНУТРЕННИЕ ЗАМЕЧАНИЯ", "threads")
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
