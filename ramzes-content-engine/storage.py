import copy
import hashlib
import json
import logging
import re
from difflib import SequenceMatcher

import requests

log = logging.getLogger("ramzes-content-engine.storage")

SUPABASE_URL = __import__("os").getenv("SUPABASE_URL", "").strip().rstrip("/")
STORAGE_ENABLED = __import__("os").getenv("RAMZES_STORAGE_ENABLED", "false").strip().lower() in ("1", "true", "yes")
# This module runs only on the trusted bot server. Prefer the server-side
# service-role key; never place it in a client app or commit it to Git.
SUPABASE_SERVICE_KEY = __import__("os").getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
REST_URL = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else ""

DEFAULT_BRAND_PROFILE = {
    "positioning": "RAMZES — тату-мастер и художник из Новосибирска. Авторский подход: идея, композиция и гармония с телом важнее слепого копирования.",
    "confirmed_facts": [
        "RAMZES работает в тату-сфере с 2019 года.",
        "За профессиональный путь RAMZES работал более чем с 1000 людьми.",
        "Основные направления: реализм, графика и акварель.",
        "В работе важны индивидуальная идея, композиция и гармония с телом, а не слепое копирование чужой работы."
    ],
    "brand_voice": [
        "Естественный разговорный русский язык.",
        "Сильный, содержательный хук без пустого кликбейта.",
        "Уверенная авторская позиция без высокомерия.",
        "Конкретика вместо канцелярита и рекламных клише.",
        "Не превращать каждую публикацию в продажу."
    ],
    "content_pillars": [
        "Авторская позиция и дискуссия",
        "Экспертность и образование",
        "Художественный вкус и насмотренность",
        "Юмор и наблюдения",
        "Личность и творческий путь — только подтверждённые сведения",
        "Работы, доверие и коммерческие предложения"
    ],
    "personal_material": [],
    "audience": ["Люди из Новосибирска, интересующиеся татуировкой и авторским визуальным искусством."],
    "confirmed_workflows": [],
    "forbidden_assumptions": [
        "Не выдумывать биографию, привычки, интересы, личные истории и рабочие процессы.",
        "Не придумывать отзывы, цитаты, диалоги и истории клиентов.",
        "Не утверждать, что фотографии портфолио не ретушируются, без подтверждения.",
        "Не обещать конкретное старение, долговечность или внешний вид татуировки."
    ]
}


def enabled():
    return bool(STORAGE_ENABLED and REST_URL and SUPABASE_SERVICE_KEY)


def healthcheck():
    rows = _request(
        "GET",
        "ramzes_content_engine_brand_profile",
        params={"select": "telegram_user_id", "limit": "1"},
    )
    return rows is not None


def _headers(prefer=None):
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _request(method, table, params=None, payload=None, prefer=None):
    if not enabled():
        return None
    try:
        response = requests.request(
            method,
            f"{REST_URL}/{table}",
            params=params or {},
            json=payload,
            headers=_headers(prefer),
            timeout=12,
        )
        response.raise_for_status()
        if response.status_code == 204 or not response.text.strip():
            return []
        return response.json()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        # Avoid logging response bodies: database errors can contain row values.
        log.warning("Persistent storage request failed for %s (HTTP %s)", table, status)
        return None
    except Exception as exc:
        log.warning("Persistent storage request failed for %s (%s)", table, type(exc).__name__)
        return None


def _uid(telegram_user_id):
    try:
        return int(telegram_user_id)
    except (TypeError, ValueError):
        return None


def load_chat_history(chat_id, telegram_user_id):
    uid = _uid(telegram_user_id)
    if uid is None:
        return None
    rows = _request(
        "GET",
        "ramzes_content_engine_chat_history",
        params={"select": "messages", "telegram_user_id": f"eq.{uid}", "limit": "1"},
    )
    if rows is None:
        return None
    if not rows:
        return []
    messages = rows[0].get("messages") or []
    return messages[-16:] if isinstance(messages, list) else []


