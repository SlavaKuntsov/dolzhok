# dolzhok

Customer and executor drop Ozon links → the executor orders with their own card → the bot tracks how much the customer owes back.

- Customer and executor: both send links, both use `/list` and `/debt`.
- Executor: buttons `1 New | 2 Ordered | 3 Received | 🚫 Cancel | ✏️ Price | 🔢 Qty` (plus `↩️ Reopen` on closed/cancelled items), commands `/debt /stats /pay /payments`.
- Menu buttons: `📋 List`, `💰 Debts`, `📊 Stats`, `❌ Cancel` (plus `/menu`, `/cancel`). `💰 Debts` immediately shows the debt summary and an action submenu: `💰 Debt`, `📜 Repayments` and (for the executor) `➕ Debt`, `✏️ Past debt`, `🗑 Reset debt`, `💸 Repay`, `⬅️ Back`.
- Repayments: the executor sends `💸 Repay` (amount + optional comment), the debt shrinks, the ledger lives in `📜 Repayments` (deleting a wrong entry asks for confirmation).
- Past-orders debt: `➕ Debt` adds an untracked amount (a negative value subtracts), `✏️ Past debt` overwrites the whole figure (typo fix), `🗑 Reset debt` zeroes it with confirmation. It counts in the debt and the balance but never appears in the item list.

The bot runs 24/7 on Vercel (webhook, FastAPI ASGI) + Neon Postgres. Locally — long polling and a SQLite file. The MacBook is for development only.

## Quickstart (local)

```bash
cp .env.example .env   # BOT_TOKEN, CUSTOMER_ID, EXECUTOR_ID, DATABASE_URL
uv sync
uv run alembic upgrade head
uv run python -m src.main
```

Token: `@BotFather` → `/newbot`. User IDs: `@userinfobot`.

## Commands

| Command | Who | What |
|---|---|---|
| `/start` | anyone in the whitelist | greeting + role |
| `/list` | both | cards of the last 10 items (with control buttons for the executor) |
| `/debt` | both | «Customer owes: X BYN» + «Repaid»/«Balance» (and «Advance» on overpayment) + pending postpaid |
| `/stats` | both | ordered/received/cancelled/refunds |
| `/pay` | executor | record a repayment (FSM: amount → optional comment) |
| `/payments` | both | repayment ledger (executor gets 🗑 with confirmation) |

Inline buttons under a card exist only for the executor (the customer sees a card without buttons). Updates from anyone outside the whitelist are ignored without a reply. For `Ordered`, the executor toggles payment with one button (`💳 Switch to prepaid/postpaid`); the default is prepaid. `Received`/`Cancelled` items have `↩️ Reopen` (back to `Ordered`).

## Debt formula

```
debt        = Σ (price × qty) WHERE status IN (ORDERED, RECEIVED) AND payment = PREPAID
            + manual_debt             # signed past-orders figure (may be negative)
postpaid    = Σ (price × qty) WHERE status = ORDERED AND payment = POSTPAID
repaid      = Σ repayment.amount_kop
balance     = debt − repaid            # < 0 → «advance» (overpayment)
```

A cancellation after prepayment is not counted as debt; it shows up in `/stats` as «refunds».
Repayments are a separate cash pool — cancellations do not adjust them automatically.

## Layout

```
src/domain/         # entities, value objects, IItemRepository/IRepaymentRepository (pure)
src/use_cases/      # add_item, set_price, set_payment, change_status, calc_debt, calc_stats, add/list/delete_repayment, calc_balance, adjust/set_manual_debt
src/adapters/telegram/     # routers, keyboards, fsm
src/adapters/persistence/  # sqlalchemy models + SqlAlchemyItem/RepaymentRepository (SQLite + Postgres)
src/adapters/webhook/      # FastAPI ASGI app (Vercel) + set/delete webhook CLI
src/infrastructure/ # config, db, bootstrap (shared wiring), logging
asgi.py             # Vercel entrypoint -> src.adapters.webhook.app:app
docs/adr/           # ADR: recorded decisions
docs/agents/        # skill setup (issue-tracker, triage-labels, domain)
```

Vocabulary lives in `GLOSSARY.md`; decisions in `docs/adr/`; specs and tickets in GitHub Issues; style in `AGENTS.md`.

## Deploy (Vercel serverless + Neon Postgres, ~$0)

Production is a Telegram **webhook** (FastAPI ASGI function on Vercel Hobby) + **Neon
Postgres** (`asyncpg`). Locally — long polling and SQLite. The decision and the
rejected Fly.io option are in `docs/adr/0001-vercel-neon-webhook-over-fly.md`.

