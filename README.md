# Pokémon vs. Magic: The Gathering — Market Analytics

Statistical comparison of the two largest trading card games as products and
as markets: singles price distributions, rarity premium structure, sealed
product appreciation since release, and catalog/release cadence.

## Questions

1. **Do singles prices differ between the games?** Distribution comparison of
   TCGplayer market prices for cards from matched-era sets (Feb 2024 – Jun 2026).
2. **Is the rarity premium structured differently?** How much of each game's
   value concentrates in its top rarity tiers.
3. **Has sealed product appreciated since release?** Release MSRP vs. current
   market price per set, compared across games.
4. **Straight market comps:** franchise start dates, release cadence
   (sets/year), catalog growth, and average booster pricing.

## Data

- **MTG:** MTGJSON (card/set catalog, price snapshot) — fetched YYYY-MM-DD
- **Pokémon:** Pokémon TCG API v2 (card/set catalog + TCGplayer price
  snapshot) — fetched YYYY-MM-DD
- **Sealed product prices:** hand-collected from TCGplayer, single collection
  date per batch — YYYY-MM-DD
- **Release MSRP:** hand-researched; sources cited in `data/README.md`

Set scope: all main-series and major special expansions released
2024-02-01 through 2026-06-30 (15 MTG sets, N Pokémon sets), so both samples
cover the identical market window.

## Method

Python pipeline (`src/`) fetches catalogs and daily price snapshots, builds
matched analysis tables, and runs the inference suite; Tableau consumes the
processed CSVs. Statistical tests are non-parametric (prices are heavily
right-skewed): Mann–Whitney U for cross-game distribution comparisons,
Kruskal–Wallis + Dunn's post-hoc for rarity tiers, bootstrap confidence
intervals on medians, Holm correction across the primary hypothesis family.

## Findings (singles; sealed pending)

1. Card-for-card, MTG singles price modestly higher: median cheapest copy
   $0.29 vs $0.19; Cliff's delta 0.163 (set-clustered 95% CI 0.063-0.250).
2. Pokemon concentrates 93.5% of singles market value in its top rarity
   tier vs 71.2% for MTG (gap CI [-0.37, -0.11]) - the games differ more
   in where value sits than in what a typical card costs.
3. Both rarity ladders are statistically real (all MTG tier pairs
   distinct; 32/55 Pokemon pairs, adjacent premium tiers overlapping).
4. Results are stable across set-age strata and mapping sensitivity;
   including all finishes widens the gap, making the cheapest-copy
   primary grain the conservative choice.

<!-- methodology additions -->
- Multi-face MTG cards deduplicated to their primary face (MTGJSON
  assigns each face a uuid against one physical product).
- Value-concentration figures are shares of the printed catalog at
  TCGplayer listing prices per distinct printing - not print-run-weighted
  circulating supply, which is unpublished.

## Methodology & Limitations

- **Print runs / circulation counts are not published** by either publisher.
  "Catalog size" counts distinct printed cards, not copies in circulation.
- **Prices are a cross-sectional snapshot** as of the collection date, not a
  time series. Appreciation figures compare release MSRP to current market —
  two points per set, not a price path.
- **WotC discontinued MSRP (~2019);** MTG "at release" prices are typical
  retail, hand-researched and cited. Pokémon MSRP is current and official.
- **Rarity tiers do not map 1:1 across games.** The mapping table used is
  disclosed in `data/README.md`; results are reported per-game and under the
  mapping separately.
- **Cards within a set are not independent observations.** Cross-game tests
  are reported with set-clustered bootstrap intervals alongside naive tests.
- TCGplayer "market price" is a listing-derived estimate, not transaction
  data.

## Live Viz

[link + screenshot after publish]
