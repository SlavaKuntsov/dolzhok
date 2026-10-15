# PLAN — tg-bot-dad-ozon

> Связь «папа ↔ сын» для заказов с Ozon: оба присылают ссылки, сын заказывает
> со своей карты, бот считает, сколько папа должен вернуть.

## 1. Decisions (зафиксировано с заказчиком)

| Вопрос | Решение |
|---|---|
| Хостинг | Бесплатный клауд 24/7 (MacBook — только разработка) |
| БД на старт | SQLite файл + Repository-порт под замену (Turso) |
| Цена товара | Ручной ввод (автопарсинг Ozon ненадежен: JS/капча) |
| Роли | Папа и сын оба шлют ссылки; статусы/цены меняет только сын |

**Следствие про «офлайн-накопление»:** при `long polling` Telegram хранит
неподтвержденные апдейты **24 часа** (`getUpdates`/`offset`). Простой < 24ч
закрывается сам: бот просыпается и забирает очередь. Клауд 24/7 убирает
проблему полностью. Отдельный «офлайн-режим простановки статусов» не нужен —
состояния живут в БД, а не на клиенте.

## 2. Goal / Non-goals

**Goal (MVP):**
- Принять Ozon-ссылку от папы, показать сыну карточку с кнопками.
- Статусы: `NEW → TO_ORDER → ORDERED → RECEIVED | CANCELLED`.
- Оплата: `PREPAID` (оплатил сразу) / `POSTPAID` (постоплата).
- Команда `/debt`: сколько папа должен (предоплаченное, но не отмененное).

**Non-goals (пока нет):**
- Автопарсинг цены/названия с Ozon (только ручной ввод + fallback).
- Ozon API, корзина, авто-заказ.
- Мульти-семьи, платежи внутри бота, Mini App.

## 3. Ubiquitous Language

- `Item` — одна ссылка/товар. Агрегат.
- `status` — `NEW | TO_ORDER | ORDERED | RECEIVED | CANCELLED`.
- `payment` — `PREPAID | POSTPAID` (устанавливает сын при заказе).
- `price_kop` — цена в копейках, `int | None` до ручного ввода.
- `debt` — **вычисляемое**, не хранится:
  `Σ price WHERE status IN (ORDERED, RECEIVED) AND payment=PREPAID AND NOT cancelled`.

## 4. Stack

- Python **3.14** + `uv` (lock, sync, run).
- `aiogram 3.x` (`>=3,<4`) — async, routers, FSM.
- `SQLAlchemy 2.0 async` + `aiosqlite` (WAL) + `Alembic`.
- `pydantic-settings` — `BOT_TOKEN`, `DAD_ID`, `SON_ID`, `DATABASE_URL`.
- Docker + `fly.toml` + volume `/data` (Fly.io free).
- Тесты: `pytest`, `pytest-asyncio`.

## 5. Architecture (Clean / Hexagonal)

```
src/
  domain/          # pure: entities, value objects, ports. НЕТ aiogram/SQLAlchemy
  use_cases/       # только domain + порты (IItemRepository)
  adapters/
    telegram/      # routers, keyboards, filters, FSM
    persistence/   # ORM models, SqliteItemRepository, маппинг <-> entity
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
- [ ] `uv sync` зеленый, `pytest -q` зеленый (пустой)

### P1 — MVP прием ссылок (SPEC-001) ✅ done
- [x] `add_item`: regex Ozon (`ozon.ru`, `ozo.ru` + HEAD-redirect для коротких),
  дедуплика по нормализованному URL/SKU.
- [x] Карточка `#id NEW` папе (подтверждение) + сыну (кнопки).
- [x] Whitelist: отвечать только `DAD_ID`, `SON_ID`, остальных игнорить + лог.
- [x] FSM «ввод цены»: сын жмет `✏️ Цена` → бот ждет число → `set_price`.
- [x] Фильтры ролей: кнопки статусов — только сын (callback answer + alert).
- [x] Плюс: `change_status` с машиной переходов, `/list`, `/start`, `/cancel`,
  `SqliteItemRepository` + alembic `0001`, `HttpxOzonResolver`.

### P2 — Деньги и статусы (SPEC-002)
- `change_status` с машиной переходов (невалидный переход = ошибка, не молчание).
- `payment` при `ORDERED`: `PREPAID | POSTPAID`.
- `calc_debt` + `/debt`, `/list`, `/stats`.
- `CANCELLED` после `PREPAID` = «вернулось», в долг не входит (видно в `/stats`).

### P3 — UX-полировка (SPEC-003)
- Фильтры списка по статусам, пагинация (по 10).
- Текст карточки: ссылка, цена, статус, оплата, дата.
- Daily digest сыну (APScheduler, внутри воркера).

### P4 — Deploy 24/7 (SPEC-004)
- `fly launch --no-deploy`, volume `data` 1GB `ams`, `fly secrets set`.
- Проверка: рестарт → догоняет апдейты < 24ч, БД на месте.
- README-раздел Deploy + runbook (логи, бэкап `sqlite3 .dump`).

## 7. Testing gate

- `tests/unit/test_*.py` на каждый use-case (in-memory repo, без сети/БД).
- Polling-recovery: `offset = last_id + 1` после рестарта (интеграционный, позже).
- Gate перед коммитом: `ruff check + mypy + pytest -q`.

## 8. Risks

| Риск | Митигация |
|---|---|
| Ozon меняет верстку/режет ботов | Не парсим вовсе на MVP, только ручная цена |
| Render sleep / Railway платность | Только Fly.io free для прод-бота |
| 256MB RAM на Fly | Один воркер, без веб-сервера; мониторинг OOM |
| Потеря SQLite без volume | `mount /data`, WAL, бэкап дампом перед деплоем |
| Апдейты старше 24ч | Потеряны по дизайну Telegram API — приемлемо при 24/7 |

## 9. Next action

Строить P1 по `docs/specs/SPEC-001-ingest.md` вертикальным срезом:
regex → `AddItemUseCase` + тест → sqlite repo → telegram router → `/debt` заглушка.
