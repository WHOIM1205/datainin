"""
Module 11 — trader segmentation.

Priority (per project rules): rule-based > quantile-based > clustering. Clustering is
only *evaluated* and adopted if it clearly beats simple segmentation. With just 32
accounts, interpretable rule/quantile segments are expected to dominate.

Every segment is: interpretable (a business label), reproducible (deterministic given
the data), and stable (fixed thresholds / rank quantiles — no random seeds).

No hypothesis testing, no recommendations — segment definitions only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Directional rule thresholds (rule-based segment).
LONG_HI, LONG_LO = 0.55, 0.45
# Accounts below this many active days have noisier metrics — flagged, not dropped.
LOW_ACTIVITY_DAYS = 10

# Metrics used for the clustering *evaluation* (interpretable behaviour/perf axes).
CLUSTER_FEATURES = ["roi_on_notional", "avg_trades_per_active_day",
                    "pct_profitable_days", "median_trade_size_usd", "long_ratio"]

SEGMENT_COLS = ["frequency_segment", "consistency_segment", "size_segment",
                "performance_segment", "directional_segment"]


def _qbin(s: pd.Series, q: int, labels: list[str]) -> pd.Series:
    """Rank-based quantile binning (balanced, deterministic)."""
    return pd.qcut(s.rank(method="first"), q, labels=labels)


def assign_segments(metrics: pd.DataFrame) -> pd.DataFrame:
    m = metrics.copy()
    # quantile-based (median splits / tertile) — balanced by construction
    m["frequency_segment"] = _qbin(m["avg_trades_per_active_day"], 2, ["Infrequent", "Frequent"])
    m["consistency_segment"] = _qbin(m["pct_profitable_days"], 2, ["Inconsistent", "Consistent"])
    m["size_segment"] = _qbin(m["median_trade_size_usd"], 2, ["Small", "Large"])
    m["performance_segment"] = _qbin(m["roi_on_notional"], 3, ["Bottom", "Mid", "Top"])
    # rule-based (fixed, interpretable thresholds)
    m["directional_segment"] = np.select(
        [m["long_ratio"] > LONG_HI, m["long_ratio"] < LONG_LO],
        ["Long-biased", "Short-biased"], default="Balanced")
    # data-quality caveat flag (not a segment)
    m["is_low_activity"] = m["n_active_days"] < LOW_ACTIVITY_DAYS
    return m


def segment_balance(seg: pd.DataFrame) -> dict:
    return {c: seg[c].value_counts().sort_index().to_dict() for c in SEGMENT_COLS}


def evaluate_clustering(metrics: pd.DataFrame, seed: int = 42) -> dict:
    """Evaluate KMeans on standardized features: silhouette per k, seed-stability (ARI),
    and overlap with the quantile performance segment. Returns a decision dict."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score, silhouette_score
    from sklearn.preprocessing import StandardScaler

    X = metrics[CLUSTER_FEATURES].copy()
    # log1p the heavy-tailed positive axes before scaling (E6), sign-safe
    for col in ["avg_trades_per_active_day", "median_trade_size_usd"]:
        X[col] = np.log1p(X[col].clip(lower=0))
    Xs = StandardScaler().fit_transform(X.fillna(X.median()))

    sils = {}
    for k in range(2, 6):
        labels = KMeans(k, n_init=10, random_state=seed).fit_predict(Xs)
        sils[k] = round(float(silhouette_score(Xs, labels)), 3)
    best_k = max(sils, key=sils.get)

    # seed stability of best_k: ARI across 10 seeds
    labelings = [KMeans(best_k, n_init=10, random_state=s).fit_predict(Xs) for s in range(10)]
    aris = [adjusted_rand_score(labelings[0], labelings[i]) for i in range(1, 10)]
    stability = round(float(np.mean(aris)), 3)

    # overlap with quantile performance segment
    seg = assign_segments(metrics)
    perf_codes = seg["performance_segment"].cat.codes.values
    km_best = KMeans(best_k, n_init=10, random_state=seed).fit_predict(Xs)
    overlap = round(float(adjusted_rand_score(perf_codes, km_best)), 3)

    return {
        "silhouette_by_k": sils, "best_k": best_k, "best_silhouette": sils[best_k],
        "seed_stability_ari": stability, "overlap_with_performance_ari": overlap,
        "n_accounts": len(metrics),
    }
