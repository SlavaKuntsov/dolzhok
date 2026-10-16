# Debt is derived; repayments are a single pool

The outstanding debt is computed from items on every call and never stored as a running total; the only money actually persisted is a ledger of `Repayment` entries. A repayment reduces the single running balance and is not tied to specific items. Deriving debt keeps item edits and status changes automatically consistent, and the pool model means cancellations, partial refunds, and overpayments need no allocation logic.

```
debt    = Σ (price × qty) WHERE payment = PREPAID AND status IN (ORDERED, RECEIVED)
balance = debt − Σ repayments        # < 0 → advance (the customer overpaid)
```

## Consequences

- Cancelling a prepaid item removes it from the debt (a refund) but does **not** auto-adjust past repayments; overpayment simply shows as an advance.
- The executor may delete a mistaken repayment entry (with confirmation).
