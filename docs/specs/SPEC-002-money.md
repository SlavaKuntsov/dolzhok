# SPEC-002 — money, payment and debt (P2)

## Goal
Turn tracked links into money: mark `payment` when an item is ordered, then
compute the debt dad owes son and show per-status stats. Nothing is stored as a
running total — `debt` and stats are derived from items on every call.

## Flows
1. Son sets payment on an item in work (`ORDERED` or `RECEIVED`) via inline
   buttons `💳 Предоплата` / `💳 Постоплата` (the current choice is inert).
   Payment may be (re)set on received items too.
2. `/debt` (or `💰 Долг`) shows two numbers:
   - `Папа должен` — prepaid items in `ORDERED`/`RECEIVED` (son paid, dad owes).
   - `Ждет постоплаты` — postpaid items still `ORDERED` (dad pays on receipt).
   It also shows the running balance after repayments — `Погашено`, `Остаток`
   and (when overpaid) `Аванс` (see SPEC-005).
3. `/stats` (or `📊 Статистика`) shows counts per status plus returns.
4. Cancelling a `PREPAID` item is a refund: it leaves the debt and appears under
   `↩️ Возвраты` in `/stats`. Returns are never part of the debt.

## Formulas
```
item total  = price_kop * qty                    (None price → ignored)
debt        = Σ total WHERE payment = PREPAID AND status IN (ORDERED, RECEIVED)
postpaid    = Σ total WHERE payment = POSTPAID AND status = ORDERED
returns     = items WHERE status = CANCELLED AND payment = PREPAID
```

## Acceptance criteria
- Given son presses `2 📦 Заказан` When card rerenders Then payment buttons appear.
- Given payment `PREPAID` on an ordered item with total 2 599 BYN When `/debt` Then
  `Папа должен: 2 599,00 BYN`.
- Given a prepaid item is then `CANCELLED` When `/debt` Then it is excluded;
  When `/stats` Then `↩️ Возвраты` counts it and sums its total.
- Given a postpaid `ORDERED` item When `/debt` Then it shows under `Ждет постоплаты`,
  not under `Папа должен`.
- Given an item without price When computing debt Then it is skipped (no crash).
- Given qty > 1 When computing total Then `price_kop * qty` is used.
- Given non-son taps a `pay:` button When received Then `alert`, no state change.
- Given any card with a payment Then the money line shows `💳 предоплата` /
  `💳 постоплата`; a refunded item shows `↩️ возврат`.

## Out of scope
Editing history/audit trail, partial refunds, per-item currency, Ozon API.