# Dev pipeline — dolzhok

Как проходит задача от идеи до мержа. Скиллы mattpocock стоят в `.agents/skills/`; артефакты оседают в GitHub Issues + `GLOSSARY.md` + `docs/adr/`.

```
идея → выравнивание → спека → тикеты → триаж → реализация → ревью → PR → ретро
       /grill-with-docs /to-spec /to-tickets /triage /implement  /code-review /pr /retro
                                                          └─ /tdd
```

## Стадии

| # | Стадия | Скилл | Что на выходе / куда |
|---|---|---|---|
| 0 | Настройка (разово на репо) | `setup-matt-pocock-skills` ✅ | `docs/agents/*`, метки на GitHub |
| 1 | Выравнивание «что вообще строим» | **`/grill-with-docs`** (код) · `/grill-me` (не код) | уточнённый план; правки в `GLOSSARY.md` + `docs/adr/` по ходу |
| 2 | Спека | **`/to-spec`** | GitHub Issue в `SlavaKuntsov/dolzhok` (без интервью — синтез из разговора) |
| 3 | Нарезка на тикеты | **`/to-tickets`** | tracer-bullet issues с блокировками (sub-issues / `Blocked by`) |
| 4 | Триаж | **`/triage`** | двигает метки: `needs-triage → needs-info → ready-for-agent/ready-for-human → wontfix` |
| 5 | Реализация | **`/implement`** (один тикет/фронт) · **`/implement-spec`** (вся спека, параллельные субагенты) | код + тесты; внутри ведёт **`/tdd`** |
| 6 | Ревью | **`/code-review`** | два параллельных субагента: Standards + Spec |
| 7 | PR | **`/pr`** | тело PR (summary, before/after, merge-danger) |
| 8 | Ретро | `/retro`; раз в несколько дней `/improve-codebase-architecture` | предложения по среде/архитектуре |

## Три режима

- **Обычная фича (тикет):** `/grill-with-docs` → `/to-spec` → `/to-tickets` → `/triage` (стало `ready-for-agent`) → `/implement` → `/code-review` → `/pr`
- **Хардкорный баг:** `/diagnosing-bugs` вместо `/implement` (красный фидбек-луп → минимизация → гипотеза → инструмент → фикс → регресс-тест).
- **Большая неясная тема:** `/wayfinder` (карта решенческих тикетов на issues) и/или `/research` (факты из первоисточников → cited markdown).

## Кто вызывается

- **Ты вызываешь слэшем** (оркестраторы): `/ask-matt` (роутер), `/grill-with-docs`, `/to-spec`, `/to-tickets`, `/triage`, `/implement`, `/implement-spec`, `/wayfinder`, `/retro`, `/improve-codebase-architecture`, `/setup-matt-pocock-skills`.
- **Агент подтягивает сам по задаче** (дисциплина): `/tdd`, `/code-review`, `/diagnosing-bugs`, `/domain-modeling`, `/codebase-design`, `/pr`, `/prototype`, `/research`, `/wizard`, `/grilling`, `/writing-for-agents`.

## Где что лежит

- **Язык** → `GLOSSARY.md`
- **Решения** → `docs/adr/NNNN-*.md`
- **Спеки и тикеты** → GitHub Issues (`docs/agents/issue-tracker.md`)
- **Метки триажа** → `docs/agents/triage-labels.md`
- **Правила чтения домена** → `docs/agents/domain.md`

## Личные задачи (не код)

`/handoff` (сжать сессию другому агенту), `/wait-what` (не дошло — переобъясни), `/teach`, `/to-questionnaire`.
