import os
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

import requests
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ramzes-content-engine")

app = Flask(__name__)
pool = ThreadPoolExecutor(max_workers=4)
memory = {}
memory_lock = threading.Lock()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OWNER_ID = os.getenv("TELEGRAM_OWNER_ID", "").strip()
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat").strip()
APP_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""
OR_API = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """Ты — RAMZES CONTENT ENGINE: персональный ИИ-маркетолог, стратег и редактор контента тату-мастера RAMZES.

БРЕНД:
- RAMZES — тату-мастер из Новосибирска, в сфере с 2019 года, более 1000 клиентов.
- Главный принцип: не копировать чужие татуировки, а создавать идею, композицию и решение, гармонирующее с телом человека.
- Направления: реализм, графика, акварель; уместны blackwork и black & grey.
- Визуальный характер: чёрный, графитовый, красный, фиолетовый.
- Аудитория: люди из Новосибирска и ближайших районов, которые выбирают тату-мастера, ценят индивидуальный подход, качество, безопасность и продуманную композицию.
- Цели: узнаваемость, доверие, входящие заявки и записи на сеансы.

ТВОЯ РОЛЬ:
Ты работаешь как полноценный контент-отдел: маркетолог, SMM-стратег, копирайтер, редактор, сценарист коротких видео и аналитик.

ПРАВИЛА:
1. Пиши естественно, уверенно, по-человечески, без канцелярита и шаблонных фраз.
2. Не повторяй одну и ту же идею, хук или структуру в пределах одного ответа.
3. Для Threads делай сильную первую строку: любопытство, контраст, спорное мнение, узнаваемая проблема или неожиданный вывод. Не обещай гарантированные охваты.
4. Учитывай локальные ключевые слова: тату Новосибирск, татуировка Новосибирск, тату мастер Новосибирск, реализм, графика и другие релевантные запросу.
5. Каждый продающий текст веди к конкретному следующему шагу: написать в личные сообщения, обсудить идею или записаться.
6. Не выдумывай отзывы, кейсы, цены, свободные даты, статистику, сертификаты и факты о клиенте. Если данных нет — спроси или оставь пометку.
7. Если просят тренды, не утверждай, что проверил актуальные тренды в интернете: у тебя нет live-браузинга. Давай гипотезы и темы для проверки.
8. Для Reels указывай: хук первых 1–2 секунд, кадры, текст/озвучку, монтаж, финальный CTA и подпись.
9. Для контент-плана указывай формат, тему, цель и CTA.
10. Не используй токсичное давление, унижение клиентов или медицинские обещания.
11. По умолчанию отвечай на русском.
12. Если пользователь просит несколько публикаций, делай их действительно разными по углу подачи, а не перефразируй одну мысль.

ФОРМАТ:
Сразу выдавай готовый материал. Не начинай с длинных вступлений. Структурируй ответ заголовками и нумерацией, когда это помогает.
"""

MENU = [
    [("🔥 Контент на сегодня", "daily"), ("📅 План на неделю", "week")],
    [("🧨 20 Threads", "threads"), ("🎬 Сценарии Reels", "reels")],
    [("🔎 Тренды и темы", "trends"), ("💰 Привлечение клиентов", "clients")],
    [("🧠 Стратегия RAMZES", "strategy"), ("📊 Анализ статистики", "analytics")],
    [("✍️ Рекламные публикации", "ads"), ("🎨 Идеи съёмок", "shoots")],
    [("♻️ Очистить контекст", "reset")],
]

