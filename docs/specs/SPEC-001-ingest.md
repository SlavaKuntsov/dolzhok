# SPEC-001 — ingest Ozon link (P1 MVP)

## Goal
Anyone whitelisted (dad or son) sends an Ozon URL, bot stores an `Item(NEW)`
and shows a card to both chats (inline buttons only for son).

## Flows
1. Whitelisted user sends message containing `ozon.ru/...` or `ozo.ru/...`.
2. Bot normalizes URL (resolve `ozo.ru` via HEAD redirect), extracts SKU/slug.
3. If URL already exists (dedup) → reply with existing card `#id`, no new row.
4. Else create `Item(NEW, price=None)` → card to sender + copy to the other
   party (`🆕 Dad sent #id` / `🆕 Son added #id`).
5. All user-facing text is Russian. Main commands are reply-keyboard
   buttons: `📋 Список` (/list), `💰 Долг` (/debt stub until P2).

## Acceptance criteria
- Given message from non-whitelisted user When received Then ignored + `log.warning`, no reply.
- Given `ozo.ru/abc` short link When ingested Then resolved to canonical `ozon.ru` URL.
- Given same URL twice When ingested Then second returns existing `id` (no duplicate).
- Given son presses `✏️ Price` When FSM input `«1 299,50»` Then `price_kop=129950`.
- Given son presses status button When `from_user.id != SON_ID` Then `alert` + no state change.

## Out of scope
Autoparsing price/title from Ozon HTML. Payment/debt (SPEC-002).
