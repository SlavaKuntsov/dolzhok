# AGENTS.md — dolzhok

> Инструкция для AI-агентов и людей. Приоритет: рабочее MVP малыми срезами, тесты первыми.

## 0. Язык и тон

- Ответы пользователю — русский, коротко, по делу.
- Код, docstrings, коммиты, SPEC — английский.
- Ссылки на код — `path:line`.

## 1. Stack (не менять без обсуждения)

- Python `3.14` (`requires-python >=3.13`), менеджер `uv` only (не pip/poetry).
- `aiogram >=3,<4`, `sqlalchemy[asyncio]`, `aiosqlite` (local), `asyncpg` (prod), `fastapi` (webhook ASGI), `alembic`, `pydantic-settings`.
- Линт: `ruff`, типы: `mypy --strict` на `src/`, тесты: `pytest + pytest-asyncio (asyncio_mode=auto)`.
- Деплой: прод — Vercel webhook (`asgi.py` → `src.adapters.webhook.app:app`) + Neon Postgres; локально — long polling + SQLite (ADR-0001).

## 2. Команды (единственный способ запуска)

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
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

- Граница через порт `IItemRepository` (async). Сейчас `SqlAlchemyItemRepository`, позже Turso — use-case'ы не меняются.
- Маппинг ORM ↔ entity только в `adapters/persistence/*_repo.py` (`_to_entity/_to_model`).
- Деньги: `int` копейки + `Money` VO, валидация в `__post_init__`, отрицательные запрещены.
- Статусы: любой → любой (кроме того же), свободной выбор кнопками. Повторные ссылки = отдельные товары (дедупа нет).
- FSM: минимум шагов; цена — парсинг `«1 299,50» → 129950`.

### Навигация по коду (CodeGraph)

- Ищем код через `codegraph explore "<символы или вопрос>"` (MCP-тул `codegraph_explore` или тот же CLI) — сразу отдаёт исходник нужных символов + цепочку вызовов и blast radius. `grep`/`Read` — для конфигов, миграций, `docs/` и когда индекса нет.
- Markdown (`docs/`, `GLOSSARY.md`, ADR) и YAML не индексируются — там только `grep`/`Read`.
- Индекс локальный: `.codegraph/` в `.gitignore`, демон синкает сам. `codegraph status` показывает pending — при отставании `codegraph sync`. Нет `.codegraph/` — не создаём без просьбы, работаем `grep`/`Read`.

## 4. Workflow — скиллы mattpocock (`.agents/skills/`)

Стадии, режимы, кто что вызывает и в каком порядке — `docs/dev-pipeline.md`, единственный источник.

Вертикальный срез > горизонтальный слой. Не строить «весь telegram» без use-case и теста: `domain` + `use_case` + `tests/unit/test_<usecase>.py` с `InMemory*` (без БД/сети), затем `adapters` (repo/handler) + `alembic revision` если схема менялась.

## 5. Telegram-правила

- Whitelist `ALLOWED_USER_IDS={CUSTOMER_ID,EXECUTOR_ID}` в `infrastructure/config.py`. Чужие — игнор + `log.warning`, без ответа (анти-спам).
- Проверка роли в filter, не в теле хендлера. Кнопки статусов — `F.from_user.id == EXECUTOR_ID`.
- Локально — long polling (`offset = last_update_id + 1` после рестарта); прод — webhook на Vercel. Регистрация: `python -m src.adapters.webhook.manage set|delete|info` (`make webhook-*`).
- Ozon-детект: все локали `ozon.(ru|by|kz|com|uz)` + `ozo.ru`; короткие `/t/` и `ozo.ru` храним как есть (без HTTP-резолва); дедупа нет, каждая ссылка = отдельный товар. Текст до ссылки — в `title`.

## 6. Git

- Conventional Commits: `feat|fix|chore|docs|test|refactor: ...` (lowercase, без точки).
- Малые диффы, один use-case = один коммит(ы). Пуш/PR только по просьбе.
- Никогда не коммитить `.env`, `*.db`, `*.sqlite*`. Только `.env.example`.
- **Ветка на работу.** Любой тикет/спека — в ветке от свежего `main`: `feat/<phase>-<slug>`, `fix/<slug>` или `chore/<slug>`. В `main` напрямую не коммитим. Скилл `/implement` коммитит в **текущую** ветку — перед стартом сделай `git switch -c feat/<phase>-<slug> origin/main`.
- **Спека ≠ тикет.** Issue-спека (как SPEC-006) не граббится как один тикет: сначала нарезка на sub-issues с блокировками (см. `docs/dev-pipeline.md`). Реализация: один тикет — `/implement`, вся спека — `/implement-spec`.

## 7. Definition of Done

- [ ] issue (spec/тикет) отражает работу и закрыт
- [ ] unit-тест зелен (in-memory)
- [ ] `ruff check .` + `ruff format --check .` + `mypy src` + `pytest -q` зеленые (`make check` — lint + types + tests)
- [ ] миграция `alembic` если менялась схема
- [ ] `GLOSSARY.md` / ADR обновлены если менялся язык или решение
- [ ] README обновлён если менялся UX/деплой/формула долга

## 8. Запреты

- Нет `print` — только `logging`/`structlog`.
- Нет блокирующего I/O в async (`requests`, `time.sleep`) — только `httpx`/`aiohttp`, `asyncio.sleep`.
- Нет SQL в хендлерах. Нет aiogram-импортов в `domain/` и `use_cases/`.
- Не выдумывать URL/API Ozon — только проверенное или `TODO(spec)` с вопросом.

## Agent skills

### Issue tracker

Issues и спеки живут в GitHub Issues (`SlavaKuntsov/dolzhok`, через `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Дефолтные пять ролей: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` + `docs/adr/` в корне. See `docs/agents/domain.md`.
