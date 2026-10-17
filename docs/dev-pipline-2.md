Верный путь для #9

1. /grill-with-docs — выравнивание. ✅ Сделано раньше: зафиксировано в ADR-0001 (Vercel+Neon вместо Fly).
2. /to-spec — спека в GitHub Issue. ✅ #9 и есть спека.
3. /to-tickets ← вот это пропущено. Спеку режут на вертикальные tracer-bullet тикеты с блокировками, публикуют sub-issues и вешают ready-for-agent. #9 так и остался одной issue с 6 чекбоксами и меткой needs-triage — граббить агенту нечего.
4. /triage — двигает метки (needs-triage → ready-for-agent / ready-for-human). Тоже пропущено.
5. Реализация — тут два законных варианта:

- /implement-spec #9 — вся спека за один прогон: создаёт integration branch, гоняет implementer-субагентов по каждому тикету в отдельных worktree/ветках, мержит, и один /code-review по integration branch. Это и был «правильный» скилл для #9.
- либо /implement #<child> по каждому нарезанному тикету — свой branch на тикет, /code-review на каждый.
- /implement (без -spec) по определению работает в текущей ветке — поэтому он и не должен был идти по целой спеке.

6. /code-review — ✅ сделано (Standards + Spec, двумя субагентами).
7. /pr — тело PR. ⬜
8. /retro — ⬜
