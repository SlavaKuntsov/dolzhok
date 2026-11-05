# Receiving a postpaid item turns it into debt

`RECEIVED` + `POSTPAID` used to match neither branch of the debt formula: not prepaid debt, not pending postpaid. The amount silently vanished from both figures, so marking a postpaid item as received *reduced* the pending total without ever increasing the debt (the reported bug: 18,12 BYN disappeared and the balance stayed put).

We decided the semantic instead of patching the symptom: a postpaid item becomes debt the moment it is received, because the executor had to pay Ozon to collect it. Only an `ORDERED` postpaid item is still pending — money not yet owed.

```
debt_prepaid  = Σ (price × qty) WHERE payment = PREPAID  AND status IN (ORDERED, RECEIVED)
debt_postpaid = Σ (price × qty) WHERE payment = POSTPAID AND status = RECEIVED
pending       = Σ (price × qty) WHERE payment = POSTPAID AND status = ORDERED
debt          = debt_prepaid + debt_postpaid
balance       = debt + manual_debt − Σ repayments
```

## Consequences

- The debt is now split by payment type in the response, and the summary renders it that way: «Уже оплачено за товары» with `предоплата`/`постоплата` bullets, then «Будет оплачено при получении».
- Pending postpaid stays out of `debt`, so the running balance is unchanged by an order that has not arrived — it only moves when the item is received.
- The gross «Итого долг» (accrual before repayments) and «Погашено» lines were dropped from the summary: only the work-in-progress split and «Остаток» answer "how much is left". The repayment ledger still lives in «📜 Погашения».
- ADR-0003 (derived debt) and ADR-0005 (manual past-orders debt) are **amended**: their quoted formulas gained the `POSTPAID + RECEIVED` line. Both decisions otherwise stand — debt is still derived, and manual debt is still one signed figure.