def save_chat_history(chat_id, telegram_user_id, messages):
    uid = _uid(telegram_user_id)
    try:
        cid = int(chat_id)
    except (TypeError, ValueError):
        return False
    if uid is None:
        return False
    result = _request(
        "POST",
        "ramzes_content_engine_chat_history",
        params={"on_conflict": "telegram_user_id"},
        payload={"telegram_user_id": uid, "chat_id": cid, "messages": messages[-16:]},
        prefer="resolution=merge-duplicates,return=minimal",
    )
    return result is not None


def clear_chat_history(telegram_user_id):
    uid = _uid(telegram_user_id)
    if uid is None:
        return False
    result = _request(
        "DELETE",
        "ramzes_content_engine_chat_history",
        params={"telegram_user_id": f"eq.{uid}"},
        prefer="return=minimal",
    )
    return result is not None


def load_brand_profile(telegram_user_id):
    uid = _uid(telegram_user_id)
    if uid is None:
        return copy.deepcopy(DEFAULT_BRAND_PROFILE)
    rows = _request(
        "GET",
        "ramzes_content_engine_brand_profile",
        params={"select": "profile", "telegram_user_id": f"eq.{uid}", "limit": "1"},
    )
    if rows is None:
        return dict(DEFAULT_BRAND_PROFILE)
    if rows:
        profile = rows[0].get("profile")
        if isinstance(profile, dict):
            merged = dict(DEFAULT_BRAND_PROFILE)
            merged.update(profile)
            return merged
    profile = copy.deepcopy(DEFAULT_BRAND_PROFILE)
    save_brand_profile(telegram_user_id, profile)
    return profile


def save_brand_profile(telegram_user_id, profile):
    uid = _uid(telegram_user_id)
    if uid is None:
        return False
    result = _request(
        "POST",
        "ramzes_content_engine_brand_profile",
        params={"on_conflict": "telegram_user_id"},
        payload={"telegram_user_id": uid, "profile": profile},
        prefer="resolution=merge-duplicates,return=minimal",
    )
    return result is not None


def add_brand_fact(telegram_user_id, fact):
    profile = load_brand_profile(telegram_user_id)
    facts = profile.setdefault("confirmed_facts", [])
    normalized = fact.strip()
    if not normalized:
        return False, profile
    if normalized.lower() not in [str(item).lower() for item in facts]:
        facts.append(normalized)
        profile["confirmed_facts"] = facts[-100:]
        if not save_brand_profile(telegram_user_id, profile):
            return False, profile
    return True, profile


def build_brand_context(profile):
    facts = profile.get("confirmed_facts") or []
    voice = profile.get("brand_voice") or []
    pillars = profile.get("content_pillars") or []
    personal = profile.get("personal_material") or []
    audience = profile.get("audience") or []
    workflows = profile.get("confirmed_workflows") or []
    return (
        "\n\nПРОФИЛЬ БРЕНДА RAMZES — ПОДТВЕРЖДЁННЫЕ ДАННЫЕ ИЗ ПОСТОЯННОЙ ПАМЯТИ:\n"
        f"Позиционирование: {profile.get('positioning', '')}\n"
        "Подтверждённые факты:\n- " + "\n- ".join(map(str, facts)) +
        "\nПодтверждённые личные материалы:\n- " + ("\n- ".join(map(str, personal)) if personal else "Пока не добавлены; не выдумывать.") +
        "\nПодтверждённые рабочие процессы:\n- " + ("\n- ".join(map(str, workflows)) if workflows else "Не описаны; не приписывать мастеру конкретные действия.") +
        "\nАудитория:\n- " + "\n- ".join(map(str, audience)) +
        "\nОпоры контента:\n- " + "\n- ".join(map(str, pillars)) +
        "\nГолос бренда:\n- " + "\n- ".join(map(str, voice)) +
        "\nПравило: этот профиль — источник фактов о RAMZES. Не добавляй к нему выдуманные сведения."
    )


