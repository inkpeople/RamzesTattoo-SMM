"""Safe parsing helpers for owner-entered lead and booking events.

Only explicitly supplied business fields are stored. Do not put client names,
phone numbers, social handles, health details, or message transcripts here.
"""
from datetime import date
import re


ALIASES = {
    "source": "source_platform", "источник": "source_platform", "platform": "source_platform",
    "направление": "style", "стиль": "style", "зона": "zone",
    "бюджет": "budget", "срок": "deadline", "намерение": "intent",
    "проект": "project", "дата": "session_date", "сумма": "amount",
    "статус": "status", "лид": "lead_id",
}


def parse_fields(raw):
    result = {}
    for part in re.split(r"[;|\n]+", str(raw or "")):
        part = part.strip()
        if not part:
            continue
        match = re.match(r"^([^:=]+)\s*[:=]\s*(.+)$", part)
        if not match:
            continue
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        key = ALIASES.get(key, key)
        result[key] = value[:500]
    return result


def _money(value):
    if value is None or value == "":
        return None
    if str(value).strip().startswith("-"):
        raise ValueError("Сумма не может быть отрицательной.")
    digits = re.sub(r"[^0-9]", "", str(value))
    if not digits:
        raise ValueError("Сумма должна быть числом в рублях.")
    amount = int(digits)
    if amount < 0 or amount > 100000000:
        raise ValueError("Сумма вне допустимого диапазона.")
    return amount


def parse_lead(raw):
    fields = parse_fields(raw)
    allowed = {"source_platform", "intent", "project", "style", "zone", "budget", "deadline"}
    data = {key: value for key, value in fields.items() if key in allowed}
    if not data:
        raise ValueError("Укажи хотя бы одно поле: intent, project, style, zone, budget или deadline.")
    if "budget" in data:
        data["budget"] = _money(data["budget"])
    data["source_platform"] = str(data.get("source_platform", "unknown")).lower()[:40]
    return data


def parse_booking(raw):
    fields = parse_fields(raw)
    try:
        session_date = date.fromisoformat(fields.get("session_date", ""))
    except ValueError as exc:
        raise ValueError("Укажи дату сеанса в формате YYYY-MM-DD.") from exc
    status = str(fields.get("status", "booked")).lower()
    if status not in {"booked", "completed", "cancelled", "no_show"}:
        raise ValueError("Статус: booked, completed, cancelled или no_show.")
    amount = _money(fields.get("amount"))
    lead_id = fields.get("lead_id")
    if lead_id:
        if not lead_id.isdigit():
            raise ValueError("lead_id должен быть числом.")
        lead_id = int(lead_id)
    return {
        "session_date": session_date.isoformat(),
        "status": status,
        "amount": amount,
        "source_platform": str(fields.get("source_platform", "unknown")).lower()[:40],
        "lead_id": lead_id,
    }



def parse_publication(raw):
    fields = parse_fields(raw)
    platform = str(fields.get("source_platform") or fields.get("platform") or "unknown").lower()[:40]
    topic = str(fields.get("topic") or fields.get("тема") or "").strip()
    hook = str(fields.get("hook") or "").strip()
    url = str(fields.get("url") or "").strip()
    published_at = fields.get("published_at") or fields.get("date")
    if not topic:
        raise ValueError("Укажи тему публикации: topic=...")
    if url and not url.startswith(("https://", "http://")):
        raise ValueError("Ссылка должна начинаться с https:// или http://")
    if published_at:
        try:
            date.fromisoformat(published_at[:10])
        except ValueError as exc:
            raise ValueError("Дата публикации должна быть YYYY-MM-DD.") from exc
    return {
        "platform": platform,
        "topic": topic[:1000],
        "hook": hook[:500],
        "url": url[:2000],
        "published_at": published_at,
    }
