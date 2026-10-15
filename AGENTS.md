# AGENTS.md — tg-bot-dad-ozon

> Инструкция для AI-агентов и людей. Приоритет: рабочее MVP малыми срезами, тесты первыми.

## 0. Язык и тон

- Ответы пользователю — русский, коротко, по делу.
- Код, docstrings, коммиты, SPEC — английский.
- Ссылки на код — `path:line`.

## 1. Stack (не менять без обсуждения)

- Python `3.14` (`requires-python >=3.13`), менеджер `uv` only (не pip/poetry).
- `aiogram >=3,<4`, `sqlalchemy[asyncio]`, `aiosqlite`, `alembic`, `pydantic-settings`.
- Линт: `ruff`, типы: `mypy --strict` на `src/`, тесты: `pytest + pytest-asyncio (asyncio_mode=auto)`.

## 2. Команды (единственный способ запуска)

```bash
uv sync
uv run ruff check .
uv run mypy src
uv run pytest -q
uv run alembic upgrade head
uv run python -m src.main
```

## 3. Архитектура — Clean / Hexagonal (обязательно)

```
domain/         # entities, value_objects, interfaces. ЗАПРЕЩЕНЫ aiogram, sqlalchemy, pydantic
use_cases/      # импортируют ТОЛЬКО domain. Никаких adapters/infrastructure
adapters/       # telegram (routers/keyboards/fsm), persistence (models/repo)
infrastructure/ # config, engine/session, logging
```

- Граница через порт `IItemRepository` (async). Сейчас `SqliteItemRepository`, позже Turso — use-case'ы не меняются.
- Маппинг ORM ↔ entity только в `adapters/persistence/*_repo.py` (`_to_entity/_to_model`).
- Деньги: `int` копейки + `Money` VO, валидация в `__post_init__`, отрицательные запрещены.
- Статусы: `NEW → TO_ORDER → ORDERED → RECEIVED | CANCELLED`. Невалидный переход = `DomainError`, не молчаливое `pass`.
- FSM: минимум шагов; цена — парсинг `«1 299,50» → 129950`.

## 4. AI-first workflow (порядок на каждую фичу)

1. `docs/specs/SPEC-00X-<name>.md` — goal, flows, acceptance criteria (Given/When/Then).
2. `domain` + `use_case` + `tests/unit/test_<usecase>.py` с `InMemory*` (без БД/сети).
3. `adapters` (repo/handler) + `alembic revision` если схема менялась.
4. `ruff + mypy + pytest` зеленые → коммит.

Вертикальный срез > горизонтальный слой. Не строить «весь telegram» без use-case и теста.

## 5. Telegram-правила

- Whitelist `ALLOWED_USER_IDS={DAD_ID,SON_ID}` в `infrastructure/config.py`. Чужие — игнор + `log.warning`, без ответа (анти-спам).
- Проверка роли в filter, не в теле хендлера. Кнопки статусов — `F.from_user.id == SON_ID`.
- Long polling, `offset = last_update_id + 1` после рестарта. Никаких вебхуков на MVP.
- Ozon-детект: все локали `ozon.(ru|by|kz|com|uz)` + `ozo.ru`; короткие `/t/` и `ozo.ru` — HEAD-redirect резолв; дедуп по нормализованному URL. Текст до ссылки — в `title`.

## 6. Git

- Conventional Commits: `feat|fix|chore|docs|test|refactor: ...` (lowercase, без точки).
- Малые диффы, один use-case = один коммит(ы). Пуш/PR только по просьбе.
- Никогда не коммитить `.env`, `*.db`, `*.sqlite*`. Только `.env.example`.

## 7. Definition of Done

- [ ] SPEC обновлен/есть
- [ ] unit-тест зелен (in-memory)
- [ ] `ruff check .` + `mypy src` + `pytest -q` зеленые
- [ ] миграция `alembic` если менялась схема
- [ ] README/PLAN обновлены если менялся UX/деплой/формула долга

## 8. Запреты

- Нет `print` — только `logging`/`structlog`.
- Нет блокирующего I/O в async (`requests`, `time.sleep`) — только `httpx`/`aiohttp`, `asyncio.sleep`.
- Нет SQL в хендлерах. Нет aiogram-импортов в `domain/` и `use_cases/`.
- Не выдумывать URL/API Ozon — только проверенное или `TODO(spec)` с вопросом.
