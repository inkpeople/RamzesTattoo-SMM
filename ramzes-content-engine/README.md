# RAMZES CONTENT ENGINE — RAMZES AI

Отдельный Telegram-бот для личного контент-маркетинга RAMZES. Работает отдельно от Tattoo Manager.

## Возможности
- Генерация Threads, Reels, контент-планов, рекламных публикаций.
- Маркетинговые идеи для привлечения клиентов в Новосибирске.
- Постоянная память диалога, профиля бренда, библиотеки контента и метрик через Supabase (после настройки хранилища).
- Доступ по Telegram ID владельца.
- Telegram webhook + OpenRouter.

## Развёртывание
Проект рассчитан на Render Web Service. Выбрать этот репозиторий, указать Root Directory `ramzes-content-engine`, Runtime Python, Build Command `pip install -r requirements.txt`, Start Command `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`.

Переменные окружения:
- `TELEGRAM_BOT_TOKEN` — токен только для @RamzesContentEngineBot.
- `TELEGRAM_WEBHOOK_SECRET` — случайный секрет для проверки Telegram webhook.
- `TELEGRAM_OWNER_ID` — Telegram ID владельца.
- `OPENROUTER_API_KEY` — API-ключ OpenRouter.
- `OPENROUTER_MODEL` — модель OpenRouter (необязательно).

После первого развёртывания временно оставить `TELEGRAM_OWNER_ID` пустым, открыть бота и отправить /start. Бот покажет ID. Внести ID в переменную `TELEGRAM_OWNER_ID` и перезапустить сервис.

## Настройка новой Supabase

1. Создать отдельный проект в организации RAMZES AI.
2. Открыть SQL Editor и выполнить миграцию `supabase/migrations/202611160001_initial_ramzes_content_engine.sql`.
3. В Render добавить `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `RAMZES_STORAGE_ENABLED=true` и `RAMZES_ENGINE_STORAGE_SECRET`.
4. Проверить корневой health endpoint: `persistent_storage_configured` должен стать `true`.
5. Проверить запись/чтение истории, профиля, библиотеки и метрик тестовым Telegram-аккаунтом до переключения рабочего webhook.

Миграция включает четыре таблицы с RLS. Политики для `anon` и `authenticated` не создаются: доступ к данным предназначен только для доверенного серверного процесса через service-role key. Service-role key обладает повышенными правами и не должен попадать в клиентские приложения.

## Примечания по эксплуатации
- На бесплатном тарифе Render сервис может засыпать после простоя; первый ответ после пробуждения может задержаться.
- Пока Supabase не настроена или `RAMZES_STORAGE_ENABLED` выключен, данные остаются только в памяти процесса и теряются при перезапуске.
- Постоянное хранение считается готовым только после успешной проверки `persistent_storage_configured: true` и фактического теста чтения/записи.
- Для production укажи `TELEGRAM_OWNER_ID` и `TELEGRAM_WEBHOOK_SECRET`. Без owner ID функции бота закрыты; без webhook secret endpoint не принимает обновления.

Не добавлять токены или API-ключи в GitHub. Все секреты задаются только в настройках хостинга.
