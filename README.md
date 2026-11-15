# RAMZES CONTENT ENGINE

В репозитории добавлена отдельная временная версия Telegram-бота **@RamzesContentEngineBot**. Она разворачивается как самостоятельный сервис Render и не использует Supabase или инфраструктуру Tattoo Manager.

## Развернуть временного бота

Открой ссылку на телефоне:

**[Развернуть RAMZES CONTENT ENGINE на Render](https://dashboard.render.com/blueprint/new?repo=https://github.com/inkpeople/RamzesTattoo-SMM)**

В Render нужно:
1. Войти или зарегистрироваться.
2. Подключить GitHub и разрешить доступ к репозиторию `inkpeople/RamzesTattoo-SMM`.
3. Проверить Blueprint `ramzes-content-engine`.
4. Добавить секретные переменные:
   - `TELEGRAM_BOT_TOKEN` — токен только бота @RamzesContentEngineBot (получить у @BotFather).
   - `OPENROUTER_API_KEY` — личный API-ключ OpenRouter.
5. Нажать Apply / Deploy.

Переменная `TELEGRAM_WEBHOOK_SECRET` генерируется автоматически. После первого запуска открыть @RamzesContentEngineBot и отправить `/start`. Бот покажет Telegram ID. Добавить это число в `TELEGRAM_OWNER_ID` в настройках сервиса Render и выполнить Manual Deploy / Restart.

**Не вставляй токены в GitHub и не отправляй их в чат.** Вводи их только в Environment Variables сервиса Render.

## Временные ограничения

Бесплатный Render Web Service засыпает после 15 минут без входящего трафика; первый запрос после сна может ждать около минуты. Файловая система бесплатного сервиса временная. История диалога текущей версии хранится в оперативной памяти и сбрасывается при перезапуске. Это тестовая версия до переноса на полноценный сервер после 6 декабря 2026 года.

Документация Render: https://render.com/docs/free
