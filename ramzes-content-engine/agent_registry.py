"""Deterministic task routing and specialist registry for RAMZES AI.

Routing is intentionally keyword/rule based: it is cheap, predictable and does not
consume model tokens. It selects a small team; it never performs external actions.
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    name: str
    group: str
    triggers: tuple
    requires_llm: bool = True
    approval_required: bool = False
    max_tokens: int = 1800


# Stable identifiers are used in logs, tests and future memory records.
AGENTS = (
    AgentSpec("orchestrator", "Главный управляющий", "management", (), False, False, 0),
    AgentSpec("market_researcher", "Исследователь рынка", "strategy", ("рынок", "исследуй", "конкурент", "тренд"), True, False, 5000),
    AgentSpec("strategist", "Главный стратег", "strategy", ("стратегия", "план", "пост", "контент"), True, False, 2400),
    AgentSpec("audience", "Исследователь аудитории", "strategy", ("аудитория", "клиент", "возражен", "страх"), True, False, 1800),
    AgentSpec("positioning", "Эксперт по позиционированию", "strategy", ("позиционирование", "отстройка", "конкурент"), True, False, 1600),
    AgentSpec("hooks", "Специалист по хукам", "content", ("пост", "threads", "заголовок", "хук"), True, False, 1800),
    AgentSpec("copywriter", "Копирайтер", "content", ("напиши", "пост", "текст", "сценарий"), True, False, 5000),
    AgentSpec("platform_editor", "Редактор площадки", "content", ("threads", "вк", "vk", "instagram", "инстаграм", "telegram", "телеграм"), True, False, 3500),
    AgentSpec("seo", "SEO-специалист", "content", ("seo", "поиск", "ключев", "wordstat"), True, False, 1800),
    AgentSpec("visual", "Арт-директор", "content", ("изображение", "визуал", "фото", "видео", "съёмк", "съемк"), True, False, 1800),
    AgentSpec("conversion", "Эксперт по конверсии", "sales", ("заявк", "запись", "продаж", "конверси", "оффер"), True, False, 1800),
    AgentSpec("editor", "Выпускающий редактор", "quality", ("проверь", "отредактируй", "улучши", "пост"), True, False, 5000),
    AgentSpec("factcheck", "Фактчекер", "quality", ("проверь", "факт", "цифр", "источник"), True, False, 2500),
    AgentSpec("brand_guardian", "Хранитель бренда", "quality", ("бренд", "стиль", "тон", "пост"), True, False, 1800),
    AgentSpec("analytics", "Аналитик эффективности", "analytics", ("аналитик", "статистик", "охват", "просмотр", "метрик", "результат"), True, False, 3000),
    AgentSpec("campaigns", "Планировщик кампаний", "sales", ("кампан", "воронк", "акци", "промо", "контент-план"), True, False, 3000),
    AgentSpec("community", "Менеджер сообщества", "sales", ("комментар", "коммент", "ответь", "переписк", "сообщени"), True, True, 2200),
    AgentSpec("competitor_watch", "Конкурентный наблюдатель", "research", ("конкурент", "студии", "мастеров", "цены конкурентов"), True, False, 2200),
    AgentSpec("trend_radar", "Радар трендов", "research", ("тренд", "вирусн", "мем", "актуальн", "что сейчас"), True, False, 2200),
    AgentSpec("lead_finder", "Поисковик клиентов", "sales", ("найди клиентов", "где ищут мастера", "ищут тату", "запросы на тату"), True, True, 2200),
    AgentSpec("lead_qualifier", "Квалификатор заявок", "sales", ("квалифиц", "разбери заявку", "заявка", "обращение"), True, False, 1600),
    AgentSpec("lead_scorer", "Оценщик лидов", "sales", ("приоритет заяв", "оцени лид", "горячий клиент"), False, False, 0),
    AgentSpec("objection_analyst", "Аналитик возражений", "sales", ("возражен", "дорого", "сомнени", "почему не записываются"), True, False, 1800),
    AgentSpec("reply_assistant", "Помощник переписки", "sales", ("ответ клиенту", "ответь клиенту", "что ответить", "сообщение клиенту"), True, True, 1800),
    AgentSpec("booking_funnel", "Контролёр пути заявки", "analytics", ("путь заявки", "воронка записи", "конверсия в запись"), False, False, 0),
    AgentSpec("client_return", "Возвращатель клиентов", "sales", ("вернуть клиента", "повторный сеанс", "повторная запись"), True, True, 1800),
    AgentSpec("audience_segments", "Сегментатор аудитории", "strategy", ("сегмент", "группы клиентов", "аудитория"), True, False, 1800),
    AgentSpec("reputation", "Аналитик репутации", "analytics", ("отзыв", "репутац", "обратная связь"), True, False, 1800),
    AgentSpec("referrals", "Менеджер рекомендаций", "sales", ("реферал", "рекомендац", "приведи друга"), True, False, 1800),
    AgentSpec("offer_economics", "Экономист предложений", "analytics", ("посчитай акцию", "скидк", "маржин", "экономик", "сертификат"), False, False, 0),
    AgentSpec("content_repurpose", "Машина переработки контента", "content", ("переработай", "адаптируй", "из одного поста", "контент-пакет"), True, False, 3000),
    AgentSpec("anti_repeat", "Антиповтор", "quality", ("не повторяй", "повтор", "новые темы", "архив контента"), False, False, 0),
    AgentSpec("portfolio_archivist", "Архивариус портфолио", "content", ("портфолио", "категоризируй работы", "разбери фотографии"), True, False, 1800),
    AgentSpec("headline_tester", "Тестировщик заголовков", "content", ("варианты заголов", "протестируй заголов", "заголовки"), True, False, 1600),
    AgentSpec("experiment_planner", "Планировщик экспериментов", "analytics", ("эксперимент", "a/b", "тест гипотез", "что проверить"), True, False, 1800),
    AgentSpec("publication_control", "Контролёр публикаций", "quality", ("проверь публикац", "перед публикацией", "проверка поста"), False, False, 0),
    AgentSpec("data_auditor", "Аудитор данных", "quality", ("проверь данные", "достоверность цифр", "аудит данных"), False, False, 0),
)

AGENT_BY_ID = {item.agent_id: item for item in AGENTS}

CONTENT_WORDS = ("пост", "публикац", "threads", "контент", "сторис", "reels", "сценарий", "текст")
RESEARCH_WORDS = ("конкурент", "рынок", "тренд", "исследуй", "что сейчас", "найди клиентов")
ANALYTICS_WORDS = ("аналитик", "аналитика", "статистик", "охват", "просмотр", "метрик", "результат", "конверсия", "эффективность", "сравни публикац", "сравни пост")
SALES_WORDS = ("заявк", "запись", "лид", "воронк", "клиент", "переписк", "комментар", "возражен", "акци", "оффер", "реферал", "отзыв", "репутац", "кампан", "сегмент", "вернуть клиента")


def _has(text, phrases):
    return any(phrase in text for phrase in phrases)


def plan_task(request, full_team=True, max_llm_agents=16):
    """Return a deterministic, bounded plan. No network/model calls are made."""
    text = str(request or "").lower()
    selected = ["orchestrator"]
    task_type = "general"

    direct_content = _has(text, ("напиши пост", "создай пост", "подготовь публикац", "сделай публикац", "напиши threads", "сценарий видео", "сценарии reels"))
    is_research = _has(text, RESEARCH_WORDS)
    is_analytics = _has(text, ANALYTICS_WORDS)
    is_content = _has(text, CONTENT_WORDS) and not is_analytics and not (_has(text, RESEARCH_WORDS) and not direct_content)
    is_sales = _has(text, SALES_WORDS)

    if is_content:
        task_type = "content"
        selected += ["strategist", "copywriter"]
        if full_team:
            selected += ["audience", "positioning", "hooks", "visual", "conversion", "seo", "factcheck", "brand_guardian", "editor"]
        if _has(text, ("threads", "вк", "vk", "instagram", "инстаграм", "telegram", "телеграм")):
            selected.append("platform_editor")
        if _has(text, ("переработай", "адаптируй", "из одного поста", "контент-пакет")):
            selected.append("content_repurpose")
        if _has(text, ("не повторяй", "новые темы", "архив контента")):
            selected.append("anti_repeat")
        if _has(text, ("заголов", "хук")):
            selected.append("headline_tester")
        if _has(text, ("портфолио", "фотограф")):
            selected.append("portfolio_archivist")
    elif is_research:
        task_type = "research"
        selected += ["market_researcher"]
        if _has(text, ("конкурент", "студии", "мастеров", "цены конкурентов")):
            selected += ["competitor_watch", "positioning"]
        if _has(text, ("тренд", "вирусн", "мем", "актуальн", "что сейчас")):
            selected.append("trend_radar")
        if _has(text, ("найди клиентов", "где ищут мастера", "ищут тату", "запросы на тату")):
            selected.append("lead_finder")
    elif is_analytics:
        task_type = "analytics"
        selected += ["analytics", "data_auditor", "experiment_planner"]
        if _has(text, ("воронка", "конверсия в запись", "путь заявки")):
            selected.append("booking_funnel")
        if _has(text, ("заявк", "лид", "обращение")):
            selected += ["lead_qualifier", "lead_scorer"]
        if _has(text, ("публикац", "пост", "threads", "reels")):
            selected += ["headline_tester", "publication_control"]
        if _has(text, ("репутац", "отзыв", "обратная связь")):
            selected.append("reputation")
    elif is_sales:
        task_type = "sales"
        selected += ["conversion"]
        if _has(text, ("заявк", "обращение")):
            selected += ["lead_qualifier", "lead_scorer"]
        if _has(text, ("ответ", "переписк", "комментар")):
            selected += ["community", "reply_assistant"]
        if _has(text, ("возражен", "дорого", "сомнени")):
            selected.append("objection_analyst")
        if _has(text, ("вернуть клиента", "повторный сеанс", "повторная запись")):
            selected.append("client_return")
        if _has(text, ("реферал", "рекомендац", "приведи друга")):
            selected.append("referrals")
        if _has(text, ("акци", "оффер", "скидк", "сертификат")):
            selected.append("offer_economics")
        if _has(text, ("сегмент", "группы клиентов", "аудитория")):
            selected.append("audience_segments")
        if _has(text, ("кампан", "промо", "контент-план")):
            selected.append("campaigns")
        if _has(text, ("репутац", "отзыв", "обратная связь")):
            selected.append("reputation")
    else:
        selected += ["strategist", "copywriter"]

    # Always unique and capped; deterministic tools do not consume LLM budget.
    unique = []
    for agent_id in selected:
        if agent_id not in unique:
            unique.append(agent_id)
    llm_ids = [agent_id for agent_id in unique if AGENT_BY_ID[agent_id].requires_llm]
    allowed_llm = set(llm_ids[:max(0, int(max_llm_agents))])
    unique = [agent_id for agent_id in unique if not AGENT_BY_ID[agent_id].requires_llm or agent_id in allowed_llm]
    return {
        "task_type": task_type,
        "agents": unique,
        "llm_agent_count": len([x for x in unique if AGENT_BY_ID[x].requires_llm]),
        "estimated_max_tokens": sum(AGENT_BY_ID[x].max_tokens for x in unique),
        "approval_required": any(AGENT_BY_ID[x].approval_required for x in unique),
        "agent_details": [asdict(AGENT_BY_ID[x]) for x in unique],
    }
