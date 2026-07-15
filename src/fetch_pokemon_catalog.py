"""Fetch Pokemon TCG sets, cards, and current TCGplayer price snapshot.

Data source: Pokemon TCG API v2 (https://docs.pokemontcg.io), key via .env.

Two modes:
  --sets-only            Fetch all sets, print the release-window candidate
                         cohort for approval, write the full set list.
  --set-ids sv8,sv9,...  Fetch cards + prices for the approved cohort.

Outputs (under DATA_DIR/raw/):
  pokemon_sets_all.csv      every set the API knows, with release dates
  pokemon_cards.parquet     card-grain catalog for the cohort
  pokemon_prices.parquet    card-finish-grain TCGplayer snapshot
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

API_BASE = "https://api.pokemontcg.io/v2"
PAGE_SIZE = 250
MAX_RETRIES = 5
TIMEOUT_S = 60

# Matched to the MTG play-booster cohort window (MKM 2024-02-09 -> MSH 2026-06-26)
DEFAULT_WINDOW_START = "2024-02-01"
DEFAULT_WINDOW_END = "2026-06-30"


def make_session() -> requests.Session:
    s = requests.Session()
    key = os.getenv("POKEMONTCG_API_KEY", "").strip()
    if key and key != "your_key_here":
        s.headers["X-Api-Key"] = key
    else:
        print("WARNING: no POKEMONTCG_API_KEY in .env - using keyless "
              "rate limits (slow).", file=sys.stderr)
    return s


def get_json(session: requests.Session, url: str, params: dict | None = None) -> dict:
    """GET with retry/backoff on 429 and 5xx."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=TIMEOUT_S)
            if resp.status_code == 200:
                return resp.json()
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


def fetch_all_sets(session: requests.Session) -> pd.DataFrame:
    rows, page = [], 1
    while True:
        payload = get_json(session, f"{API_BASE}/sets",
                           {"page": page, "pageSize": PAGE_SIZE})
        for s in payload.get("data", []):
            rows.append({
                "set_id": s.get("id"),
                "set_name": s.get("name"),
                "series": s.get("series"),
                "release_date": s.get("releaseDate"),  # YYYY/MM/DD
                "printed_total": s.get("printedTotal"),
                "total": s.get("total"),
                "ptcgo_code": s.get("ptcgoCode"),
            })
        if page * PAGE_SIZE >= payload.get("totalCount", 0):
            break
        page += 1
    df = pd.DataFrame(rows)
    df["release_date"] = pd.to_datetime(df["release_date"], format="%Y/%m/%d",
                                        errors="coerce")
    return df.sort_values("release_date").reset_index(drop=True)


def fetch_cards_for_set(session: requests.Session, set_id: str) -> list[dict]:
    cards, page = [], 1
    while True:
        payload = get_json(session, f"{API_BASE}/cards",
                           {"q": f"set.id:{set_id}",
                            "page": page, "pageSize": PAGE_SIZE})
        cards.extend(payload.get("data", []))
        if page * PAGE_SIZE >= payload.get("totalCount", 0):
            break
        page += 1
    return cards


