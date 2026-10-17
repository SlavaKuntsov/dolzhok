# dolzhok

Заказчик и исполнитель кидают ссылки на Ozon → исполнитель заказывает со своей карты → бот считает, сколько заказчик должен вернуть.

- Заказчик и исполнитель: оба шлют ссылки, смотрят `/list`, `/debt`.
- Исполнитель: кнопки `1 Новое | 2 Заказан | 3 Получен | 🚫 Отмена | ✏️ Цена | 🔢 Кол-во` (+ у закрытых/отменённых — `↩️ В работу`), команды `/debt /stats /pay /payments`.
- Кнопки меню: `📋 Список`, `💰 Долги`, `📊 Статистика`, `❌ Отмена` (+ команды `/menu`, `/cancel`). `💰 Долги` сразу показывает сводку долга и подменю действий: `💰 Долг`, `📜 Погашения` и (у исполнителя) `💸 Погасить`, `⬅️ Назад`.
- Погашения: исполнитель вносит `💸 Погасить` (сумма + опц. комментарий), долг уменьшается, лента — в `📜 Погашения` (удаление ошибочной записи с подтверждением).

Бот 24/7 на Vercel (webhook, FastAPI ASGI) + Neon Postgres. Локально — long polling и SQLite файл. MacBook — только разработка.

## Quickstart (локально)

```bash
cp .env.example .env   # BOT_TOKEN, CUSTOMER_ID, EXECUTOR_ID, DATABASE_URL
uv sync
uv run alembic upgrade head
uv run python -m src.main
```

Токен: `@BotFather` → `/newbot`. ID пользователей: `@userinfobot`.

## Команды

| Команда | Кто | Что |
|---|---|---|
| `/start` | все из whitelist | привет + роль |
| `/list` | оба | карточки последних 10 (у исполнителя — с кнопками управления) |
| `/debt` | оба | «Заказчик должен: X BYN» + «Погашено»/«Остаток» (и «Аванс» при переплате) + постоплата |
| `/stats` | оба | заказано/получено/отменено/возвраты |
| `/pay` | исполнитель | внести погашение (FSM: сумма → опц. комментарий) |
| `/payments` | оба | лента погашений (у исполнителя — 🗑 с подтверждением) |

Инлайн-кнопки под карточкой — только у исполнителя (у заказчика карточка без кнопок). Чужие апдейты вне whitelist игнорятся без ответа. Для `Заказан` исполнитель переключает оплату одной кнопкой (`💳 Сменить на предоплату/постоплату`); по умолчанию — предоплата. У `Получен`/`Отменён` есть `↩️ В работу` (возврат в `Заказан`).

## Формула долга

```
долг       = Σ (price × qty) WHERE status IN (ORDERED, RECEIVED) AND payment = PREPAID
постоплата = Σ (price × qty) WHERE status = ORDERED AND payment = POSTPAID
погашено   = Σ repayment.amount_kop
остаток    = долг − погашено         # < 0 → «аванс» (переплата)
```

Отмена после предоплаты в долг не входит, видна в `/stats` как «возвраты».
Погашения — отдельный счёт наличных (пул), отмены их не корректируют автоматически.

## Структура

```
src/domain/         # entities, value objects, IItemRepository/IRepaymentRepository (pure)
src/use_cases/      # add_item, set_price, set_payment, change_status, calc_debt, calc_stats, add/list/delete_repayment, calc_balance
src/adapters/telegram/     # routers, keyboards, fsm
src/adapters/persistence/  # sqlalchemy models + SqlAlchemyItem/RepaymentRepository (SQLite + Postgres)
src/adapters/webhook/      # FastAPI ASGI app (Vercel) + set/delete webhook CLI
src/infrastructure/ # config, db, bootstrap (shared wiring), logging
asgi.py             # Vercel entrypoint -> src.adapters.webhook.app:app
docs/adr/           # ADR: зафиксированные решения
docs/agents/        # настройка скиллов (issue-tracker, triage-labels, domain)
```

Язык — `GLOSSARY.md`; решения — `docs/adr/`; спеки и тикеты — GitHub Issues; стиль — `AGENTS.md`.

## Deploy (Vercel serverless + Neon Postgres, ~$0)

Прод — Telegram **webhook** (FastAPI ASGI-функция на Vercel Hobby) + **Neon
Postgres** (`asyncpg`). Локально — long polling и SQLite. Решение и отклонённый
Fly.io — `docs/adr/0001-vercel-neon-webhook-over-fly.md`.

