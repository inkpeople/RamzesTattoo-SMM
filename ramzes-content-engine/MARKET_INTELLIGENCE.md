# RAMZES AI Market Intelligence

## Purpose
An independent background worker monitors publicly indexed advertising and social content related to tattoo services, focused on Novosibirsk. It scans hourly and sends a Telegram digest every six hours. Seen URLs and generated recommendations are stored in SQLite on a persistent Render disk.

## Sources and limitations
- With BRAVE_SEARCH_API_KEY, the worker searches public web results for local tattoo ads, Threads pages, social posts and ad-library pages.
- Without that key, it falls back to Google News RSS. This fallback is much narrower and may not index social posts or ads.
- It does not log into competitors' accounts, bypass access controls, or scrape private profiles.
- Public reach/view counts are reported only when a source explicitly exposes them. Likes/comments/reposts are engagement signals, not reach.
- Direct Threads and Meta Ad Library API access is not assumed; platform permissions and supported endpoints must be verified before adding those connectors.

## Render setup
The render.yaml worker is a separate always-on service with a persistent disk. It uses the existing Telegram bot token to send private reports and OpenRouter for analysis. Add BRAVE_SEARCH_API_KEY for broader public-web search. It does not register or replace the Telegram webhook.

The Render worker plan and persistent disk are paid infrastructure. Review Render's price before creating the service. Do not deploy this worker inside the existing webhook web-service process.

## Default cadence
- Scan public search sources every 60 minutes.
- Send digests every 6 hours.
- Retain source URLs for 45 days, reports for 90 days, and generated draft history for 180 days.
- Deduplicate exact source URLs and report hashes; provide previous recommendations to the AI to reduce repeated topics and hooks.

## Required environment
TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_ID, OPENROUTER_API_KEY. BRAVE_SEARCH_API_KEY is strongly recommended. Optional: MARKET_MONITOR_LOCATION, MARKET_MONITOR_INTERVAL_SECONDS, MARKET_REPORT_INTERVAL_HOURS, MARKET_DB_PATH, OPENROUTER_MODEL.
