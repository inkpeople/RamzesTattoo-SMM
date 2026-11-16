import unittest

from agents import run_content_team, research_agent


class AgentPipelineTests(unittest.TestCase):
    def test_content_team_passes_strategy_to_copywriter(self):
        calls = []

        def fake_model(messages, temperature, max_tokens, title, timeout=60, web_search=False):
            calls.append((messages, title, web_search))
            return "Бриф" if "СТРАТЕГ" in title else "Черновик"

        result = run_content_team(fake_model, "Сделай пост", "Профиль RAMZES")
        self.assertEqual(result["strategy_brief"], "Бриф")
        self.assertEqual(result["draft"], "Черновик")
        self.assertEqual(len(calls), 2)
        self.assertIn("Бриф", calls[1][0][1]["content"])

    def test_research_agent_requests_web_search(self):
        calls = []

        def fake_model(messages, temperature, max_tokens, title, timeout=60, web_search=False):
            calls.append(web_search)
            return "Исследование"

        self.assertEqual(research_agent(fake_model, "рынок тату").strip(), "Исследование")
        self.assertEqual(calls, [True])


if __name__ == "__main__":
    unittest.main()