def extract_topics(text):
    source = str(text or "")
    found = re.findall(
        r"(?im)^\s*(?:центральная тема|тема)\s*:\s*(.+?)\s*$",
        source,
    )
    cleaned = []
    for item in found:
        value = re.sub(r"\s+", " ", item).strip(" -*•")
        if value and value.lower() not in [x.lower() for x in cleaned]:
            cleaned.append(value)
    if cleaned:
        return cleaned[:20]
    headings = re.findall(r"(?m)^\s{0,3}#{1,3}\s+(.+?)\s*$", source)
    for item in headings:
        value = re.sub(r"^\d+[.)]\s*", "", item).strip()
        if value and value.lower() not in [x.lower() for x in cleaned]:
            cleaned.append(value[:180])
    return cleaned[:20]


def load_recent_content(telegram_user_id, limit=20):
    uid = _uid(telegram_user_id)
    if uid is None:
        return []
    rows = _request(
        "GET",
        "ramzes_content_engine_content_library",
        params={
            "select": "id,created_at,platform,content_type,pillar,topic,hook,status,content_hash",
            "telegram_user_id": f"eq.{uid}",
            "order": "created_at.desc",
            "limit": str(min(max(int(limit), 1), 50)),
        },
    )
    return rows if isinstance(rows, list) else []


def build_recent_content_context(items):
    if not items:
        return "\n\nАРХИВ КОНТЕНТА: пока нет сохранённых публикаций. Не утверждай, что темы уже использовались."
    lines = []
    seen = set()
    for item in items[:20]:
        topic = str(item.get("topic") or "").strip()
        hook = str(item.get("hook") or "").strip()
        key = topic.lower()
        if key and key not in seen:
            seen.add(key)
            lines.append(f"- {topic}" + (f" | хук: {hook[:140]}" if hook else ""))
    if not lines:
        return ""
    return (
        "\n\nАРХИВ НЕДАВНЕГО КОНТЕНТА RAMZES (не повторять тему, мысль или хук; искать новый угол):\n"
        + "\n".join(lines)
    )


def topic_repeat_issues(new_topics, recent_items, threshold=0.86):
    previous = []
    for item in recent_items or []:
        value = str(item.get("topic") or "").strip()
        previous.extend([part.strip() for part in value.split(" | ") if len(part.strip()) >= 18])
    issues = []
    for topic in new_topics or []:
        candidate = str(topic).strip()
        if len(candidate) < 18:
            continue
        for old in previous:
            score = SequenceMatcher(None, candidate.lower(), old.lower()).ratio()
            if score >= threshold:
                issues.append(f"Тема «{candidate}» слишком похожа на недавнюю публикацию «{old}» (сходство {score:.0%}).")
                break
    return issues


def save_content_pack(chat_id, telegram_user_id, content, content_type="content_pack", plan=""):
    uid = _uid(telegram_user_id)
    try:
        cid = int(chat_id)
    except (TypeError, ValueError):
        return None
    if uid is None or not content:
        return None
    body = str(content).strip()
    digest = hashlib.sha256(re.sub(r"\s+", " ", body).lower().encode("utf-8")).hexdigest()
    existing = _request(
        "GET",
        "ramzes_content_engine_content_library",
        params={
            "select": "id",
            "telegram_user_id": f"eq.{uid}",
            "content_hash": f"eq.{digest}",
            "limit": "1",
        },
    )
    if isinstance(existing, list) and existing:
        return existing[0].get("id")
    topics = extract_topics(plan or body)
    topic = " | ".join(topics[:12]) if topics else " ".join(body.splitlines()[:2])[:500]
    first_lines = [line.strip(" #*-") for line in body.splitlines() if line.strip()]
    hook = first_lines[0][:300] if first_lines else ""
    rows = _request(
        "POST",
        "ramzes_content_engine_content_library",
        payload={
            "telegram_user_id": uid,
            "chat_id": cid,
            "platform": "multi",
            "content_type": content_type,
            "pillar": "personal_brand",
            "topic": topic[:2000],
            "hook": hook,
            "body": body,
            "status": "draft",
            "content_hash": digest,
        },
        prefer="return=representation",
    )
    if isinstance(rows, list) and rows:
        return rows[0].get("id")
    return None


