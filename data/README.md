# Data directory (gitignored)

Nothing in this directory is committed except this file. To reproduce:

1. `python src/fetch_pokemon_catalog.py` — sets, cards, and current
   TCGplayer price snapshot from the Pokemon TCG API v2 (requires
   POKEMONTCG_API_KEY in .env).
2. `python src/fetch_mtg_catalog.py` — set list, card attributes, and
   price snapshot from MTGJSON.
3. `python src/fetch_price_snapshot.py` — dated snapshot for both games,
   written to data/snapshots/YYYY-MM-DD/. Run on a schedule to accrue
   history.
4. `data/sealed_prices.csv` — hand-collected TCGplayer sealed prices,
   single collection date per batch (see collected_date column).
5. `data/msrp_sources.csv` — release MSRP / typical retail at release,
   one citation URL per row.

## Rarity mapping table

[committed here at build time: MTG tier <-> Pokemon tier mapping used in
the cross-game rarity analysis]
