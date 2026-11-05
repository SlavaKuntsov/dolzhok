# Manual past-orders debt is a single signed figure

Some debt predates the bot: past orders the customer never paid for, with no Ozon link worth entering. Those amounts must still count against the running balance, but modelling them as `Item` rows would leak them into the item list, status pipeline, stats and cards.

We store one signed `ManualDebt` figure in its own `manual_debts` table (single row). It is added to the derived item debt:

```
debt    = Σ (price × qty) WHERE payment = PREPAID AND status IN (ORDERED, RECEIVED)
        + Σ (price × qty) WHERE payment = POSTPAID AND status = RECEIVED   # ADR-0006
        + manual_debt
balance = debt − Σ repayments        # < 0 → advance (the customer overpaid)
```

Status: amended by [ADR-0006](0006-postpaid-received-becomes-debt.md); the
postpaid-received line and the pending/`Ждет постоплаты` split are newer than
this decision.

The executor changes it with an add/subtract delta (`➕ Долг`, negative input subtracts), overwrites it (`✏️ Долг за прошлое`, fixing a typo) or resets it to zero (`🗑 Сбросить долг`, with confirmation). Only the executor sees the actions; the customer only sees the total debt.

## Consequences

- The figure may be negative: subtracting more than the current value means the customer overpaid for past orders. It is not clamped — the balance already renders overpayment as «Аванс».
- There is no per-entry history: one number, fixed by overwriting or resetting. Per-entry records were rejected as unnecessary UI for a two-person ledger.
- Manual debt never appears in the item list, never has a status and never counts as a refund in `/stats`.
- Repayments stay a single pool (ADR-0003); they shrink item debt and manual debt alike, with no allocation.