ACTIONS = {
    "daily": "Составь контент на сегодня: 5 разных публикаций для Threads и одну идею короткого видео. Для каждой публикации дай сильный хук, готовый текст и цель. Не повторяй темы.",
    "week": "Составь подробный контент-план на 7 дней для RAMZES. Каждый день: 2 идеи Threads, одна идея Stories и через день идея Reels. Укажи формат, тему, цель, хук и CTA. Чередуй охват, доверие, экспертность и продажи.",
    "threads": "Создай 20 оригинальных Threads для привлечения клиентов на татуировки в Новосибирске. Разные углы подачи: провокационные мнения, юмор, экспертность, ошибки выбора мастера, композиция, истории процесса, доверие и мягкие продажи. Каждый пост готов к публикации, с сильной первой строкой и уместным CTA. Не повторяй идеи.",
    "reels": "Создай 5 сильных сценариев Reels для тату-мастера RAMZES. Для каждого: хук 1–2 секунды, покадровый план, текст на экране/озвучка, монтаж, финальный CTA и подпись.",
    "trends": "Предложи 15 перспективных тем и контент-гипотез для Threads и Reels тату-мастера в Новосибирске. Раздели на: дискуссионные, полезные, развлекательные, локальные и продающие. Не выдавай их за проверенные текущие тренды — пометь как идеи для тестирования.",
    "clients": "Разработай практическую систему привлечения новых клиентов на татуировки в Новосибирске: контент, локальные ключевые слова, доверие, офферы без выдуманных скидок, CTA и путь от просмотра до записи. Дай конкретные действия на ближайшие 7 дней.",
    "strategy": "Проведи стратегическую сессию по продвижению RAMZES: позиционирование, целевая аудитория, отличия от конкурентов, контентные рубрики, воронка, доверие, локальное продвижение и KPI. Отделяй известные факты от гипотез.",
    "analytics": "Помоги проанализировать статистику Threads/Instagram/VK. Попроси прислать цифры, если их нет. Скажи, какие метрики нужны, и после получения данных найди сильные публикации, слабые места и следующие тесты. Не придумывай показатели.",
    "ads": "Подготовь 5 разных рекламных публикаций для RAMZES, чтобы привлечь клиентов из Новосибирска. Не выдумывай цены и свободные даты. Используй разные мотивы: индивидуальная идея, композиция на теле, качество процесса, стиль и запись на консультацию.",
    "shoots": "Предложи 20 идей фото- и видеосъёмок для тату-мастера RAMZES: готовые работы, процесс, эскизы, детали, рабочее место, экспертность и личный бренд. Для каждой идеи укажи кадр и короткий сценарий."
}


def tg(method, payload=None):
    if not TG_API:
        raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN")
    response = requests.post(f"{TG_API}/{method}", json=payload or {}, timeout=25)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(str(data))
    return data.get("result")


def send_text(chat_id, text):
    text = str(text or "").strip()
    if not text:
        text = "Не удалось получить ответ. Попробуй ещё раз."
    # Telegram message limit is 4096 characters; leave a margin.
    while text:
        part = text[:3900]
        if len(text) > 3900:
            split_at = part.rfind("\n")
            if split_at > 1800:
                part = part[:split_at]
        tg("sendMessage", {"chat_id": chat_id, "text": part, "disable_web_page_preview": True})
        text = text[len(part):].lstrip()


def menu_markup():
    return {
        "keyboard": [[{"text": label} for label, _ in row] for row in MENU],
        "resize_keyboard": True,
        "is_persistent": True
    }


def send_menu(chat_id):
    send_text(chat_id, "🔥 RAMZES CONTENT ENGINE\n\nТвой отдельный ИИ-маркетолог. Выбери задачу или напиши запрос своими словами.",)
    tg("sendMessage", {"chat_id": chat_id, "text": "Выбери действие:", "reply_markup": menu_markup()})


def remember(chat_id, role, content):
    with memory_lock:
        history = memory.setdefault(str(chat_id), [])
        history.append({"role": role, "content": content})
        memory[str(chat_id)] = history[-14:]


def ask_ai(chat_id, user_text):
    if not OPENROUTER_API_KEY:
        send_text(chat_id, "Не настроен OPENROUTER_API_KEY на хостинге. Добавь его в переменные окружения сервиса.")
        return
    with memory_lock:
        history = list(memory.get(str(chat_id), []))
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": user_text}]
    try:
        response = requests.post(
            OR_API,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": APP_URL or "https://ramzes-content-engine.onrender.com",
                "X-Title": "RAMZES CONTENT ENGINE"
            },
            json={"model": MODEL, "messages": messages, "temperature": 0.85, "max_tokens": 3500},
            timeout=90
        )
        response.raise_for_status()
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        remember(chat_id, "user", user_text)
        remember(chat_id, "assistant", answer)
        send_text(chat_id, answer)
    except Exception as exc:
        log.exception("AI request failed")
        send_text(chat_id, f"Не получилось получить ответ от ИИ. Проверь API-ключ, баланс OpenRouter и модель.\nТехническая ошибка: {str(exc)[:350]}")


