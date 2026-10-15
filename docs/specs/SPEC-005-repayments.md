# SPEC-005 — debt repayment & history (P5)

## Goal
Let executor record money customer actually hands over, so the outstanding debt shrinks and
there is a visible history of repayments. The debt itself stays **derived** from
items; the only new stored thing is a ledger of `Repayment` entries. Pool model:
a repayment reduces the single running balance, it is not tied to specific items.

## Flows
1. Executor taps `💸 Погасить` (reply menu) or `/pay` → FSM: enter amount
   `«1 299,50»` → optional comment → repayment saved; bot replies with the new
   remaining balance.
2. `/debt` (`💰 Долг`) shows: `Заказчик должен` (debt), `Погашено` (Σ repayments),
   `Остаток` (`debt − repaid`); when overpaid, an `Аванс` / `Переплата` line.
3. `/payments` (`📜 Погашения`) lists repayments newest-first: `DD.MM.YYYY`,
   amount, comment, who entered it; each row has `🗑` (executor only, with confirm).
4. Customer sees `/debt` and `/payments` read-only — no buttons, no FSM.

## Formulas
```
debt     = Σ (price_kop * qty) WHERE payment = PREPAID AND status IN (ORDERED, RECEIVED)
repaid   = Σ repayment.amount_kop
balance  = debt - repaid          # < 0 → advance (переплата)
```
Cancelling a prepaid item already leaves the debt (SPEC-002); repayments are
independent cash and are not auto-adjusted by cancellations.

## Domain
- `Repayment` aggregate: `id`, `amount_kop` (via `Money` VO, `> 0`), `note`
  (optional, ≤256), `created_by`, `created_at`.
- Port `IRepaymentRepository` (async): `add`, `list_all` (newest first), `delete(id)`.
- Use cases: `AddRepaymentUseCase` (validates amount > 0), `ListRepaymentsUseCase`,
  `DeleteRepaymentUseCase`, and `CalcBalanceUseCase` (`debt`, `repaid`, `balance`,
  counts). `CalcDebtUseCase` stays as-is for the postpaid line.

## Persistence
- `RepaymentModel` + alembic `0005_create_repayments` (dialect-agnostic types).
- Mapping only in `adapters/persistence/*_repo.py`.

## UX
- Reply menu gains `💸 Погасить`; commands `/pay`, `/payments`.
- FSM states: `RepaymentFSM.amount`, `RepaymentFSM.note` (optional, `/cancel` clears).
- Amount parsing reuses the price parser (`«1 299,50» → 129950`).

## Acceptance criteria
- Given debt 2 599,00 and executor pays 1 000,00 When `/debt` Then `Остаток: 1 599,00`
  and `/payments` has one entry.
- Given debt 2 599,00 and a full payment 2 599,00 When `/debt` Then `Остаток: 0,00`.
- Given debt 1 000,00 and payment 1 500,00 When `/debt` Then balance `-500,00`
  shown as `Аванс: 500,00` (no negative "долг").
- Given a repayment When executor taps `🗑` and confirms Then it is gone and the balance
  is restored; customer tapping `🗑` gets an `alert` and no state change.
- Given input `«1 299,50»` When parsed Then `amount_kop = 129950`.
- Given input `«0»` or empty/garbage When submitted Then an error hint, no record.
- Given an item without price When computing the balance Then it is skipped.
- Given repayments exist When `/payments` renders Then entries are newest-first
  with date, amount and comment.

## Out of scope
FIFO / per-item settlement, editing a repayment (delete + re-add instead),
multi-currency, receipts/screenshots, automatic reconciliation with refunds.