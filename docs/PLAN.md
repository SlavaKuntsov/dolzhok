# PLAN — dolzhok

> Связь «заказчик ↔ исполнитель» для заказов с Ozon: оба присылают ссылки, исполнитель заказывает
> со своей карты, бот считает, сколько заказчик должен вернуть.

## 1. Decisions (зафиксировано с владельцем проекта)

| Вопрос | Решение |
|---|---|
| Хостинг | **Vercel** (serverless, **webhook**), план Hobby — $0, non-commercial |
| БД | **Neon Postgres** (`asyncpg`) в проде; локально/интеграционные тесты — SQLite (`aiosqlite`) |
| Цена товара | Ручной ввод (автопарсинг Ozon ненадежен: JS/капча) |
| Роли | Заказчик и исполнитель оба шлют ссылки; статусы/цены меняет только исполнитель |
| Погашение долга | Исполнитель вносит платёж (сумма + комментарий) → долг уменьшается; история погашений хранится |

**Отклонено:** Fly.io — у новых организаций нет free-tier, always-on машина ≈
$3.9/мес, а 256 МБ уходит в OOM (импорт aiogram+pydantic+sqlalchemy ≈ 196 МБ) →
нужно 512 МБ. Turso — `sqlalchemy-libsql` **без async-движка**, переписывать
репозиторий. Oracle/GCP/AWS — карты и гео-ограничения (РБ).

**Следствие про доставку апдейтов:** прод-бот работает через **webhook** (long
polling только как локальный fallback): Telegram шлёт POST на Vercel-URL, каждый
апдейт = вызов serverless-функции. Состояния живут в БД, «офлайн-режим простановки
статусов» не нужен. Функция просыпается на запрос, поэтому простой закрывается почти
мгновенно; недоставленные апдейты Telegram ретраит с backoff.

## 2. Goal / Non-goals

**Goal (MVP):**
- Принять Ozon-ссылку от заказчика, показать исполнителю карточку с кнопками.
- Статусы: `NEW → ORDERED → RECEIVED | CANCELLED` (переходы свободные).
- Оплата: `PREPAID` (оплатил сразу, **по умолчанию**) / `POSTPAID` (постоплата);
  переключается одной кнопкой-тогглом на карточке.
- Команда `/debt`: сколько заказчик должен (предоплаченное, но не отмененное).
- Погашение: исполнитель вносит платёж, долг уменьшается; история погашений видна.

**Non-goals (пока нет):**
- Автопарсинг цены/названия с Ozon (только ручной ввод + fallback).
- Ozon API, корзина, авто-заказ.
- Мульти-тенантность (несколько независимых пар), платежи внутри бота, Mini App.

## 3. Ubiquitous Language

- `Item` — одна ссылка/товар. Агрегат.
- `status` — `NEW | ORDERED | RECEIVED | CANCELLED`, переходы свободные
  (любой → любой, кроме того же). Повторные ссылки — отдельные товары, дедупа нет.
- `payment` — `PREPAID | POSTPAID`, по умолчанию `PREPAID`; исполнитель переключает
  одной кнопкой на карточке (показывает противоположный способ).
- `price_kop` — цена в копейках, `int | None` до ручного ввода.
- `debt` — **вычисляемое**, не хранится:
  `Σ price WHERE status IN (ORDERED, RECEIVED) AND payment=PREPAID AND NOT cancelled`.
- `Repayment` — платёж от заказчика исполнителю (погашение долга). Хранится: `amount_kop` (>0),
  опциональный комментарий, автор (исполнитель), дата. Агрегат.
- `balance` — **вычисляемый**: `debt − Σ repayments`. Может быть отрицательным
  (переплата/аванс) — показывается отдельно.

## 4. Stack

- Python **3.14** + `uv` (lock, sync, run).
- `aiogram 3.x` (`>=3,<4`) — async, routers, FSM; доставка через **webhook**
  (ASGI-приложение на FastAPI) на Vercel.
- `SQLAlchemy 2.0 async` + `asyncpg` (прод, Neon Postgres) / `aiosqlite` (локально,
  интеграционные тесты) + `Alembic`. Репозиторий диалект-агностичен.
- `pydantic-settings` — `BOT_TOKEN`, `CUSTOMER_ID`, `EXECUTOR_ID`, `DATABASE_URL`.
- **Vercel** (Hobby, Python Function) + **Neon Postgres** (Vercel Marketplace, $0).
- Опционально: `Dockerfile` + `fly.toml` + volume `/data` (SPEC-004) — оставлены как
  альтернативный деплой, но **не прод**.
- Тесты: `pytest`, `pytest-asyncio`.

