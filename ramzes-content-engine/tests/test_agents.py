import unittest

from agents import (
    run_content_team, research_agent, factcheck_agent,
    brand_guardian_agent, analytics_agent, platform_agent,
)


class AgentPipelineTests(unittest.TestCase):
    def test_full_team_hands_off_context_and_specialist_notes(self):
        calls = []

        def fake_model(messages, temperature, max_tokens, title, timeout=60, web_search=False):
            calls.append((messages, title, web_search))
            role = title.split(":")[-1].strip()
            return f"Результат {role}"

        result = run_content_team(fake_model, "Сделай пост", "Профиль RAMZES")
        self.assertIn("СТРАТЕГ", result["strategy_brief"])
        self.assertIn("копирайтер", result["draft"].lower())
        self.assertIn("audience", result["agent_notes"])
        self.assertIn("visual", result["agent_notes"])
        self.assertIn("Локальный поиск", result["draft"])
        self.assertGreaterEqual(len(calls), 8)

    def test_light_team_uses_two_agents(self):
        calls = []

        def fake_model(messages, temperature, max_tokens, title, timeout=60, web_search=False):
            calls.append(title)
            return title

        result = run_content_team(fake_model, "Помоги", full_team=False)
        self.assertEqual(len(calls), 2)
        self.assertTrue(result["draft"])

    def test_router_selected_content_extras_are_executed(self):
        calls = []

        def fake_model(messages, temperature, max_tokens, title, timeout=60, web_search=False):
            calls.append(title)
            return "Результат " + title

        result = run_content_team(
            fake_model,
            "Напиши пост для Threads, проверь заголовки, не повторяй темы и предложи гипотезу эксперимента",
            full_team=True,
            platforms=["Threads"],
            recent_topics=["Тема из архива"],
        )
        self.assertIn("headline_tester", result["agent_notes"])
        self.assertIn("experiment_planner", result["agent_notes"])
        self.assertIn("anti_repeat", result["agent_notes"])
        self.assertTrue(any("HEADLINE" in title.upper() for title in calls))

    def test_research_agent_requests_web_search(self):
        calls = []

        def fake_model(messages, temperature, max_tokens, title, timeout=60, web_search=False):
            calls.append(web_search)
            return "Исследование"

        self.assertEqual(research_agent(fake_model, "рынок тату").strip(), "Исследование")
        self.assertEqual(calls, [True])

    def test_specialists_are_separate_roles(self):
        titles = []
        def fake_model(messages, temperature, max_tokens, title, timeout=60, web_search=False):
            titles.append(title)
            return "Проверка"
        factcheck_agent(fake_model, "проверь", "текст")
        brand_guardian_agent(fake_model, "проверь", "текст")
        analytics_agent(fake_model, {"views": 100})
        platform_agent(fake_model, "адаптируй", "текст", "Threads")
        self.assertEqual(len(set(titles)), 4)


if __name__ == "__main__":
    unittest.main()