def load_recent_metrics(telegram_user_id, limit=30):
    uid = _uid(telegram_user_id)
    if uid is None:
        return []
    rows = _request(
        "GET",
        "ramzes_content_engine_metrics",
        params={
            "select": "platform,captured_at,views,likes,comments,reposts,saves,profile_visits,followers_gained,inbound_messages,bookings,ad_spend,notes,raw_metrics",
            "telegram_user_id": f"eq.{uid}",
            "order": "captured_at.desc",
            "limit": str(min(max(int(limit), 1), 100)),
        },
    )
    return rows if isinstance(rows, list) else []


_METRIC_LABELS = {
    "views": r"просмотр(?:а|ов)?|охват|views?",
    "likes": r"лайк(?:а|ов)?|likes?",
    "comments": r"комментар(?:ий|ия|иев|ии)?|comments?|ответ(?:а|ов)?",
    "reposts": r"репост(?:а|ов)?|reposts?|shares?",
    "saves": r"сохранени(?:е|я|й)|saves?",
    "profile_visits": r"переход(?:а|ов)?\s+(?:в\s+)?профил(?:ь|я)|посещени(?:е|я)\s+профил(?:я)?|profile visits?",
    "followers_gained": r"подписчик(?:а|ов)?|followers?",
    "inbound_messages": r"сообщени(?:е|я|й)|заявк(?:а|и|ок)|dm(?:s)?",
    "bookings": r"запис(?:ь|и|ей)|bookings?",
    "ad_spend": r"бюджет|расход(?:ы|ов)?|ad spend|spend",
}


