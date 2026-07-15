"""Build matched cross-game singles-price analysis tables.

Inputs  (data/raw/):   pokemon_cards.parquet, pokemon_prices.parquet,
                       pokemon_sets_all.csv, mtg_cards.parquet,
                       mtg_prices.parquet, mtg_sets.csv
Reference (committed): reference/rarity_mapping.csv
                       columns: game, rarity_raw, tier_mapped, tier_order
                       The build FAILS LOUDLY if any rarity value in the
                       data is missing from the mapping - no silent drops.

Outputs (data/processed/):
  singles_prices.csv                    card grain, cheapest available
                                        finish, fresh rows only (Tableau +
                                        stats input; row-level, no ratios)
  singles_prices_all_finishes.parquet   card-finish grain (sensitivity)

Modes:
  --rarities-only    print distinct rarity values per game and exit
                     (used to ground the rarity mapping in real data)

Scope constants (see README methodology):
  FRESH_DAYS       drop price rows with tcgplayer_updated_at older than
                   this many days before the fetch date (Pokemon side)
  PRICE_WINDOW_END matched sub-window for cross-game price analyses -
                   Pokemon coverage ends at me2 (2025-11-14), so the MTG
                   sample is trimmed to the same window to avoid
                   confounding by set age
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

FRESH_DAYS = 14
PRICE_WINDOW_END = "2025-11-30"
RARITY_MAP_PATH = PROJECT_ROOT / "reference" / "rarity_mapping.csv"


def load_pokemon(raw: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    cards = pd.read_parquet(raw / "pokemon_cards.parquet")
    prices = pd.read_parquet(raw / "pokemon_prices.parquet")
    sets_all = pd.read_csv(raw / "pokemon_sets_all.csv",
                           parse_dates=["release_date"])

    # freshness filter
    prices["updated_dt"] = pd.to_datetime(
        prices["tcgplayer_updated_at"], format="%Y/%m/%d", errors="coerce")
    fetch_dt = pd.to_datetime(prices["fetched_at"]).max()
    stale = (fetch_dt - prices["updated_dt"]).dt.days > FRESH_DAYS
    n_stale = int(stale.sum())
    prices = prices[~stale].copy()

    # price per row: market, mid as guarded fallback
    n_fallback = int(prices["price_market"].isna().sum())
    prices["price_usd"] = prices["price_market"].fillna(prices["price_mid"])

    df = (prices.merge(cards[["card_id", "card_name", "set_name"]],
                       on="card_id", how="left")
                .merge(sets_all[["set_id", "release_date"]],
                       on="set_id", how="left"))
    df["game"] = "pokemon"
    df = df.rename(columns={"card_id": "card_key", "set_id": "set_code",
                            "rarity": "rarity_raw"})
    print(f"pokemon: dropped {n_stale} stale price rows; "
          f"{n_fallback} market-null rows used mid price")
    return df[["game", "set_code", "set_name", "release_date", "card_key",
               "card_name", "rarity_raw", "finish", "price_usd",
               "fetched_at"]], cards


def load_mtg(raw: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    cards = pd.read_parquet(raw / "mtg_cards.parquet")
    prices = pd.read_parquet(raw / "mtg_prices.parquet")
    sets = pd.read_csv(raw / "mtg_sets.csv", parse_dates=["release_date"])

    n_promo = int(cards["is_promo"].sum())
    cards_np = cards[~cards["is_promo"]].copy()

    # multi-face cards: MTGJSON gives each face its own uuid pointing at the
    # same physical product - keep face 'a' only to avoid double-counting
    face_b = cards_np["side"].notna() & (cards_np["side"] != "a")
    n_faces = int(face_b.sum())
    cards_np = cards_np[~face_b].copy()

    df = (prices.merge(cards_np[["uuid", "set_code", "card_name", "number",
                                 "rarity"]],
                       on="uuid", how="inner")
                .merge(sets[["set_code", "set_name", "release_date"]],
                       on="set_code", how="left"))
    df["game"] = "mtg"
    df = df.rename(columns={"uuid": "card_key", "rarity": "rarity_raw"})
    print(f"mtg: excluded {n_promo} isPromo card(s) "
          f"({len(prices) - len(df)} price rows dropped by promo/join filter)"
          f"; dropped {n_faces} non-primary faces")
    return df[["game", "set_code", "set_name", "release_date", "card_key",
               "card_name", "rarity_raw", "finish", "price_usd",
               "fetched_at"]], cards_np


def apply_rarity_mapping(df: pd.DataFrame) -> pd.DataFrame:
    if not RARITY_MAP_PATH.exists():
        sys.exit(f"ERROR: {RARITY_MAP_PATH} not found. Run with "
                 "--rarities-only first and build the mapping file.")
    mapping = pd.read_csv(RARITY_MAP_PATH)
    out = df.merge(mapping, how="left", on=["game", "rarity_raw"])
    unmapped = (out[out["tier_mapped"].isna()]
                [["game", "rarity_raw"]].drop_duplicates())
    if not unmapped.empty:
        print("\nERROR: unmapped rarity values - add these to "
              f"{RARITY_MAP_PATH.name} and re-run:", file=sys.stderr)
        print(unmapped.to_string(index=False), file=sys.stderr)
        sys.exit(1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rarities-only", action="store_true")
    ap.add_argument("--out-dir", type=str, default="",
                    help="override data dir (default DATA_DIR or ./data)")
    args = ap.parse_args()

    data_dir = Path(args.out_dir) if args.out_dir else \
        Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
    raw = data_dir / "raw"
    processed = data_dir / "processed"
    processed.mkdir(parents=True, exist_ok=True)

    pk, pk_cards = load_pokemon(raw)
    mt, _ = load_mtg(raw)

    if args.rarities_only:
        print("\n=== Distinct rarity values (price-bearing rows) ===")
        for name, df in (("POKEMON", pk), ("MTG", mt)):
            counts = (df.drop_duplicates("card_key")
                        .groupby("rarity_raw", dropna=False)
                        .size().sort_values(ascending=False))
            print(f"\n{name} ({len(counts)} distinct):")
            print(counts.to_string())
        return

    both = pd.concat([pk, mt], ignore_index=True)
    both = apply_rarity_mapping(both)

    # matched price sub-window flag + set age at snapshot
    fetch_dt = pd.to_datetime(both["fetched_at"]).max()
    both["set_age_days"] = (fetch_dt - both["release_date"]).dt.days
    both["in_price_window"] = both["release_date"] <= PRICE_WINDOW_END

    # release_event_id: same game + same release date = one release event
    events = (both[["game", "release_date"]].drop_duplicates()
              .sort_values(["game", "release_date"]).reset_index(drop=True))
    events["release_event_id"] = (events["game"] + "_"
                                  + events["release_date"].dt.strftime("%Y%m%d"))
    both = both.merge(events, on=["game", "release_date"], how="left")

    # all-finishes sensitivity grain
    all_out = processed / "singles_prices_all_finishes.parquet"
    both.to_parquet(all_out, index=False)

    # primary grain: cheapest available finish per card
    idx = both.groupby("card_key")["price_usd"].idxmin()
    cheapest = both.loc[idx].rename(columns={"finish": "finish_used"})
    csv_out = processed / "singles_prices.csv"
    cheapest.drop(columns=["fetched_at"]).to_csv(csv_out, index=False)

    # --- verification -----------------------------------------------------
    print("\n=== Verification ===")
    print(f"All-finishes rows: {len(both):>6} -> {all_out}")
    print(f"Card-grain rows:   {len(cheapest):>6} -> {csv_out}")
    win = cheapest[cheapest["in_price_window"]]
    print("\nIn matched price window "
          f"(release <= {PRICE_WINDOW_END}):")
    print(win.groupby("game").agg(
        cards=("card_key", "count"),
        sets=("set_code", "nunique"),
        min_price=("price_usd", "min"),
        median_price=("price_usd", "median"),
        max_price=("price_usd", "max"),
    ).round(2).to_string())
    print("\nCards by tier (window, cross-tab):")
    print(pd.crosstab(win["tier_mapped"], win["game"]).to_string())
    print("\nSets excluded from price window (catalog/sealed analyses only):")
    excl = (cheapest[~cheapest["in_price_window"]]
            [["game", "set_code", "set_name"]].drop_duplicates())
    print(excl.to_string(index=False) if not excl.empty else "  (none)")
    # cross-check: pokemon card-grain count should equal distinct priced
    # card_ids in raw prices minus stale-only cards
    n_pk_expected = pk["card_key"].nunique()
    n_pk_built = (cheapest["game"] == "pokemon").sum()
    status = "OK" if n_pk_expected == n_pk_built else "MISMATCH - investigate"
    print(f"\nCross-check pokemon card grain: raw distinct priced cards "
          f"{n_pk_expected} vs built {n_pk_built} [{status}]")


if __name__ == "__main__":
    main()