def flatten(cards: list[dict], fetched_at: str) -> tuple[list[dict], list[dict]]:
    """Split raw card JSON into catalog rows and card-finish price rows."""
    card_rows, price_rows = [], []
    for c in cards:
        tcg = c.get("tcgplayer") or {}
        card_rows.append({
            "card_id": c.get("id"),
            "card_name": c.get("name"),
            "supertype": c.get("supertype"),
            "subtypes": "|".join(c.get("subtypes") or []),
            "rarity": c.get("rarity"),
            "number": c.get("number"),
            "set_id": (c.get("set") or {}).get("id"),
            "set_name": (c.get("set") or {}).get("name"),
            "has_tcgplayer_price": bool(tcg.get("prices")),
        })
        for finish, p in (tcg.get("prices") or {}).items():
            price_rows.append({
                "card_id": c.get("id"),
                "set_id": (c.get("set") or {}).get("id"),
                "rarity": c.get("rarity"),
                "finish": finish,  # normal / holofoil / reverseHolofoil / ...
                "price_low": p.get("low"),
                "price_mid": p.get("mid"),
                "price_high": p.get("high"),
                "price_market": p.get("market"),
                "price_direct_low": p.get("directLow"),
                "tcgplayer_updated_at": tcg.get("updatedAt"),
                "fetched_at": fetched_at,
            })
    return card_rows, price_rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sets-only", action="store_true",
                    help="fetch set list and print window candidates only")
    ap.add_argument("--set-ids", type=str, default="",
                    help="comma-separated set ids for the approved cohort")
    ap.add_argument("--window-start", default=DEFAULT_WINDOW_START)
    ap.add_argument("--window-end", default=DEFAULT_WINDOW_END)
    ap.add_argument("--out-dir", type=str, default="",
                    help="override output dir (default DATA_DIR or ./data)")
    args = ap.parse_args()

    data_dir = Path(args.out_dir) if args.out_dir else \
        Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    session = make_session()
    fetched_at = date.today().isoformat()

    if args.sets_only or not args.set_ids:
        sets_df = fetch_all_sets(session)
        out = raw_dir / "pokemon_sets_all.csv"
        sets_df.to_csv(out, index=False)
        print(f"Wrote {len(sets_df)} sets -> {out}\n")

        win = sets_df[
            (sets_df["release_date"] >= args.window_start)
            & (sets_df["release_date"] <= args.window_end)
        ]
        print(f"=== Window candidates {args.window_start} .. {args.window_end} "
              f"({len(win)} sets) ===")
        cols = ["set_id", "set_name", "series", "release_date",
                "printed_total", "total"]
        print(win[cols].to_string(index=False))
        print("\nReview against the selection rule (main-series + major "
              "specials; exclude promo/mini sets), then rerun with "
              "--set-ids id1,id2,...")
        return

    set_ids = [s.strip() for s in args.set_ids.split(",") if s.strip()]
    all_card_rows, all_price_rows = [], []
    for sid in set_ids:
        print(f"Fetching cards for {sid} ...")
        cards = fetch_cards_for_set(session, sid)
        card_rows, price_rows = flatten(cards, fetched_at)
        print(f"  {len(card_rows)} cards, {len(price_rows)} price rows")
        all_card_rows.extend(card_rows)
        all_price_rows.extend(price_rows)

    cards_df = pd.DataFrame(all_card_rows)
    prices_df = pd.DataFrame(all_price_rows)

    cards_out = raw_dir / "pokemon_cards.parquet"
    prices_out = raw_dir / "pokemon_prices.parquet"
    cards_df.to_parquet(cards_out, index=False)
    prices_df.to_parquet(prices_out, index=False)

    # --- verification summary -------------------------------------------
    print("\n=== Verification ===")
    print(f"Cards:  {len(cards_df):>6} -> {cards_out}")
    print(f"Prices: {len(prices_df):>6} -> {prices_out}")
    print("\nCards per set (catalog vs priced):")
    summary = (cards_df.groupby("set_id")
               .agg(cards=("card_id", "count"),
                    priced=("has_tcgplayer_price", "sum"))
               .assign(pct_priced=lambda d: (100 * d.priced / d.cards).round(1)))
    print(summary.to_string())
    n_null_rarity = cards_df["rarity"].isna().sum()
    print(f"\nCards with null rarity: {n_null_rarity} "
          "(expected for some Energy cards - inspect before the rarity analysis)")
    if not prices_df.empty:
        print(f"Null market price rows: {prices_df['price_market'].isna().sum()}")
        print(f"tcgplayer_updated_at range: "
              f"{prices_df['tcgplayer_updated_at'].min()} .. "
              f"{prices_df['tcgplayer_updated_at'].max()}")


if __name__ == "__main__":
    main()