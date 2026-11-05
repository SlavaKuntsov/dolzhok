# Receiving a postpaid item turns it into debt

`RECEIVED` + `POSTPAID` used to match neither branch of the debt formula: not prepaid debt, not pending postpaid. The amount silently vanished from both figures, so marking a postpaid item as received *reduced* the pending total without ever increasing the debt (the reported bug: 18,12 BYN disappeared and the balance stayed put).

We decided the semantic instead of patching the symptom: a postpaid item becomes debt the moment it is received, because the executor had to pay Ozon to collect it. Only an `ORDERED` postpaid item is still pending — money not yet owed.

```
prepaid_ordered   = Σ (price × qty) WHERE PREPAID  AND ORDERED
prepaid_received  = Σ (price × qty) WHERE PREPAID  AND RECEIVED
postpaid_received = Σ (price × qty) WHERE POSTPAID AND RECEIVED
postpaid_ordered  = Σ (price × qty) WHERE POSTPAID AND ORDERED   # pending, not debt
debt              = prepaid_ordered + prepaid_received + postpaid_received
balance           = debt + manual_debt − Σ repayments
```

The four buckets are the full `payment type × receipt status` grid, so every
in-work item that carries money is classified by construction — the bug this
ADR fixes was exactly a combination falling between two branches. Items that
carry no money (no price, or a zero line total) are counted separately as
unpriced work items rather than dropped.

## Consequences

- The debt is split by payment type and by receipt, and the summary explains each quantity: «Долг за товары» → «заплатил заранее» (with in-hand vs in-transit counts) and «заплатил при получении», then «Ещё не долг, оплачу при получении». The remaining line carries its own arithmetic (`долг − погашено`).
- Amounts and counts travel together as a `MoneyCount`, so a line can never print an amount from one bucket with a count from another.
- In-work items that carry no money (no price, or a zero line total) are reported as «⚠️ Без цены» instead of being dropped silently — the same class of gap as the original bug.
- Pending postpaid stays out of `debt`, so the running balance is unchanged by an order that has not arrived — it only moves when the item is received.
- The standalone gross «Итого долг» (accrual before repayments) and «Погашено» lines were dropped from the summary; the subtraction survives only as the one-line explanation under «Остаток». The repayment ledger still lives in «📜 Погашения».
- ADR-0003 (derived debt) and ADR-0005 (manual past-orders debt) are **amended**: their quoted formulas gained the `POSTPAID + RECEIVED` line. Both decisions otherwise stand — debt is still derived, and manual debt is still one signed figure.
