"""Deterministic analytics for RAMZES AI. No model calls or inferred metrics."""
from collections import defaultdict


def _number(row, key):
    value = row.get(key)
    try:
        return max(0.0, float(value)) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def publication_analytics(metrics):
    rows = list(metrics or [])
    totals = defaultdict(float)
    by_platform = defaultdict(lambda: defaultdict(float))
    for row in rows:
        platform = str(row.get("platform") or "unknown")
        for key in ("views", "likes", "comments", "reposts", "saves",
                    "profile_visits", "followers_gained", "inbound_messages", "bookings"):
            value = _number(row, key)
            totals[key] += value
            by_platform[platform][key] += value
    views = totals["views"]
    interactions = totals["likes"] + totals["comments"] + totals["reposts"] + totals["saves"]
    totals_out = {key: int(value) if value.is_integer() else round(value, 2) for key, value in totals.items()}
    totals_out["engagement_rate"] = round(interactions / views, 4) if views else None
    platforms = {}
    for platform, values in by_platform.items():
        pviews = values["views"]
        interactions = values["likes"] + values["comments"] + values["reposts"] + values["saves"]
        platforms[platform] = {
            key: int(value) if value.is_integer() else round(value, 2)
            for key, value in values.items()
        }
        platforms[platform]["engagement_rate"] = round(interactions / pviews, 4) if pviews else None
    return {"sample_size": len(rows), "totals": totals_out, "by_platform": platforms}


def funnel_analytics(leads, bookings):
    leads = list(leads or [])
    bookings = list(bookings or [])
    qualified = sum(1 for item in leads if str(item.get("stage", "new")) in {"qualified", "consultation", "booked", "completed"})
    booked = sum(1 for item in bookings if item.get("status") in {"booked", "completed"})
    completed = sum(1 for item in bookings if item.get("status") == "completed")
    cancelled = sum(1 for item in bookings if item.get("status") == "cancelled")
    amounts = [_number(item, "amount") for item in bookings if item.get("status") == "completed" and item.get("amount") is not None]
    return {
        "leads": len(leads),
        "qualified_leads": qualified,
        "booked_sessions": booked,
        "completed_sessions": completed,
        "cancelled_sessions": cancelled,
        "lead_to_booking_rate": round(booked / len(leads), 4) if leads else None,
        "booking_completion_rate": round(completed / booked, 4) if booked else None,
        "completed_revenue": round(sum(amounts), 2),
        "average_completed_check": round(sum(amounts) / len(amounts), 2) if amounts else None,
    }


def build_analytics_snapshot(metrics, leads, bookings):
    return {
        "publications": publication_analytics(metrics),
        "booking_funnel": funnel_analytics(leads, bookings),
        "data_limitations": [
            "Закрытая статистика площадок не подгружается автоматически.",
            "Заявки и записи учитываются только после передачи из подключённого источника или ручного ввода владельцем.",
            "Показатели без исходных данных не оцениваются и не заменяются догадками.",
        ],
    }


def render_daily_report(metrics, leads, bookings, market_count=0):
    snapshot = build_analytics_snapshot(metrics, leads, bookings)
    p = snapshot["publications"]
    f = snapshot["booking_funnel"]
    t = p["totals"]
    rate = "нет данных" if t["engagement_rate"] is None else f'{t["engagement_rate"]:.1%}'
    conversion = "нет данных" if f["lead_to_booking_rate"] is None else f'{f["lead_to_booking_rate"]:.1%}'
    avg = "нет данных" if f["average_completed_check"] is None else f'{f["average_completed_check"]:,.0f} ₽'.replace(",", " ")
    return (
        "📊 RAMZES AI · ЕЖЕДНЕВНАЯ СВОДКА\n\n"
        f"Публикации в выборке: {p['sample_size']}\n"
        f"Просмотры: {t['views']} · взаимодействия: {t['likes'] + t['comments'] + t['reposts'] + t['saves']}\n"
        f"Вовлечённость от просмотров: {rate}\n"
        f"Заявки: {f['leads']} · записи: {f['booked_sessions']} · завершено: {f['completed_sessions']}\n"
        f"Конверсия заявка → запись: {conversion}\n"
        f"Выручка по завершённым сеансам: {f['completed_revenue']:,.0f} ₽\n"
        f"Средний чек по завершённым сеансам: {avg}\n"
        f"Новые публичные материалы рынка: {int(market_count)}\n\n"
        "Важно: сводка учитывает только фактически переданные данные. "
        "Закрытые охваты конкурентов и отсутствующие показатели не оцениваются."
    )
