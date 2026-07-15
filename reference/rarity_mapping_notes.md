# Rarity mapping — rationale

Four-tier cross-game ladder used only for cross-game comparisons; all
within-game analyses use each game's raw rarity tiers untouched.

## Principle

Tiers align by **slot role within each game's own pack structure**, not by
cross-game pull-rate equivalence (which does not exist):

| tier_order | tier_mapped | MTG | Pokemon |
|---|---|---|---|
| 1 | common | common | Common |
| 2 | uncommon | uncommon | Uncommon |
| 3 | rare | rare | Rare, Double Rare |
| 4 | top | mythic | Illustration Rare, Ultra Rare, Special Illustration Rare, Hyper Rare, Mega Hyper Rare, Black White Rare, ACE SPEC Rare |

- `rare` = baseline outcomes of the pack's rare slot.
- `top` = premium/chase tiers above the baseline slot.

## Interpretation constraint (also in dashboard methodology footer)

Cross-game tier results measure **where value concentrates within each
game's own rarity ladder**. They do not assert that a Pokemon `top` and an
MTG `top` have equal scarcity.

## Flagged judgment call

`ACE SPEC Rare` -> `top` (n=33). Mechanically distinct (deck-restricted)
rather than art-chase; an argument exists for `rare`. The inference suite
includes a sensitivity rerun with ACE SPEC reassigned to `rare`.

Mapping grounded in observed rarity values from the 2026-07-15 fetch
(11 distinct Pokemon tiers, 4 MTG) - not assumed from memory.
