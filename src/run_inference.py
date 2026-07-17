"""Statistical inference suite for the cross-game singles analysis.

Input:  data/processed/singles_prices.csv (card grain, cheapest finish)
        data/processed/singles_prices_all_finishes.parquet (sensitivity)
        data/sealed_prices.csv + data/msrp_sources.csv (H3; auto-skipped
        with a notice until collection is complete)

Output: data/processed/inference_results.csv (tidy: analysis, metric, value)
        data/processed/dunn_mtg.csv, dunn_pokemon.csv (post-hoc matrices)

Design (pre-registered in conversation before results were seen):
  H1  Cross-game price distributions (window, card grain): Mann-Whitney U,
      Cliff's delta, Hodges-Lehmann shift, medians; set-clustered bootstrap
      CIs alongside the naive test (cards within a set are not independent).
  H2a Within-game rarity effect (raw tiers): Kruskal-Wallis + Dunn's
      post-hoc (Holm), per game.
  H2b Cross-game value concentration: share of summed market value in the
      'top' tier per game, clustered bootstrap CI on the difference.
  H3  Sealed appreciation since release: annualized return from MSRP to
      market per set; MWU across games (n=15/15 - underpowered, estimates
      emphasized over p); Spearman (set age vs return) per game.
  Family-wise Holm correction across primary p-values {H1, H2a-mtg,
      H2a-pokemon} (+ H3 when available).
  Sensitivities: (A) age-stratified H1 (validates the window trim),
      (B) ACE SPEC Rare reassigned to 'rare' (mapping judgment check),
      (C) H1 on the all-finishes grain (grain-choice check).

Rank tests are scale-invariant, so no log transform is applied for
testing; medians are reported in raw USD.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scikit_posthocs as sp
from scipy.stats import kruskal, mannwhitneyu, spearmanr

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEED = 2026
N_BOOT = 2000

RESULTS: list[dict] = []


def record(analysis: str, metric: str, value) -> None:
    RESULTS.append({"analysis": analysis, "metric": metric, "value": value})


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    u = mannwhitneyu(x, y, alternative="two-sided").statistic
    return 2.0 * u / (len(x) * len(y)) - 1.0


def hodges_lehmann(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.median(np.subtract.outer(x, y)))


def replicate_stats(df: pd.DataFrame) -> dict:
    m = df.loc[df["game"] == "mtg", "price_usd"].to_numpy()
    p = df.loc[df["game"] == "pokemon", "price_usd"].to_numpy()
    top_share = (df[df["tier_mapped"] == "top"].groupby("game")["price_usd"].sum()
                 / df.groupby("game")["price_usd"].sum())
    return {
        "median_diff_usd": float(np.median(m) - np.median(p)),
        "cliffs_delta": cliffs_delta(m, p),
        "top_share_mtg": float(top_share.get("mtg", np.nan)),
        "top_share_pokemon": float(top_share.get("pokemon", np.nan)),
        "top_share_diff": float(top_share.get("mtg", np.nan)
                                - top_share.get("pokemon", np.nan)),
    }


def clustered_bootstrap(win: pd.DataFrame, rng: np.random.Generator,
                        n_boot: int = N_BOOT) -> pd.DataFrame:
    groups = {g: dict(tuple(gdf.groupby("set_code")))
              for g, gdf in win.groupby("game")}
    reps = []
    for _ in range(n_boot):
        parts = []
        for sets in groups.values():
            keys = list(sets)
            for k in rng.choice(keys, size=len(keys), replace=True):
                parts.append(sets[k])
        reps.append(replicate_stats(pd.concat(parts, ignore_index=True)))
    return pd.DataFrame(reps)


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    adj, running = {}, 0.0
    for i, (name, p) in enumerate(items):
        running = max(running, (m - i) * p)
        adj[name] = min(1.0, running)
    return adj


def run_h1(win: pd.DataFrame, rng: np.random.Generator) -> float:
    print("\n=== H1: cross-game price distributions (window, card grain) ===")
    m = win.loc[win["game"] == "mtg", "price_usd"].to_numpy()
    p = win.loc[win["game"] == "pokemon", "price_usd"].to_numpy()
    res = mannwhitneyu(m, p, alternative="two-sided")
    delta = cliffs_delta(m, p)
    hl = hodges_lehmann(m, p)
    print(f"n: mtg={len(m)}, pokemon={len(p)}")
    print(f"median: mtg=${np.median(m):.2f}, pokemon=${np.median(p):.2f}")
    print(f"Mann-Whitney U={res.statistic:.0f}, p={res.pvalue:.3g}")
    print(f"Cliff's delta={delta:.3f} (positive = mtg stochastically higher)")
    print(f"Hodges-Lehmann shift=${hl:.2f}")
    for k, v in (("n_mtg", len(m)), ("n_pokemon", len(p)),
                 ("median_mtg", float(np.median(m))),
                 ("median_pokemon", float(np.median(p))),
                 ("mwu_p", float(res.pvalue)), ("cliffs_delta", delta),
                 ("hodges_lehmann_usd", hl)):
        record("H1", k, v)

    print(f"\nSet-clustered bootstrap ({N_BOOT} reps, resampling sets)...")
    boot = clustered_bootstrap(win, rng)
    for col in ("median_diff_usd", "cliffs_delta",
                "top_share_mtg", "top_share_pokemon", "top_share_diff"):
        lo, hi = np.percentile(boot[col], [2.5, 97.5])
        tag = "H1" if "share" not in col else "H2b"
        record(tag, f"{col}_ci_lo", float(lo))
        record(tag, f"{col}_ci_hi", float(hi))
        print(f"  {col}: 95% CI [{lo:.3f}, {hi:.3f}]")
    return float(res.pvalue)


def run_h2a(win: pd.DataFrame, processed: Path) -> dict[str, float]:
    print("\n=== H2a: within-game rarity effect (raw tiers) ===")
    pvals = {}
    for game, gdf in win.groupby("game"):
        groups = [d["price_usd"].to_numpy()
                  for _, d in gdf.groupby("rarity_raw")]
        stat, p = kruskal(*groups)
        pvals[f"H2a_{game}"] = float(p)
        print(f"{game}: Kruskal-Wallis H={stat:.1f}, p={p:.3g}, "
              f"tiers={gdf['rarity_raw'].nunique()}")
        record(f"H2a_{game}", "kw_H", float(stat))
        record(f"H2a_{game}", "kw_p", float(p))
        dunn = sp.posthoc_dunn(gdf, val_col="price_usd",
                               group_col="rarity_raw", p_adjust="holm")
        out = processed / f"dunn_{game}.csv"
        dunn.to_csv(out)
        n_pairs = dunn.shape[0] * (dunn.shape[0] - 1) // 2
        n_sig = int((dunn.values[np.triu_indices_from(dunn.values, 1)] < 0.05).sum())
        print(f"  Dunn's (Holm): {n_sig}/{n_pairs} pairs significant "
              f"at 0.05 -> {out.name}")
        record(f"H2a_{game}", "dunn_sig_pairs", n_sig)
        record(f"H2a_{game}", "dunn_total_pairs", n_pairs)
    return pvals


def run_h2b_point(win: pd.DataFrame, label: str = "H2b") -> None:
    print(f"\n=== {label}: value concentration in 'top' tier ===")
    stats = replicate_stats(win)
    for k in ("top_share_mtg", "top_share_pokemon", "top_share_diff"):
        record(label, k, stats[k])
        print(f"  {k}: {stats[k]:.3f}")


def run_h3(data_dir: Path) -> float | None:
    sealed_p = data_dir / "sealed_prices.csv"
    msrp_p = data_dir / "msrp_sources.csv"
    if not (sealed_p.exists() and msrp_p.exists()):
        print("\n=== H3: sealed appreciation - SKIPPED "
              "(collection files not found) ===")
        return None
    sealed = pd.read_csv(sealed_p, parse_dates=["release_date",
                                                "collected_date"])
    msrp = pd.read_csv(msrp_p)
    if sealed["tcgplayer_market_usd"].isna().any() or \
       msrp["msrp_usd"].isna().any():
        print("\n=== H3: sealed appreciation - SKIPPED "
              "(collection incomplete: blank prices/MSRPs remain) ===")
        return None

    df = sealed.merge(msrp[["game", "set_code", "msrp_usd", "msrp_basis"]],
                      on=["game", "set_code"], how="inner", validate="1:1")
    if len(df) != len(sealed):
        sys.exit("ERROR: sealed/msrp join lost rows - check set codes.")
    print("\n=== H3: sealed appreciation since release ===")
    df["years"] = (df["collected_date"] - df["release_date"]).dt.days / 365.25
    df["total_return"] = df["tcgplayer_market_usd"] / df["msrp_usd"]
    df["cagr"] = df["total_return"] ** (1 / df["years"]) - 1

    cols = ["game", "set_code", "msrp_usd", "tcgplayer_market_usd",
            "years", "total_return", "cagr"]
    print(df[cols].sort_values(["game", "cagr"]).round(3).to_string(index=False))

    m = df.loc[df["game"] == "mtg", "cagr"].to_numpy()
    p = df.loc[df["game"] == "pokemon", "cagr"].to_numpy()
    res = mannwhitneyu(m, p, alternative="two-sided")
    print(f"\nmedian CAGR: mtg={np.median(m):.1%}, pokemon={np.median(p):.1%}")
    print(f"Mann-Whitney U={res.statistic:.0f}, p={res.pvalue:.3g} "
          f"(n=15/15 - underpowered; emphasize estimates)")
    record("H3", "median_cagr_mtg", float(np.median(m)))
    record("H3", "median_cagr_pokemon", float(np.median(p)))
    record("H3", "mwu_p", float(res.pvalue))
    for game, arr in (("mtg", None), ("pokemon", None)):
        sub = df[df["game"] == game]
        rho, sp_p = spearmanr(sub["years"], sub["cagr"])
        print(f"Spearman(age, cagr) {game}: rho={rho:.2f}, p={sp_p:.3g}")
        record("H3", f"spearman_rho_{game}", float(rho))
        record("H3", f"spearman_p_{game}", float(sp_p))
    df.to_csv(data_dir / "processed" / "sealed_returns.csv", index=False)
    return float(res.pvalue)


def sensitivity_age_strata(win: pd.DataFrame) -> None:
    print("\n=== Sensitivity A: age-stratified H1 ===")
    strata = {}
    for game, gdf in win.groupby("game"):
        order = (gdf[["set_code", "release_date"]].drop_duplicates()
                 .sort_values("release_date"))
        half = len(order) // 2
        early = set(order["set_code"].iloc[:half])
        strata[game] = early
    win = win.copy()
    win["stratum"] = [
        "early" if r.set_code in strata[r.game] else "late"
        for r in win.itertuples()
    ]
    for stratum, sdf in win.groupby("stratum"):
        m = sdf.loc[sdf["game"] == "mtg", "price_usd"].to_numpy()
        p = sdf.loc[sdf["game"] == "pokemon", "price_usd"].to_numpy()
        res = mannwhitneyu(m, p, alternative="two-sided")
        d = cliffs_delta(m, p)
        print(f"{stratum}: n=({len(m)},{len(p)}) "
              f"medians=(${np.median(m):.2f},${np.median(p):.2f}) "
              f"delta={d:.3f} p={res.pvalue:.3g}")
        record("sensA_age", f"{stratum}_cliffs_delta", d)
        record("sensA_age", f"{stratum}_mwu_p", float(res.pvalue))


def sensitivity_ace_spec(win: pd.DataFrame) -> None:
    print("\n=== Sensitivity B: ACE SPEC Rare -> 'rare' ===")
    alt = win.copy()
    alt.loc[alt["rarity_raw"] == "ACE SPEC Rare", "tier_mapped"] = "rare"
    run_h2b_point(alt, label="sensB_ace_spec")


def sensitivity_all_finishes(processed: Path) -> None:
    print("\n=== Sensitivity C: H1 on all-finishes grain ===")
    allf = pd.read_parquet(processed / "singles_prices_all_finishes.parquet")
    allf = allf[allf["in_price_window"]]
    m = allf.loc[allf["game"] == "mtg", "price_usd"].to_numpy()
    p = allf.loc[allf["game"] == "pokemon", "price_usd"].to_numpy()
    res = mannwhitneyu(m, p, alternative="two-sided")
    d = cliffs_delta(m, p)
    print(f"n=({len(m)},{len(p)}) "
          f"medians=(${np.median(m):.2f},${np.median(p):.2f}) "
          f"delta={d:.3f} p={res.pvalue:.3g}")
    record("sensC_all_finishes", "cliffs_delta", d)
    record("sensC_all_finishes", "mwu_p", float(res.pvalue))


def sensitivity_min_age(data_dir: Path, min_years: float = 0.5) -> None:
    print(f"\n=== Sensitivity D: sealed, sets >= {min_years}y old only ===")
    df = pd.read_csv(data_dir / "processed" / "sealed_returns.csv")
    old = df[df["years"] >= min_years]
    med = old.groupby("game")[["total_return", "cagr"]].median().round(3)
    print(f"sets retained: {old.groupby('game').size().to_dict()}")
    print(med.to_string())
    for k, v in med.to_dict("index").items():
        record("sensD_min_age", f"median_total_return_{k}", v["total_return"])
        record("sensD_min_age", f"median_cagr_{k}", v["cagr"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=str, default="",
                    help="override data dir (default DATA_DIR or ./data)")
    args = ap.parse_args()

    data_dir = Path(args.out_dir) if args.out_dir else \
        Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
    processed = data_dir / "processed"
    rng = np.random.default_rng(SEED)

    df = pd.read_csv(processed / "singles_prices.csv",
                     parse_dates=["release_date"])
    win = df[df["in_price_window"]].copy()

    # eyeball QA: extreme values must correspond to known chase cards
    print("=== Eyeball QA: top 10 priciest per game (window) ===")
    for game, gdf in win.groupby("game"):
        top10 = gdf.nlargest(10, "price_usd")[
            ["set_code", "card_name", "rarity_raw", "finish_used", "price_usd"]]
        print(f"\n{game}:")
        print(top10.to_string(index=False))

    primary_p = {"H1": run_h1(win, rng)}
    primary_p.update(run_h2a(win, processed))
    run_h2b_point(win)
    h3_p = run_h3(data_dir)
    if h3_p is not None:
        primary_p["H3"] = h3_p

    sensitivity_age_strata(win)
    sensitivity_ace_spec(win)
    sensitivity_all_finishes(processed)
    if h3_p is not None:
        sensitivity_min_age(data_dir)

    print("\n=== Holm correction (primary family) ===")
    for name, p_adj in holm(primary_p).items():
        print(f"  {name}: raw p={primary_p[name]:.3g} -> "
              f"holm-adjusted p={p_adj:.3g}")
        record("holm", name, p_adj)

    out = processed / "inference_results.csv"
    pd.DataFrame(RESULTS).to_csv(out, index=False)
    print(f"\nWrote {len(RESULTS)} result rows -> {out}")


if __name__ == "__main__":
    main()