`vercel.json` + `asgi.py` (`[tool.vercel] entrypoint` в `pyproject.toml`)
задают ASGI-энтрипоинт; зависимости Vercel ставит из `pyproject.toml`/`uv.lock`.

### Первичная настройка (руками, один раз)

1. **Neon**: создать проект/базу, скопировать connection string в `DATABASE_URL`
   (можно как есть, `postgresql://…` — драйвер поднимется до `asyncpg`, а
   `sslmode`/`channel_binding` нормализуются в коде).
2. **Миграции на Neon** (с локальной машины). `make migrate` читает `DATABASE_URL`
   из окружения **или `.env`**. Для миграций бери **direct** (`ep-…`, без
   `-pooler`) хост: пулер в transaction-mode ломает DDL.
   ```bash
   make migrate   # DATABASE_URL уже в .env, либо: DATABASE_URL='postgresql://…' make migrate
   ```
3. **Vercel**: импортировать репозиторий, задать env (Production):
   `BOT_TOKEN`, `CUSTOMER_ID`, `EXECUTOR_ID`, `DATABASE_URL`,
   `WEBHOOK_BASE_URL=https://<app>.vercel.app`, `WEBHOOK_SECRET=<random string>`.
4. **Deploy + webhook**: `make deploy` — это `vercel deploy --prod` + `make webhook-set`
   (`setWebhook` с секретом). Только код, без вебхука: `make vercel-deploy`.
5. **Smoke**: написать боту `/start` — должен ответить.

### Обновление

```bash
make migrate   # если менялась схема (DATABASE_URL из .env)
make deploy
```

### Runbook

| Задача | Команда |
|---|---|
| Deploy + webhook | `make deploy` |
| Только deploy кода | `make vercel-deploy` |
| Статус webhook | `make webhook-info` |
| Снять webhook (вернуться к polling) | `make webhook-delete` |
| Регистрация webhook | `make webhook-set` |
| Миграции Neon | `make migrate` (читает `DATABASE_URL` из `.env`) |

- **Почему webhook.** Telegram сам повторяет недоставленные апдейты с backoff и
  будит функцию на каждый запрос — не нужен always-on воркер (ADR-0001).
- **Апдейты вне функции.** `WEBHOOK_SECRET` проверяется по заголовку
  `X-Telegram-Bot-Api-Secret-Token`; чужие запросы получают `403`. Без секрета
  endpoint открыт — в проде секрет обязателен (app пишет warning при старте).
- **Схема — только Alembic (на обоих диалектах).** `init_db` таблиц не создаёт
  (только `PRAGMA journal_mode=WAL` для SQLite); если миграции не прогнаны,
  старт падает с подсказкой `make migrate`. Иначе таблицы появились бы без
  `alembic_version` и первый `upgrade head` упал бы на `CREATE TABLE`.
- **Соединения на serverless.** Для Postgres клиентский пул отключён
  (`NullPool`): пулинг делает Neon-пулер. Иначе замороженный инстанс Vercel
  отдаёт соединение, которое Neon уже закрыл (`InterfaceError: connection is closed`).
- **Дрейф диалектов.** `make test-pg TEST_DATABASE_URL='postgresql://…'` гоняет
  миграции и repo-раундтрип на Postgres (опционально, нужна отдельная БД).
  Без `TEST_DATABASE_URL` тест скипается, поэтому в `make check` его нет.
  `make test-pg-reset` — destructive-проверка sequence в `0003` (только на
  scratch-БД: откатывает схему до `0002` и обратно).
- **Известное ограничение (FSM).** Диспатчер использует `MemoryStorage`: на
  serverless состояние FSM живёт в конкретном инстансе и теряется при cold start,
  поэтому многошаговые флоу (`/pay`) могут сброситься между апдейтами. Нужен
  персистентный storage (follow-up тикет); пока — риск митигируется тёплым
  инстансом.

### Fly.io — отклонён

Fly.io больше не прод-путь (платный always-on, OOM на 256 МБ — ADR-0001).
`Dockerfile`, `fly.toml` и `make *-fly`/`fly-*` оставлены как опциональный
не-прод фолбэк; `make fly-init`/`make deploy-fly` — только если очень нужно.
Удаление старого приложения: `fly apps destroy dolzhok`.