def allowed(user_id):
    return not OWNER_ID or str(user_id) == OWNER_ID


def process_update(update):
    try:
        if "callback_query" in update:
            query = update["callback_query"]
            user_id = query.get("from", {}).get("id")
            chat_id = query.get("message", {}).get("chat", {}).get("id")
            action = query.get("data", "")
            tg("answerCallbackQuery", {"callback_query_id": query["id"]})
            if not allowed(user_id):
                send_text(chat_id, "Этот бот закрыт для личного использования.")
                return
            if action == "reset":
                with memory_lock:
                    memory.pop(str(chat_id), None)
                send_text(chat_id, "Контекст текущего диалога очищен.")
                return
            if action in ACTIONS:
                send_text(chat_id, "Готовлю материал. Это может занять немного времени…")
                ask_ai(chat_id, ACTIONS[action])
            return

        message = update.get("message") or update.get("edited_message")
        if not message:
            return
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        text = (message.get("text") or "").strip()
        if not text:
            if message.get("photo"):
                send_text(chat_id, "Пока я принимаю текстовые запросы. Опиши статистику или задачу сообщением.")
            return

        if not allowed(user_id):
            send_text(chat_id, "Этот бот закрыт для личного использования.")
            return

        if text.startswith("/start"):
            if not OWNER_ID:
                send_text(chat_id, f"Твой Telegram ID: {user_id}\n\nДобавь это число в переменную TELEGRAM_OWNER_ID на хостинге, затем перезапусти сервис и отправь /start ещё раз.")
            else:
                send_menu(chat_id)
            return
        if text.startswith("/menu"):
            send_menu(chat_id)
            return
        if text.startswith("/reset"):
            with memory_lock:
                memory.pop(str(chat_id), None)
            send_text(chat_id, "Контекст очищен. Начинаем с чистого листа.")
            return
        if not OWNER_ID:
            send_text(chat_id, "Сначала настрой доступ владельца: отправь /start и добавь свой Telegram ID в TELEGRAM_OWNER_ID на хостинге.")
            return

        labels = {label: key for row in MENU for label, key in row}
        if text in labels:
            action = labels[text]
            if action == "reset":
                with memory_lock:
                    memory.pop(str(chat_id), None)
                send_text(chat_id, "Контекст текущего диалога очищен.")
            else:
                send_text(chat_id, "Готовлю материал. Это может занять немного времени…")
                ask_ai(chat_id, ACTIONS[action])
            return

        send_text(chat_id, "Принял задачу. Готовлю ответ…")
        ask_ai(chat_id, text)
    except Exception:
        log.exception("Update processing failed")


@app.get("/")
def health():
    return jsonify({"ok": True, "service": "RAMZES CONTENT ENGINE", "mode": "temporary"})


@app.post("/telegram")
def telegram_webhook():
    if WEBHOOK_SECRET:
        supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if supplied != WEBHOOK_SECRET:
            return jsonify({"ok": False}), 403
    update = request.get_json(silent=True) or {}
    pool.submit(process_update, update)
    return jsonify({"ok": True})


def configure_webhook():
    if not BOT_TOKEN or not APP_URL or not WEBHOOK_SECRET:
        log.warning("Webhook not configured: set TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET and deploy URL.")
        return
    try:
        result = tg("setWebhook", {
            "url": f"{APP_URL}/telegram",
            "secret_token": WEBHOOK_SECRET,
            "allowed_updates": ["message", "callback_query"],
            "drop_pending_updates": False
        })
        log.info("Telegram webhook configured: %s", result)
    except Exception:
        log.exception("Could not configure Telegram webhook")


if __name__ == "__main__":
    configure_webhook()
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
else:
    # Render imports the module through gunicorn; configure webhook after import.
    configure_webhook()
