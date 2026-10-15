# dolzhok

Заказчик и исполнитель кидают ссылки на Ozon → исполнитель заказывает со своей карты → бот считает, сколько заказчик должен вернуть.

- Заказчик и исполнитель: оба шлют ссылки, смотрят `/list`, `/debt`.
- Исполнитель: кнопки `1 Новое | 2 Заказан | 3 Получен | 🚫 Отмена | ✏️ Цена | 🔢 Кол-во` (+ у закрытых/отменённых — `↩️ В работу`), команды `/debt /stats /pay /payments`.
- Кнопки меню: `📋 Список`, `💰 Долги`, `📊 Статистика`, `❌ Отмена` (+ команды `/menu`, `/cancel`). `💰 Долги` сразу показывает сводку долга и подменю действий: `💰 Долг`, `📜 Погашения` и (у исполнителя) `💸 Погасить`, `⬅️ Назад`.
- Погашения: исполнитель вносит `💸 Погасить` (сумма + опц. комментарий), долг уменьшается, лента — в `📜 Погашения` (удаление ошибочной записи с подтверждением).

Бот 24/7 на Fly.io free, БД — SQLite файл (с портом под Turso). MacBook — только разработка.

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
src/adapters/persistence/  # sqlalchemy models + SqliteItem/RepaymentRepository
src/infrastructure/ # config, db, logging
docs/specs/         # SPEC-00X на каждую фичу
```

Подробно: `docs/PLAN.md`, стиль: `AGENTS.md`.

## Deploy (Fly.io free, ~$0)

Один always-on воркер, SQLite на volume `/data`. HTTP-порта нет (long polling).

### Первичная настройка

```bash
make fly-init        # fly launch --no-deploy + volume data 1GB (ams)
fly secrets set BOT_TOKEN=... CUSTOMER_ID=... EXECUTOR_ID=...
make deploy          # fly deploy
make logs            # проверить, что миграции применились и бот опросил Telegram
```

- `fly launch --no-deploy` берёт готовые `Dockerfile` + `fly.toml` (регион `ams`,
  volume `data` → `/data`, `DATABASE_URL=sqlite+aiosqlite:////data/bot.db`).
- Секреты (`BOT_TOKEN`, `CUSTOMER_ID`, `EXECUTOR_ID`) — только через `fly secrets set`,
  в образ не попадают (`.dockerignore` исключает `.env`).
- На каждом старте контейнер выполняет `alembic upgrade head` против
  `DATABASE_URL` (`docker-entrypoint.sh`), затем `python -m src.main`.

### Runbook

| Задача | Команда |
|---|---|
| Логи в реальном времени | `make logs` (`fly logs`) |
| Статус машины | `fly status` |
| SSH на машину | `fly ssh console` |
| Бэкап БД (dated dump) | `make backup` → `backup-YYYY-MM-DD.sql` |
| Восстановление | `make restore FILE=backup-YYYY-MM-DD.sql` |
| Ручной рестарт | `make restart` (`fly machines restart`) |
| Обновление кода | `make deploy` (тот же volume, БД на месте) |

- **Догон после рестарта.** `long polling` + `drop_pending_updates=False`:
  Telegram хранит неподтверждённые апдейты < 24ч, бот забирает их после
  пробуждения. Пропуски > 24ч теряются по дизайну Telegram API.
- **Миграции.** Схема применяется автоматически на старте. Если volume заведён
  до P4 (таблицы созданы через `create_all`, без `alembic_version`) — один раз
  проставь версию: `fly ssh console -C "uv run alembic stamp head"`.
- **Восстановление.** `make restore` сначала удаляет текущий `/data/bot.db*`
  (`.dump` не содержит `DROP TABLE`), заливает бэкап в пустую БД и перезапускает
  машину. Делай это в простое: до перезапуска бот пишет в старый (удалённый) файл.
- **Бэкап перед деплоем** со сменой схемы: `make backup`, затем `make deploy`.
- Alembic читает `DATABASE_URL` из окружения; локально он совпадает с `.env` по
  умолчанию, но если меняешь путь в `.env` — экспортируй его и для `make migrate`.

Замена SQLite → Turso: реализовать `IItemRepository` на `libsql`, остальное не трогать.
