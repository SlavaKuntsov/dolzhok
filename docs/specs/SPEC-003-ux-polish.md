# SPEC-003 — list UX & card details (P3)

## Goal
Make the growing item list usable: filter by status, page through it 10 at a
time, open any item as a full card, and show the full card details (link,
price, status, payment, date). No new stored state — everything is derived from
`IItemRepository.list_all`.

## Flows
1. `/list` (or `📋 Список`) sends **one** message: a header, a filter row, one
   button per item on the current page, and a prev/next row.
2. Filter buttons `Все · 🆕 · 📦 · ✅ · 🚫` switch the status filter; the active
   filter is rendered inert. Changing the filter jumps back to page 1.
3. `◀️` / `▶️` move one page (10 items). Arrows at the ends are inert.
4. Tapping an item button (`view:<id>`) opens that item's full card
   (`card_message`) as a new message — with action buttons for executor, plain for
   customer.
5. The full card shows: `#id` + pipeline (status), optional title, money line
   with `💳 предоплата`/`💳 постоплата`/`↩️ возврат`, link, and the creation
   date.
6. Card actions (executor): open items get status buttons (current inert) + `✏️ Цена`
   + `🔢 Кол-во`; `ORDERED` items get the payment toggle; **closed items
   (`RECEIVED` and `CANCELLED`) get a single `↩️ В работу` button** that returns
   them to `ORDERED`.

## Pagination / filtering
```
page_size       = 10
filtered        = items WHERE status = filter        (all items when filter = none)
total           = len(filtered)
pages           = max(1, ceil(total / page_size))
page            = clamp(requested, 0, pages - 1)
page_items      = filtered[page*page_size : (page+1)*page_size]   (newest first)
```

## Date format
`created_at` rendered as `DD.MM.YYYY` (e.g. `📅 15.10.2026`).

## Acceptance criteria
- Given 24 items When `/list` (filter «Все») Then header says `стр. 1/3 · всего 24`
  and the message holds ≤10 item buttons.
- Given the list When `▶️` Then the header shows `стр. 2/3` and items 11-20 are
  listed; When `◀️` on page 1 Then the arrow is inert (no request).
- Given filter `🚫 Отменено` When pressed Then only cancelled items count in
  `всего` and the page resets to 1.
- Given an empty filter result When the page renders Then a hint line is shown
  and no item buttons.
- Given an item button When tapped Then a full card for that `#id` is sent;
  for executor it carries action buttons, for customer it does not.
- Given a `RECEIVED` or `CANCELLED` item When its card renders for executor Then it
  shows `↩️ В работу`, which moves it back to `ORDERED`.
- Given any card When rendered Then it contains the pipeline status, money line,
  `🔗` link and `📅 DD.MM.YYYY`.
- Given a requested page beyond the last When the use case runs Then it clamps
  to the last page (no crash, never empty-by-error).
- Given `page_size < 1` When the use case runs Then `DomainError`.

## Out of scope
- Daily digest / APScheduler (dropped from P3 by decision).
- Strict status transitions and `TO_ORDER` (separate ticket; statuses stay free).
- Search by text, sorting options, per-item deletion.
- Stored list state / cursor persistence (page+filter live in the button callbacks).
