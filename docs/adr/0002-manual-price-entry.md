# Manual price entry, no Ozon scraping

Item prices are entered by hand; the bot never fetches or parses Ozon pages. Ozon's storefront is JS-rendered, bot-hostile, and changes markup often, so automated parsing is unreliable and would break silently. We still detect and store Ozon links (all locales + `ozo.ru`, short `/t/` links kept as-is without HTTP resolution) and take the pre-link message text as the title, but price is always a manual step.

## Consequences

- The price parser accepts human input like `«1 299,50»` and stores kopecks.
- Items can exist without a price; unknown totals are ignored in money math rather than blocking.