## 5. Architecture (Clean / Hexagonal)

```
src/
  domain/          # pure: entities, value objects, ports. НЕТ aiogram/SQLAlchemy
  use_cases/       # только domain + порты (IItemRepository)
  adapters/
    persistence/   # ORM models, репозиторий на SQLAlchemy (SQLite локально / Postgres в проде)
    telegram/      # routers, keyboards, filters, FSM + webhook entrypoint (ASGI)
  infrastructure/  # config, db engine/session, logging
```

Правила:
- `use_cases` импортируют только `domain`.
- Границы пересекаются через интерфейсы (`IItemRepository`).
- Каждый use-case покрыт unit-тестом с `InMemoryItemRepository`.
- Деньги — `int` копейки + `Money` VO, валидация в `__post_init__`.

## 6. Phases

### P0 — Bootstrap (этот коммит)
- [x] `pyproject`, `.python-version`, `.env.example`, `.gitignore`
- [x] Скелет `src/`, `AGENTS.md`, `README.md`, `docs/PLAN.md`
- [x] `Dockerfile`, `fly.toml`, `alembic.ini` placeholder
- [x] `uv sync` зеленый, `pytest -q` зеленый (пустой)

### P1 — MVP прием ссылок (SPEC-001) ✅ done
- [x] `add_item`: regex Ozon (`ozon.ru`, `ozo.ru` + HEAD-redirect для коротких),
  дедуплика по нормализованному URL/SKU.
- [x] Карточка `#id NEW` заказчику (подтверждение) + исполнителю (кнопки).
- [x] Whitelist: отвечать только `CUSTOMER_ID`, `EXECUTOR_ID`, остальных игнорить + лог.
- [x] FSM «ввод цены»: исполнитель жмет `✏️ Цена` → бот ждет число → `set_price`.
- [x] Фильтры ролей: кнопки статусов — только исполнитель (callback answer + alert).
- [x] Плюс: `change_status` с машиной переходов, `/list`, `/start`, `/cancel`,
  `SqliteItemRepository` + alembic `0001`, `HttpxOzonResolver`.

### P2 — Деньги и статусы (SPEC-002) ✅ done
- [x] Статусы: свободные переходы, повтор в тот же статус = ошибка (не молчание).
- [x] `payment` (`PREPAID | POSTPAID`, по умолчанию `PREPAID`) одной кнопкой-тогглом на карточке `ORDERED`.
- [x] `CalcDebtUseCase` + `/debt`: «Заказчик должен» (предоплата) и «Ждет постоплаты».
- [x] `CalcStatsUseCase` + `/stats`: счётчики по статусам + возвраты.
- [x] `CANCELLED` после `PREPAID` = «вернулось», в долг не входит (видно в `/stats`).
- [x] Долг/статистика — вычисляемые из `IItemRepository.list_all`, не хранятся.

### P3 — UX-полировка (SPEC-003) ✅ done
- [x] Фильтры `/list` по статусам + пагинация по 10 (одно сообщение, `◀️/▶️`).
- [x] Карточка: пайплайн статуса, цена/оплата, ссылка, дата (`DD.MM.YYYY`).
- [x] Кнопка товара в списке открывает полную карточку (`view:<id>`).
- [-] Daily digest — отменен по решению (APScheduler не добавляем).

### P4 — Deploy 24/7 (SPEC-004) ❌ отклонён (хостинг)
Код готов и проверен вживую, но Fly.io оказался платным (~$3.9/мес: нет free-tier
у новых орг, 256 МБ OOM → 512 МБ). Оставлен как **опциональный** деплой.
- [x] `docker-entrypoint.sh`, `Dockerfile`, `.dockerignore`, `fly.toml`, Makefile.
- [x] Живой деплой проверен (миграции на volume, polling, рестарт) — затем остановлен.
- [-] Прод-хостинг переносится на Vercel (см. P5).

### P5 — Погашение долга и история (SPEC-005) ✅ done
Делать **до** хостинга. Долг становится не только «сколько накопилось», но и
«сколько осталось» с лентой погашений.
- [x] Агрегат `Repayment` (`amount_kop` > 0, note ≤256, `created_by`, `created_at`) +
  порт `IRepaymentRepository` (async): add, list_all (newest first), delete.
- [x] `AddRepaymentUseCase` (только исполнитель) + `CalcBalanceUseCase`:
  `balance = debt − Σ repayments`; отдельно «переплата»/«аванс», если внесли больше.
- [x] `/debt`: строки «Погашено», «Остаток» и (при переплате) «Аванс».
- [x] UX: кнопка `💸 Погасить` (исполнитель) → FSM сумма `«1 299,50»` → опц. комментарий →
  запись; ответ показывает новый остаток.
