"""One-shot daily owner report for GitHub Actions or a trusted server."""
import os
from datetime import datetime, timedelta, timezone
import requests

from analytics_engine import render_daily_report

BASE = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OWNER_ID = os.getenv("TELEGRAM_OWNER_ID", "").strip()


def _get(table, select, since):
    response = requests.get(
        f"{BASE}/rest/v1/{table}",
        params={"select": select, "telegram_user_id": f"eq.{OWNER_ID}",
                "created_at": f"gte.{since}", "order": "created_at.desc", "limit": "500"},
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def send_report(text):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": OWNER_ID, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError("Telegram rejected daily report")


def main():
    missing = [name for name, value in (
        ("SUPABASE_URL", BASE), ("SUPABASE_SERVICE_ROLE_KEY", KEY),
        ("TELEGRAM_BOT_TOKEN", BOT_TOKEN), ("TELEGRAM_OWNER_ID", OWNER_ID)
    ) if not value]
    if missing:
        raise SystemExit("Missing required GitHub Actions secrets/variables: " + ", ".join(missing))
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    metrics = _get("ramzes_content_engine_metrics",
                   "platform,views,likes,comments,reposts,saves,profile_visits,followers_gained,inbound_messages,bookings,ad_spend,captured_at", since)
    leads = _get("ramzes_content_engine_leads", "stage,created_at,lead_data", since)
    bookings = _get("ramzes_content_engine_bookings", "status,amount,created_at,session_date", since)
    market = _get("ramzes_content_engine_market_sources", "id,created_at", since)
    send_report(render_daily_report(metrics, leads, bookings, len(market)))


if __name__ == "__main__":
    main()
