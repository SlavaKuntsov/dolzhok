# SPEC-001 — ingest Ozon link (P1 MVP)

## Goal
Anyone whitelisted (dad or son) sends an Ozon URL, bot stores an `Item(NEW)`
and shows a card to both chats (inline buttons only for son).

## Flows
1. Whitelisted user sends message containing an Ozon URL (any locale:
   `ozon.ru/by/kz/com/uz`, short `ozo.ru`, share `/t/` links). Leading text
   before the URL is stored as the item title.
2. Bot normalizes URL (resolve short/share links via HEAD redirect), extracts SKU/slug.
3. Every sent link creates a NEW item, even if the URL already exists
   (duplicates are separate goods, e.g. two identical втулки for different needs).
4. Else create `Item(NEW, price=None)` → card to sender + copy to the other
   party (`🆕 Dad sent #id` / `🆕 Son added #id`).
5. All user-facing text is Russian. Global actions live in the persistent
   reply menu: `📋 Список` (/list), `💰 Долг` (/debt stub until P2),
   `📊 Статистика` (/stats stub until P2), `❌ Отмена` (/cancel, clears FSM).
   `/menu` re-sends the menu if hidden.

## Acceptance criteria
- Given message from non-whitelisted user When received Then ignored + `log.warning`, no reply.
- Given `ozo.ru/abc` short link When ingested Then resolved to canonical `ozon.ru` URL.
- Given same URL twice When ingested Then two items with different `id`.
- Given son opens a card Then status buttons show every other pipeline
  status in their own rows (free transitions); same-status press is rejected.
- Given son presses `✏️ Цена` When FSM input `«1 299,50»` Then `price_kop=129950`.
- Given son presses `🔢 Кол-во` When FSM input `«3»` Then `qty=3` (default 1).
- Given non-son whitelisted user triggers a son-only button When received Then `alert` + no state change.
- Given dad sends a new URL Then son receives a copy; Given son sends Then dad receives a copy.

## Out of scope
Autoparsing price/title from Ozon HTML. Payment/debt (SPEC-002).
