# SPEC-001 — ingest Ozon link (P1 MVP)

## Goal
Dad sends an Ozon URL, bot stores an `Item(NEW)` and shows a card with action buttons to son.

## Flows
1. Dad (`DAD_ID`) sends message containing `ozon.ru/...` or `ozo.ru/...`.
2. Bot normalizes URL (resolve `ozo.ru` via HEAD redirect), extracts SKU/slug.
3. If URL already exists (dedup) → reply with existing card `#id`, no new row.
4. Else create `Item(NEW, price=None)` → confirm to dad + card to son with buttons.

## Acceptance criteria
- Given message from non-whitelisted user When received Then ignored + `log.warning`, no reply.
- Given `ozo.ru/abc` short link When ingested Then resolved to canonical `ozon.ru` URL.
- Given same URL twice When ingested Then second returns existing `id` (no duplicate).
- Given son presses `✏️ Price` When FSM input `«1 299,50»` Then `price_kop=129950`.
- Given son presses status button When `from_user.id != SON_ID` Then `alert` + no state change.

## Out of scope
Autoparsing price/title from Ozon HTML. Payment/debt (SPEC-002).