`vercel.json` + `asgi.py` (`[tool.vercel] entrypoint` in `pyproject.toml`)
define the ASGI entrypoint; Vercel installs dependencies from `pyproject.toml`/`uv.lock`.

### First-time setup (manual, once)

1. **Neon**: create a project/database, copy the connection string into `DATABASE_URL`
   (it can stay as-is, `postgresql://…` — the driver is upgraded to `asyncpg`, and
   `sslmode`/`channel_binding` are normalized in code).
2. **Migrations on Neon** (from your local machine). `make migrate` reads `DATABASE_URL`
   from the environment **or `.env`**. For migrations use the **direct** (`ep-…`, no
   `-pooler`) host: the pooler in transaction mode breaks DDL.
   ```bash
   make migrate   # DATABASE_URL is already in .env, or: DATABASE_URL='postgresql://…' make migrate
   ```
3. **Vercel**: import the repository and set env vars (Production):
   `BOT_TOKEN`, `CUSTOMER_ID`, `EXECUTOR_ID`, `DATABASE_URL`,
   `WEBHOOK_BASE_URL=https://<app>.vercel.app`, `WEBHOOK_SECRET=<random string>`.
4. **Deploy + webhook**: `make deploy` — that is `vercel deploy --prod` + `make webhook-set`
   (`setWebhook` with the secret). Code only, no webhook: `make vercel-deploy`.
5. **Smoke test**: send the bot `/start` — it should reply.

### Updating

```bash
make migrate   # if the schema changed (DATABASE_URL from .env)
make deploy
```

### Runbook

| Task | Command |
|---|---|
| Deploy + webhook | `make deploy` |
| Code deploy only | `make vercel-deploy` |
| Webhook status | `make webhook-info` |
| Unregister webhook (back to polling) | `make webhook-delete` |
| Register webhook | `make webhook-set` |
| Neon migrations | `make migrate` (reads `DATABASE_URL` from `.env`) |
| Production function logs | `make logs-vercel` (last 30 min) |
| Checks (lint + types + tests) | `make check` |
| SQLite↔Postgres drift | `make test-pg` |
| Sequence in `0003` (destructive) | `make test-pg-reset` |

- **Logs.** `make logs-vercel` prints the last 30 minutes of production runtime logs
  and exits (it does not stream) — run it right after reproducing an issue. Vercel
  Hobby stores them for 1 hour per the docs, but the CLI on Hobby rejects `--since 1h`.
- **Why webhook.** Telegram retries undelivered updates with backoff and
  wakes the function on every request — no always-on worker needed (ADR-0001).
- **Updates outside the function.** `WEBHOOK_SECRET` is checked via the
  `X-Telegram-Bot-Api-Secret-Token` header; foreign requests get `403`. Without a
  secret the endpoint is open — in production the secret is mandatory (the app logs
  a warning at startup).
- **Schema — Alembic only (on both dialects).** `init_db` does not create tables
  (only `PRAGMA journal_mode=WAL` for SQLite); if migrations were not run, startup
  fails with a hint to run `make migrate`. Otherwise tables would appear without
  `alembic_version` and the first `upgrade head` would fail on `CREATE TABLE`.
- **Connections on serverless.** For Postgres the client-side pool is disabled
  (`NullPool`): pooling is done by the Neon pooler. Otherwise a frozen Vercel
  instance hands out a connection Neon has already closed (`InterfaceError: connection is closed`).
- **Dialect drift.** `make test-pg TEST_DATABASE_URL='postgresql://…'` runs
  migrations and a repo roundtrip on Postgres (optional, needs a separate DB).
  Without `TEST_DATABASE_URL` the test is skipped, so it is not part of `make check`.
  `make test-pg-reset` — a destructive check of the sequence in `0003` (scratch DB
  only: rewinds the schema to `0002` and back).
- **Known limitation (FSM).** The dispatcher uses `MemoryStorage`: on serverless the
  FSM state lives in a specific instance and is lost on cold start, so multi-step
  flows (`/pay`) may reset between updates. A persistent storage is needed (follow-up
  ticket); for now the risk is mitigated by a warm instance.

### Fly.io — rejected

Fly.io is no longer a production path (paid always-on, OOM on 256 MB — ADR-0001).
`Dockerfile`, `fly.toml` and the `make *-fly`/`fly-*` targets are kept as an optional
non-prod fallback; `make fly-init`/`make deploy-fly` only if really needed.
Removing the old app: `fly apps destroy dolzhok`.