def _metric_number(text, label_pattern):
    patterns = [
        rf"(\d[\d\s]*(?:[.,]\d+)?)\s*(?:{label_pattern})",
        rf"(?:{label_pattern})\s*[:=]?\s*(\d[\d\s]*(?:[.,]\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = re.sub(r"\s+", "", match.group(1)).replace(",", ".")
            try:
                number = float(value)
                return int(number) if number.is_integer() else number
            except ValueError:
                pass
    return None


def parse_metric_message(text):
    raw = str(text or "").strip()
    lowered = raw.lower()
    platform = "unknown"
    for key, aliases in {
        "threads": ["threads", "тредс", "трендс"],
        "instagram": ["instagram", "инстаграм", "инста", "reels", "рилс"],
        "vk": ["вк", "vkontakte", "вконтакте"],
        "telegram": ["telegram", "телеграм"],
    }.items():
        if any(alias in lowered for alias in aliases):
            platform = key
            break
    metrics = {key: _metric_number(raw, pattern) for key, pattern in _METRIC_LABELS.items()}
    metrics = {key: value for key, value in metrics.items() if value is not None}
    if not metrics:
        return None
    return {
        "platform": platform,
        "metrics": metrics,
        "raw_metrics": {"source_text": raw},
        "notes": raw[:1000],
    }


def save_metric(telegram_user_id, parsed):
    uid = _uid(telegram_user_id)
    if uid is None or not parsed:
        return False
    metrics = parsed.get("metrics") or {}
    payload = {
        "telegram_user_id": uid,
        "platform": parsed.get("platform", "unknown"),
        "raw_metrics": parsed.get("raw_metrics") or {},
        "notes": parsed.get("notes", ""),
    }
    allowed = {
        "views", "likes", "comments", "reposts", "saves", "profile_visits",
        "followers_gained", "inbound_messages", "bookings", "ad_spend"
    }
    for key, value in metrics.items():
        if key in allowed:
            payload[key] = value
    result = _request(
        "POST",
        "ramzes_content_engine_metrics",
        payload=payload,
        prefer="return=representation",
    )
    return isinstance(result, list) and bool(result)



def save_lead(telegram_user_id, lead_data, score=None):
    uid = _uid(telegram_user_id)
    if uid is None or not isinstance(lead_data, dict):
        return None
    rows = _request(
        "POST", "ramzes_content_engine_leads",
        payload={
            "telegram_user_id": uid,
            "source_platform": str(lead_data.get("source_platform") or "unknown")[:40],
            "stage": "new",
            "lead_data": lead_data,
            "score": score or {},
        },
        prefer="return=representation",
    )
    return rows[0] if isinstance(rows, list) and rows else None


def load_recent_leads(telegram_user_id, limit=100):
    uid = _uid(telegram_user_id)
    if uid is None:
        return []
    rows = _request(
        "GET", "ramzes_content_engine_leads",
        params={
            "select": "id,created_at,source_platform,stage,lead_data,score",
            "telegram_user_id": f"eq.{uid}",
            "order": "created_at.desc",
            "limit": str(min(max(int(limit), 1), 500)),
        },
    )
    return rows if isinstance(rows, list) else []


def save_booking(telegram_user_id, booking_data):
    uid = _uid(telegram_user_id)
    if uid is None or not isinstance(booking_data, dict):
        return None
    rows = _request(
        "POST", "ramzes_content_engine_bookings",
        payload={
            "telegram_user_id": uid,
            "lead_id": booking_data.get("lead_id"),
            "session_date": booking_data["session_date"],
            "status": booking_data.get("status", "booked"),
            "amount": booking_data.get("amount"),
            "source_platform": str(booking_data.get("source_platform") or "unknown")[:40],
        },
        prefer="return=representation",
    )
    return rows[0] if isinstance(rows, list) and rows else None


def load_recent_bookings(telegram_user_id, limit=200):
    uid = _uid(telegram_user_id)
    if uid is None:
        return []
    rows = _request(
        "GET", "ramzes_content_engine_bookings",
        params={
            "select": "id,lead_id,created_at,session_date,status,amount,source_platform",
            "telegram_user_id": f"eq.{uid}",
            "order": "session_date.desc",
            "limit": str(min(max(int(limit), 1), 500)),
        },
    )
    return rows if isinstance(rows, list) else []


def save_publication(telegram_user_id, platform, topic, hook="", url="", content_type="post", published_at=None):
    uid = _uid(telegram_user_id)
    if uid is None or not str(topic or "").strip():
        return None
    normalized = re.sub(r"\s+", " ", f"{platform}|{topic}|{hook}|{url}").lower().strip()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    payload = {
        "telegram_user_id": uid,
        "platform": str(platform or "unknown")[:40],
        "topic": str(topic)[:1000],
        "hook": str(hook)[:500],
        "url": str(url)[:2000],
        "content_type": str(content_type or "post")[:60],
        "status": "published",
        "content_hash": digest,
    }
    if published_at:
        payload["published_at"] = published_at
    rows = _request(
        "POST", "ramzes_content_engine_publications",
        params={"on_conflict": "telegram_user_id,content_hash"},
        payload=payload,
        prefer="resolution=merge-duplicates,return=representation",
    )
    return rows[0] if isinstance(rows, list) and rows else None


def load_recent_publications(telegram_user_id, limit=100):
    uid = _uid(telegram_user_id)
    if uid is None:
        return []
    rows = _request(
        "GET", "ramzes_content_engine_publications",
        params={
            "select": "id,created_at,published_at,platform,content_type,topic,hook,url,status",
            "telegram_user_id": f"eq.{uid}",
            "order": "published_at.desc.nullslast",
            "limit": str(min(max(int(limit), 1), 500)),
        },
    )
    return rows if isinstance(rows, list) else []


def save_memory_event(telegram_user_id, memory_type, content, source="owner", confidence=1.0, confirmed=True, metadata=None):
    uid = _uid(telegram_user_id)
    allowed = {"brand_fact", "preference", "decision", "campaign", "learning", "workflow"}
    text_value = str(content or "").strip()
    if uid is None or memory_type not in allowed or not text_value:
        return False
    result = _request(
        "POST", "ramzes_content_engine_memory_events",
        payload={
            "telegram_user_id": uid,
            "memory_type": memory_type,
            "content": text_value[:4000],
            "source": str(source or "owner")[:80],
            "confidence": max(0.0, min(float(confidence), 1.0)),
            "confirmed": bool(confirmed),
            "metadata": metadata or {},
        },
        prefer="return=minimal",
    )
    return result is not None


def load_recent_memory_events(telegram_user_id, limit=60):
    uid = _uid(telegram_user_id)
    if uid is None:
        return []
    rows = _request(
        "GET", "ramzes_content_engine_memory_events",
        params={
            "select": "created_at,memory_type,content,source,confidence,confirmed",
            "telegram_user_id": f"eq.{uid}",
            "confirmed": "eq.true",
            "order": "created_at.desc",
            "limit": str(min(max(int(limit), 1), 200)),
        },
    )
    return rows if isinstance(rows, list) else []


def build_memory_events_context(items):
    if not items:
        return ""
    labels = {
        "brand_fact": "Факт бренда", "preference": "Предпочтение",
        "decision": "Решение", "campaign": "Кампания",
        "learning": "Вывод", "workflow": "Рабочий процесс",
    }
    lines = []
    for item in items[:60]:
        content = str(item.get("content") or "").strip()
        if content:
            lines.append(f"- [{labels.get(item.get('memory_type'), 'Память')}] {content[:500]}")
    return "\n\nДОЛГОСРОЧНАЯ ПАМЯТЬ RAMZES AI (подтверждённые записи):\n" + "\n".join(lines) if lines else ""

def save_agent_run(telegram_user_id, task_type, agent_ids, outputs, status="completed"):
    uid = _uid(telegram_user_id)
    if uid is None:
        return False
    # Store compact, bounded outputs; never store raw customer messages or credentials.
    safe_outputs = {}
    for key, value in (outputs or {}).items():
        safe_outputs[str(key)[:80]] = str(value)[:5000]
    result = _request(
        "POST", "ramzes_content_engine_agent_runs",
        payload={
            "telegram_user_id": uid,
            "task_type": str(task_type or "general")[:80],
            "agent_ids": list(agent_ids or [])[:40],
            "status": str(status or "completed")[:40],
            "outputs": safe_outputs,
        },
        prefer="return=minimal",
    )
    return result is not None


def save_market_sources(telegram_user_id, sources):
    uid = _uid(telegram_user_id)
    if uid is None:
        return 0
    saved = 0
    for item in (sources or [])[:100]:
        url = str(item.get("url") or item.get("source_url") or "").strip()
        if not url.startswith(("https://", "http://")):
            continue
        title = str(item.get("title") or "")[:400]
        excerpt = str(item.get("snippet") or item.get("excerpt") or "")[:1800]
        digest = hashlib.sha256((url + title + excerpt).encode("utf-8")).hexdigest()
        rows = _request(
            "POST", "ramzes_content_engine_market_sources",
            params={"on_conflict": "telegram_user_id,source_url"},
            payload={
                "telegram_user_id": uid, "source_url": url,
                "source_type": str(item.get("source_type") or "public_web")[:60],
                "title": title, "excerpt": excerpt,
                "published_at": str(item.get("published_at") or "")[:120],
                "content_hash": digest,
            },
            prefer="resolution=ignore-duplicates,return=minimal",
        )
        if rows is not None:
            saved += 1
    return saved


def load_recent_market_sources(telegram_user_id, limit=100):
    uid = _uid(telegram_user_id)
    if uid is None:
        return []
    rows = _request(
        "GET", "ramzes_content_engine_market_sources",
        params={
            "select": "created_at,source_url,source_type,title,excerpt,published_at,content_hash",
            "telegram_user_id": f"eq.{uid}",
            "order": "created_at.desc",
            "limit": str(min(max(int(limit), 1), 500)),
        },
    )
    return rows if isinstance(rows, list) else []
