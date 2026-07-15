"""QA: per-set TCGplayer price coverage and freshness (Pokemon side).

Default mode reads data/raw/pokemon_cards.parquet + pokemon_prices.parquet
and reports, per set: card count, priced coverage, and the distribution of
tcgplayer_updated_at (min / max / distinct dates / share of rows older than
--stale-days relative to the fetch date).

--probe SET_ID hits the live API for a few cards from that set and prints
which price blocks actually exist on the raw JSON (tcgplayer vs cardmarket)
- used to distinguish "API has no price mapping yet" from "our flatten
missed something".
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_pokemon_catalog import make_session, get_json, API_BASE  # noqa: E402


def freshness_report(data_dir: Path, stale_days: int) -> None:
    cards = pd.read_parquet(data_dir / "raw" / "pokemon_cards.parquet")
    prices = pd.read_parquet(data_dir / "raw" / "pokemon_prices.parquet")

    prices["updated_dt"] = pd.to_datetime(
        prices["tcgplayer_updated_at"], format="%Y/%m/%d", errors="coerce")
    fetch_dt = pd.to_datetime(prices["fetched_at"]).max()
    prices["age_days"] = (fetch_dt - prices["updated_dt"]).dt.days
    prices["is_stale"] = prices["age_days"] > stale_days

    priced_ids = prices.groupby("set_id")["card_id"].nunique()
    upd = prices.groupby("set_id").agg(
        upd_min=("updated_dt", "min"),
        upd_max=("updated_dt", "max"),
        n_upd_dates=("updated_dt", "nunique"),
        pct_stale_rows=("is_stale", lambda s: round(100 * s.mean(), 1)),
    )
    cat = cards.groupby("set_id").agg(cards=("card_id", "count"))
    rpt = (cat.join(priced_ids.rename("priced_cards"))
              .join(upd)
              .fillna({"priced_cards": 0}))
    rpt["pct_priced"] = (100 * rpt["priced_cards"] / rpt["cards"]).round(1)
    rpt = rpt[["cards", "priced_cards", "pct_priced",
               "upd_min", "upd_max", "n_upd_dates", "pct_stale_rows"]]

    print(f"Fetch date: {fetch_dt.date()} | stale threshold: >{stale_days} days\n")
    print(rpt.sort_values("upd_min").to_string())

    stale_rows = prices[prices["is_stale"]]
    print(f"\nStale price rows total: {len(stale_rows)} "
          f"({100 * len(stale_rows) / len(prices):.1f}% of all price rows)")
    if not stale_rows.empty:
        print("Stale rows by set:")
        print(stale_rows.groupby("set_id").size().sort_values(ascending=False)
              .to_string())


def probe(set_id: str, n: int = 3) -> None:
    session = make_session()
    payload = get_json(session, f"{API_BASE}/cards",
                       {"q": f"set.id:{set_id}", "page": 1, "pageSize": n})
    data = payload.get("data", [])
    print(f"Probe {set_id}: totalCount={payload.get('totalCount')}, "
          f"showing {len(data)} cards\n")
    for c in data:
        tcg = c.get("tcgplayer")
        cm = c.get("cardmarket")
        print(f"- {c.get('id')} | {c.get('name')} | rarity={c.get('rarity')}")
        print(f"    top-level keys: {sorted(c.keys())}")
        if tcg:
            print(f"    tcgplayer: updatedAt={tcg.get('updatedAt')} "
                  f"finishes={sorted((tcg.get('prices') or {}).keys())}")
        else:
            print("    tcgplayer: ABSENT")
        if cm:
            print(f"    cardmarket: updatedAt={cm.get('updatedAt')} "
                  f"price_keys={sorted((cm.get('prices') or {}).keys())[:6]}...")
        else:
            print("    cardmarket: ABSENT")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stale-days", type=int, default=14)
    ap.add_argument("--probe", type=str, default="",
                    help="set id to probe against the live API (e.g. me4)")
    ap.add_argument("--out-dir", type=str, default="",
                    help="override data dir (default DATA_DIR or ./data)")
    args = ap.parse_args()

    if args.probe:
        probe(args.probe)
        return

    data_dir = Path(args.out_dir) if args.out_dir else \
        Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
    freshness_report(data_dir, args.stale_days)


if __name__ == "__main__":
    main()