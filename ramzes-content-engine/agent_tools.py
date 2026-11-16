"""Deterministic, no-LLM helpers for RAMZES AI specialist roles."""

from difflib import SequenceMatcher


def score_lead(lead):
    """Explainable priority score from explicit request fields; no sensitive inference."""
    lead = lead if isinstance(lead, dict) else {}
    score = 0
    reasons = []
    if lead.get("asked_booking"):
        score += 35
        reasons.append("Человек прямо спросил о записи")
    if lead.get("project_description"):
        score += 20
        reasons.append("Есть описание проекта")
    if lead.get("placement"):
        score += 10
        reasons.append("Указана зона тела")
    if lead.get("style"):
        score += 10
        reasons.append("Указан желаемый стиль")
    if lead.get("budget_known"):
        score += 10
        reasons.append("Обсуждён бюджет")
    days = lead.get("timeline_days")
    if isinstance(days, (int, float)) and not isinstance(days, bool):
        if days <= 30:
            score += 15
            reasons.append("Срок реализации — в ближайший месяц")
        elif days <= 90:
            score += 8
            reasons.append("Срок реализации — в ближайшие три месяца")
    score = min(100, score)
    priority = "высокий" if score >= 65 else "средний" if score >= 35 else "низкий"
    return {"score": score, "priority": priority, "reasons": reasons,
            "missing": [key for key in ("project_description", "placement", "style")
                        if not lead.get(key)]}


def calculate_offer_economics(price, discount_rub=0, direct_cost=0):
    """Calculate transparent gross economics; does not invent overhead or taxes."""
    values = (price, discount_rub, direct_cost)
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in values):
        raise ValueError("Все суммы должны быть числами")
    if price < 0 or discount_rub < 0 or direct_cost < 0:
        raise ValueError("Суммы не могут быть отрицательными")
    if discount_rub > price:
        raise ValueError("Скидка не может превышать исходную цену")
    revenue = price - discount_rub
    return {
        "original_price": round(price, 2),
        "discount_rub": round(discount_rub, 2),
        "discount_percent": round((discount_rub / price * 100), 2) if price else 0,
        "revenue_after_discount": round(revenue, 2),
        "direct_cost": round(direct_cost, 2),
        "gross_profit_before_overheads_and_taxes": round(revenue - direct_cost, 2),
    }


def find_repeated_topics(new_topics, recent_topics, threshold=0.78):
    """Return possible semantic-string repeats using a transparent text similarity heuristic."""
    if not 0 <= threshold <= 1:
        raise ValueError("threshold должен быть от 0 до 1")
    recent = [str(item).strip() for item in (recent_topics or []) if str(item).strip()]
    findings = []
    for topic in (new_topics or []):
        candidate = str(topic).strip()
        if not candidate:
            continue
        best = max(
            ((SequenceMatcher(None, candidate.casefold(), old.casefold()).ratio(), old)
             for old in recent),
            default=(0.0, ""),
        )
        if best[0] >= threshold:
            findings.append({"topic": candidate, "similar_to": best[1],
                             "similarity": round(best[0], 3)})
    return findings


def audit_metrics(metrics):
    """Flag metrics without provenance or time window; do not infer missing values."""
    rows = metrics if isinstance(metrics, list) else []
    issues = []
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            issues.append({"index": index, "issue": "Запись метрики должна быть объектом"})
            continue
        missing = [key for key in ("value", "source", "period") if item.get(key) is None]
        if missing:
            issues.append({"index": index, "issue": "Не хватает полей: " + ", ".join(missing)})
        value = item.get("value")
        if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool)):
            issues.append({"index": index, "issue": "Значение метрики должно быть числом"})
    return {"valid": not issues, "issues": issues, "checked": len(rows)}


def analyze_booking_funnel(events):
    """Count explicit funnel stages and calculate adjacent conversion rates."""
    allowed = ("inquiry", "qualified", "consultation", "booked")
    counts = {stage: 0 for stage in allowed}
    for event in events or []:
        if isinstance(event, dict) and event.get("stage") in counts:
            counts[event["stage"]] += 1
    rates = {}
    for previous, current in zip(allowed, allowed[1:]):
        denominator = counts[previous]
        rates[previous + "_to_" + current] = (
            round(counts[current] / denominator * 100, 2) if denominator else None
        )
    return {"counts": counts, "conversion_percent": rates,
            "note": "Расчёт отражает только переданные события; пустые этапы не интерпретируются как нулевой спрос."}


def check_publication(text, platform=None):
    """Basic deterministic preflight; it never publishes anything."""
    content = str(text or "").strip()
    issues = []
    if not content:
        issues.append("Пустой материал")
    if len(content) < 30:
        issues.append("Слишком короткий материал: проверь, достаточно ли контекста")
    if "ВНУТРЕННИЕ ЗАМЕЧАНИЯ" in content or "НЕ ПУБЛИКОВАТЬ" in content:
        issues.append("В тексте остались внутренние заметки")
    if platform:
        limits = {"threads": 500, "vk": 15000, "telegram": 4096, "instagram": 2200}
        limit = limits.get(str(platform).lower())
        if limit and len(content) > limit:
            issues.append("Превышен ориентировочный лимит длины для " + str(platform))
    return {"passed": not issues, "issues": issues, "character_count": len(content)}
