# tg-bot-dad-ozon

Папа кидает ссылки на Ozon → сын заказывает со своей карты → бот считает, сколько папа должен вернуть.

- Папа: шлет ссылки, смотрит `/list`, `/debt` (read-only).
- Сын: кнопки `🛒 Заказать | ✏️ Цена | ✅ Забрал | ❌ Отмена | 💰 Предоплата/Постоплата`, команды `/debt /stats`.

Бот 24/7 на Fly.io free, БД — SQLite файл (с портом под Turso). MacBook — только разработка.

## Quickstart (локально)

```bash
cp .env.example .env   # BOT_TOKEN, DAD_ID, SON_ID, DATABASE_URL
uv sync
uv run alembic upgrade head
uv run python -m src.main
```

Токен: `@BotFather` → `/newbot`. ID пользователей: `@userinfobot`.

## Команды

| Команда | Кто | Что |
|---|---|---|
| `/start` | все из whitelist | привет + роль |
| `/list` | оба | последние 10 товаров, пагинация |
| `/debt` | оба | «Папа должен: X ₽ (N тов.), постоплата ждет: Y ₽» |
| `/stats` | сын | заказано/забрано/отменено/возвраты |

Кнопки статусов под карточкой — только сын. Папе на чужую кнопку — `alert`, в лог.

## Формула долга

```
долг = Σ price WHERE status IN (ORDERED, RECEIVED)
       AND payment = PREPAID AND status != CANCELLED
```

Отмена после предоплаты в долг не входит, видна в `/stats` как «вернулось».

## Структура

```
src/domain/         # entities, value objects, IItemRepository (pure)
src/use_cases/      # add_item, set_price, change_status, calc_debt
src/adapters/telegram/     # routers, keyboards, fsm
src/adapters/persistence/  # sqlalchemy models + SqliteItemRepository
src/infrastructure/ # config, db, logging
docs/specs/         # SPEC-00X на каждую фичу
```

Подробно: `docs/PLAN.md`, стиль: `AGENTS.md`.

## Deploy (Fly.io free, ~$0)

```bash
fly launch --no-deploy
fly volumes create data --size 1 --region ams
fly secrets set BOT_TOKEN=... DAD_ID=... SON_ID=...
fly deploy
fly logs
```

- БД: `/data/bot.db` (WAL), volume переживает рестарты.
- Бот — воркер long-polling, HTTP нет.
- Пропуски < 24ч Telegram отдает сам через `getUpdates` после рестарта.
- Бэкап: `fly ssh console -C "sqlite3 /data/bot.db .dump" > backup.sql`

Замена SQLite → Turso: реализовать `IItemRepository` на `libsql`, остальное не трогать.
