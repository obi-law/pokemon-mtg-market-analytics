"""Fetch MTG sets, cards, and current TCGplayer price snapshot from MTGJSON.

Cohort: the 15 play-booster-era sets matching mtg-commercial-analytics
(MKM 2024-02-09 -> MSH 2026-06-26). Card catalogs come from per-set JSON
files (small); the price snapshot streams from AllPricesToday.json.gz via
ijson, filtered to cohort card uuids.

Outputs (under DATA_DIR/raw/):
  mtg_sets.csv          cohort set metadata
  mtg_cards.parquet     card-grain catalog for the cohort
  mtg_prices.parquet    card-finish-grain TCGplayer retail snapshot
"""

from __future__ import annotations

import argparse
import gzip
import os
import sys
import time
from datetime import date
from pathlib import Path

import ijson
import pandas as pd
import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

MTGJSON_BASE = "https://mtgjson.com/api/v5"
MAX_RETRIES = 5
TIMEOUT_S = 120

from cohorts import MTG_COHORT as COHORT


def get_with_retry(url: str, stream: bool = False) -> requests.Response:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=TIMEOUT_S, stream=stream)
            if resp.status_code == 200:
                return resp
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = 2 ** attempt
                print(f"  HTTP {resp.status_code}, retry {attempt}/{MAX_RETRIES} "
                      f"in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                raise
            wait = 2 ** attempt
            print(f"  {exc!r}, retry {attempt}/{MAX_RETRIES} in {wait}s",
                  file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Exhausted retries for {url}")


def fetch_set_list(codes: list[str]) -> pd.DataFrame:
    print("Fetching SetList.json ...")
    payload = get_with_retry(f"{MTGJSON_BASE}/SetList.json").json()
    wanted = {c.upper() for c in codes}
    rows = [{
        "set_code": s.get("code"),
        "set_name": s.get("name"),
        "release_date": s.get("releaseDate"),
        "set_type": s.get("type"),
        "base_set_size": s.get("baseSetSize"),
        "total_set_size": s.get("totalSetSize"),
    } for s in payload.get("data", []) if s.get("code", "").upper() in wanted]
    df = pd.DataFrame(rows).sort_values("release_date").reset_index(drop=True)
    missing = wanted - set(df["set_code"].str.upper())
    if missing:
        print(f"WARNING: sets not found in SetList: {sorted(missing)}",
              file=sys.stderr)
    return df


def fetch_set_cards(code: str) -> list[dict]:
    payload = get_with_retry(f"{MTGJSON_BASE}/{code}.json").json()
    cards = payload.get("data", {}).get("cards", [])
    return [{
        "uuid": c.get("uuid"),
        "set_code": code,
        "card_name": c.get("name"),
        "number": c.get("number"),
        "rarity": c.get("rarity"),
        "finishes": "|".join(c.get("finishes") or []),
        "layout": c.get("layout"),
        "side": c.get("side"),
        "is_promo": bool(c.get("isPromo")),
    } for c in cards]


def download_prices_file(raw_dir: Path, skip_download: bool) -> Path:
    dest = raw_dir / "AllPricesToday.json.gz"
    if skip_download and dest.exists():
        print(f"Reusing existing {dest}")
        return dest
    print("Downloading AllPricesToday.json.gz (this is the big one) ...")
    resp = get_with_retry(f"{MTGJSON_BASE}/AllPricesToday.json.gz", stream=True)
    with open(dest, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=1 << 20):
            fh.write(chunk)
    print(f"  saved -> {dest} ({dest.stat().st_size / 1e6:.1f} MB)")
    return dest


def stream_prices(prices_path: Path, cohort_uuids: set[str],
                  fetched_at: str) -> pd.DataFrame:
    """Stream AllPricesToday, keeping tcgplayer paper retail for cohort uuids."""
    rows = []
    with gzip.open(prices_path, "rb") as fh:
        for uuid, entry in ijson.kvitems(fh, "data"):
            if uuid not in cohort_uuids:
                continue
            tcg = ((entry.get("paper") or {}).get("tcgplayer") or {})
            retail = tcg.get("retail") or {}
            for finish in ("normal", "foil", "etched"):
                for price_date, price in (retail.get(finish) or {}).items():
                    rows.append({
                        "uuid": uuid,
                        "finish": finish,
                        "price_usd": float(price),
                        "price_date": price_date,
                        "provider": "tcgplayer_retail",
                        "fetched_at": fetched_at,
                    })
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--set-codes", type=str, default=",".join(COHORT),
                    help="comma-separated set codes (default: the 15-set cohort)")
    ap.add_argument("--skip-download", action="store_true",
                    help="reuse an already-downloaded AllPricesToday.json.gz")
    ap.add_argument("--out-dir", type=str, default="",
                    help="override output dir (default DATA_DIR or ./data)")
    args = ap.parse_args()

    data_dir = Path(args.out_dir) if args.out_dir else \
        Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    codes = [c.strip().upper() for c in args.set_codes.split(",") if c.strip()]
    fetched_at = date.today().isoformat()

    sets_df = fetch_set_list(codes)
    sets_out = raw_dir / "mtg_sets.csv"
    sets_df.to_csv(sets_out, index=False)
    print(f"Wrote {len(sets_df)} sets -> {sets_out}")

    all_rows = []
    for code in codes:
        print(f"Fetching cards for {code} ...")
        rows = fetch_set_cards(code)
        print(f"  {len(rows)} cards")
        all_rows.extend(rows)
    cards_df = pd.DataFrame(all_rows)
    cards_out = raw_dir / "mtg_cards.parquet"
    cards_df.to_parquet(cards_out, index=False)

    prices_path = download_prices_file(raw_dir, args.skip_download)
    print("Streaming price snapshot (ijson) ...")
    prices_df = stream_prices(prices_path, set(cards_df["uuid"]), fetched_at)
    prices_out = raw_dir / "mtg_prices.parquet"
    prices_df.to_parquet(prices_out, index=False)

    # --- verification summary -------------------------------------------
    print("\n=== Verification ===")
    print(f"Cards:  {len(cards_df):>6} -> {cards_out}")
    print(f"Prices: {len(prices_df):>6} -> {prices_out}")
    priced_uuids = set(prices_df["uuid"]) if not prices_df.empty else set()
    cards_df["has_price"] = cards_df["uuid"].isin(priced_uuids)
    summary = (cards_df.groupby("set_code")
               .agg(cards=("uuid", "count"), priced=("has_price", "sum"))
               .assign(pct_priced=lambda d: (100 * d.priced / d.cards).round(1))
               .reindex(codes))
    print("\nCards per set (catalog vs priced):")
    print(summary.to_string())
    if not prices_df.empty:
        print(f"\nprice_date values in snapshot: "
              f"{sorted(prices_df['price_date'].unique())}")
    print("\nCross-check: mtg_sets.csv total_set_size should be >= the "
          "catalog card count per set (MTGJSON counts include variants).")


if __name__ == "__main__":
    main()