- [x] История: `/payments` (`📜 Погашения`) — дата, сумма, комментарий, кто внёс;
  удаление ошибочной записи исполнителем (с подтверждением).
- [x] Persistence: `RepaymentModel` + alembic `0005`, маппинг в `*_repo.py`.
- [x] Unit-тесты на погашение/баланс (in-memory) + интеграционный roundtrip;
  SPEC-002/README обновлены.
- Решено: погашение **пулом** (общий остаток), **переплата разрешена** (показывается
  как «аванс»), исполнитель может **удалять** ошибочные записи (с подтверждением).

### P6 — Vercel webhook + Neon (SPEC-006)
- [ ] Webhook-адаптер: ASGI-приложение (FastAPI) с aiogram-webhook; `setWebhook`
  при деплое, `deleteWebhook` при teardown. Long polling остаётся локальным fallback.
- [ ] Persistence: `DATABASE_URL=postgresql+asyncpg://…` (Neon), добавить `asyncpg`;
  SQLite (`aiosqlite`) — для local/тестов; `init_db` без SQLite-only `PRAGMA WAL`.
- [ ] Alembic под Postgres: прогнать `upgrade head` на Neon, поправить миграции при
  необходимости (сейчас диалект-агностичны — проверить).
- [ ] Vercel: `vercel.json`, env-секреты (`BOT_TOKEN`, `CUSTOMER_ID`, `EXECUTOR_ID`,
  `DATABASE_URL`), публичный HTTPS-URL, деплой + smoke (бот отвечает на `/start`).
- [ ] Обновить README/AGENTS под webhook + Neon; Fly-раздел → «отклонено».

## 7. Testing gate

- `tests/unit/test_*.py` на каждый use-case (in-memory repo, без сети/БД).
- Погашение: `balance = debt − Σ repayments`, частичные платежи, переплата,
  удаление записи, доступ только исполнителю.
- Webhook: обработчик отвечает 200 быстро и идемпотентно (повтор апдейта не
  дублирует эффект); интеграционный smoke — позже.
- Gate перед коммитом: `ruff check + mypy + pytest -q`.

## 8. Risks

| Риск | Митигация |
|---|---|
| Ozon меняет верстку/режет ботов | Не парсим вовсе на MVP, только ручная цена |
| Vercel Hobby — только non-commercial | Личный бот — личное использование, ок |
| Vercel недоступен из РБ | Проверить регистрацию **до** реализации; fallback — бесплатная VM/no-card хост |
| Bundle-лимит Vercel 250 МБ | `asyncpg` лёгкий; следить за размером, без `sqlite` в проде |
| Cold start функции | Тёплый старт на каждый апдейт; Telegram ретраит при таймауте |
| Лимиты Neon free | Маленький объём (2 пользователя); autosuspend, storage < лимита |
| Дрейф SQLite↔Postgres | Миграции диалект-агностичны + интеграционный тест |
| Апдейты при простое | Serverless просыпается на запрос; Telegram ретраит с backoff |
| Переплата / ошибочный платёж | Показывать «переплата»; исполнитель может удалить запись |

## 9. Next action

P1–P5 закрыты; P4 (Fly.io) отклонён — платно. Следующий приоритет —
**P6 / SPEC-006 — хостинг**: Vercel (Hobby, webhook) + Neon Postgres. Vercel из РБ
регистрируется (подтверждено). Fly-деплой подлежит удалению
(`fly apps destroy dolzhok`). Нейтрализация ролей (§10) выполнена досрочно.

## 10. Нейтрализация ролей ✅ done

Семейная специфика «папа ↔ сын» убрана из репозитория; роли заменены абстрактными
**заказчик** (присылает ссылки, получает товар, должен деньги) и **исполнитель**
(заказывает со своей карты, вносит статусы/цены, получает погашения). Сделано
досрочно — до P6, вместе с переименованием проекта.

- [x] Термины `заказчик` / `исполнитель` применены в `README.md`, `docs/**`,
  `AGENTS.md`, текстах бота и `/start`.
- [x] Код и env переименованы: `DAD_ID → CUSTOMER_ID`, `SON_ID → EXECUTOR_ID`,
  `dad_id → customer_id`, `son_id → executor_id`, `for_son → for_executor`;
  тесты обновлены.
- [x] Проект переименован `tg-bot-dad-ozon → dolzhok` (pyproject, README, PLAN,
  AGENTS, `fly.toml`, `uv.lock`).
- [ ] Прод-окружения (Fly secrets / Vercel env) перевести на новые имена при деплое.
