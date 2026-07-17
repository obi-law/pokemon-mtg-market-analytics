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

## Findings

**Singles (matched window, card grain, n=4,971 MTG / 2,245 Pokemon)**

1. Card-for-card, MTG singles price modestly higher: median cheapest copy
   $0.29 vs $0.19; Cliff's delta 0.163 (set-clustered 95% CI 0.063-0.250),
   Hodges-Lehmann shift $0.06 (Holm-adj. p = 2.1e-28). The gap is
   statistically decisive but small - the typical card in either game is
   pocket change.
2. The games differ far more in where value sits than in what a typical
   card costs: Pokemon concentrates 93.5% of singles market value in its
   top rarity tier vs 71.2% for MTG (difference -0.223, set-clustered 95%
   CI [-0.37, -0.11]; robust to remapping ACE SPEC Rare, -0.220).
3. Both rarity ladders are statistically real: all 6 MTG tier pairs
   distinct (Dunn's, Holm); 32/55 Pokemon pairs, with adjacent premium
   tiers overlapping.
4. Results are stable across set-age strata (delta 0.155 early / 0.164
   late) and across the finish-grain choice; including all finishes
   widens the gap (delta 0.259), making cheapest-copy the conservative
   primary grain.

**Sealed (15 sets per game, single pack, launch price vs 2026-07-15 market)**

5. Complete separation: every Pokemon set trades above launch
   (1.35x-3.50x) while 12 of 15 MTG sets trade at or below (0.57x-1.27x).
   Median total return 2.30x vs 0.90x (Mann-Whitney U=0, Holm-adj.
   p = 3.4e-06; n=15/15, estimates emphasized over the test). Robust to
   excluding sets under 6 months old (medians 2.37x vs 0.98x).
6. Pricing strategy shows up in returns: four of five $6.99 Universes
   Beyond sets trade 0.57x-0.72x launch (Final Fantasy, 1.27x, is the
   exception), while TPCi's flat $4.49 MSRP means all Pokemon return
   dispersion is market-generated - specials cluster at 3.0x-3.5x.
7. Age gradients run in opposite directions: MTG sealed returns improve
   with age (Spearman rho=0.73) as young sets sell below launch and
   drift back; Pokemon annualized returns are highest for the youngest
   sets (rho=-0.82). Caveat: annualizing short holding periods
   mechanically amplifies both extremes (see methodology).

<!-- methodology additions -->
- Sealed comparison is single-pack grain: TCGplayer Market Price
  (2026-07-15) vs launch price per set. MKM/OTJ predate WotC's MSRP
  reinstatement and use TCGplayer Mid via MTGGoldfish on BOTH sides
  (market_at_release basis, matched metric); all launch-price bases
  (official_msrp, wotc_stated_equivalent, imputed_from_bundle,
  market_at_release) are recorded per set with citations in
  data/msrp_sources.csv.
- Pokemon special sets without standalone retail packs impute pack MSRP
  from the 6-pack Booster Bundle list price (26.94 / 6 = 4.49).
- me4 (Chaos Rising) postdates the latest found MSRP confirmation by
  ~2 months; no increase was reported as of collection.
- CAGR annualizes short holding periods and mechanically amplifies
  young-set returns in both directions; per-set total returns are
  reported alongside, and headline sealed results are checked against
  a >=6-month minimum-age sensitivity.
- Sealed n=15 per game is underpowered for formal testing; effect
  estimates are emphasized over p-values.

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
