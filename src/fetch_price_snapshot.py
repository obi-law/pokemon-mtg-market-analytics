"""Daily dated price snapshot for both games (the archive builder).

Writes DATA_DIR/snapshots/YYYY-MM-DD/:
  pokemon_prices.parquet    card-finish TCGplayer snapshot (API re-fetch)
  mtg_prices.parquet        card-finish TCGplayer retail (AllPricesToday)
  AllPricesToday.json.gz    raw MTGJSON file, kept for provenance (~5 MB)

Requires data/raw/mtg_cards.parquet to exist (run fetch_mtg_catalog.py once
first). Idempotent per day: exits early if today's snapshot is complete
unless --force. Safe to run from Task Scheduler regardless of working
directory (PROJECT_ROOT anchoring + explicit sys.path insert).
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv(PROJECT_ROOT / ".env")

from cohorts import POKEMON_COHORT  # noqa: E402
from fetch_pokemon_catalog import (  # noqa: E402
    make_session, fetch_cards_for_set, flatten,
)
from fetch_mtg_catalog import (  # noqa: E402
    download_prices_file, stream_prices,
)


def snapshot_pokemon(snap_dir: Path, fetched_at: str) -> pd.DataFrame:
    session = make_session()
    price_rows = []
    for sid in POKEMON_COHORT:
        print(f"  pokemon {sid} ...")
        cards = fetch_cards_for_set(session, sid)
        _, rows = flatten(cards, fetched_at)
        price_rows.extend(rows)
    df = pd.DataFrame(price_rows)
    df.to_parquet(snap_dir / "pokemon_prices.parquet", index=False)
    return df


def snapshot_mtg(snap_dir: Path, fetched_at: str) -> pd.DataFrame:
    cards_path = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data")) \
        / "raw" / "mtg_cards.parquet"
    if not cards_path.exists():
        sys.exit(f"ERROR: {cards_path} not found - run fetch_mtg_catalog.py "
                 "once before scheduling snapshots.")
    cohort_uuids = set(pd.read_parquet(cards_path, columns=["uuid"])["uuid"])
    gz_path = download_prices_file(snap_dir, skip_download=False)
    print("  streaming MTG snapshot (ijson) ...")
    df = stream_prices(gz_path, cohort_uuids, fetched_at)
    df.to_parquet(snap_dir / "mtg_prices.parquet", index=False)
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="re-fetch even if today's snapshot exists")
    ap.add_argument("--out-dir", type=str, default="",
                    help="override data dir (default DATA_DIR or ./data)")
    args = ap.parse_args()

    data_dir = Path(args.out_dir) if args.out_dir else \
        Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
    fetched_at = date.today().isoformat()
    snap_dir = data_dir / "snapshots" / fetched_at
    snap_dir.mkdir(parents=True, exist_ok=True)

    pk_out = snap_dir / "pokemon_prices.parquet"
    mt_out = snap_dir / "mtg_prices.parquet"
    if pk_out.exists() and mt_out.exists() and not args.force:
        print(f"Snapshot for {fetched_at} already complete "
              f"({snap_dir}) - use --force to re-fetch.")
        return

    print(f"Snapshot {fetched_at} -> {snap_dir}")
    pk_df = snapshot_pokemon(snap_dir, fetched_at)
    mt_df = snapshot_mtg(snap_dir, fetched_at)

    print("\n=== Snapshot summary ===")
    print(f"pokemon_prices: {len(pk_df):>6} rows | "
          f"null market: {pk_df['price_market'].isna().sum() if not pk_df.empty else 'n/a'}")
    print(f"mtg_prices:     {len(mt_df):>6} rows | "
          f"price_date(s): {sorted(mt_df['price_date'].unique()) if not mt_df.empty else 'n/a'}")
    n_days = len(list((data_dir / "snapshots").iterdir()))
    print(f"Archive now holds {n_days} snapshot day(s).")


if __name__ == "__main__":
    main()