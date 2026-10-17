# dolzhok

A two-person ledger for Ozon shopping: the executor fronts money for goods the customer wants, and the customer later repays it. The whole domain exists to answer one question — how much does the customer still owe?

## Language

### People

**Customer**:
The person who wants the goods and ends up owing money for them.
_Avoid_: buyer, client, user, dad

**Executor**:
The person who orders and fronts the money, then collects repayment.
_Avoid_: seller, admin, operator, son

### Items

**Item**:
One tracked Ozon product link, with an optional price and quantity. Each link is its own item; there is no dedup.
_Avoid_: product, position, order, link, card

**Item status**:
Where an item sits in its lifecycle: `NEW`, `ORDERED`, `RECEIVED`, `CANCELLED`. The first three form the pipeline; `CANCELLED` sits outside it.
_Avoid_: state, stage, phase

**Payment type**:
Who carries the money risk on an item — `PREPAID` (executor already paid, customer owes) or `POSTPAID` (customer pays on receipt).
_Avoid_: method, kind, paid status

**Line total**:
An item's `price × quantity`. Unknown while the item has no price; unknown totals are ignored in money math.
_Avoid_: sum, cost, subtotal

**SKU**:
Ozon's numeric product identifier, extracted best-effort from the link.
_Avoid_: id, article, code

**Title**:
The product name typed by the user — the message text before the link.
_Avoid_: name, label, description

### Money

**Money**:
A non-negative amount held in kopecks (minor units), displayed as roubles like `1 299,50 BYN`.
_Avoid_: amount, value, price

**Debt**:
Money the customer owes the executor: prepaid items still in work (ordered or received) plus the manual debt. Shown as «Долг» to the customer and broken down as «Долг по товарам» + «Долги за прошлое» to the executor.
_Avoid_: total, amount owed, balance, sum

**Manual debt**:
Money from past orders that were never tracked as items, entered by hand as one running figure. It is signed: negative means the customer overpaid on past debt. It counts in the debt but is not an Item and never appears in the item list.
_Avoid_: item, old order, extra debt, adjustment

**Pending postpaid**:
Postpaid ordered items the customer has not paid for yet. Explicitly not part of the debt. Shown as «Ждет постоплаты».
_Avoid_: debt, unpaid, outstanding

**Repayment**:
One cash transfer from the customer to the executor that shrinks the running balance. It is a free pool — never tied to a specific item.
_Avoid_: payment, transfer, transaction, instalment

**Balance**:
Debt (items plus manual debt) minus repayments. Positive means the customer still owes; zero means settled. Shown as «Остаток».
_Avoid_: remainder, debt, difference

**Advance**:
When repayments exceed the debt — the customer has overpaid. Shown as «Аванс» / «Переплата».
_Avoid_: overpayment, credit, deposit, prepayment

**Refund**:
A prepaid item that got cancelled — the money came back, and it never counts as debt. Shown under «Возвраты».
_Avoid_: return, cancellation, reversal
