"""
Module 6 — per-trade feature engineering.

Adds behavioural + performance features intrinsic to each trade and its account
context. Non-destructive (only adds columns). No market-context or sentiment join
here — anything needing the (still-deferred) tz/merge choice, e.g. directional
alignment vs the derived BTC market proxy, is built in the merge module (M9).

Features & rationale (frozen refs in ASSUMPTIONS_LOG.md):
  pnl_bearing / is_win   — realized PnL booked on closing fills only (D6, F2.9, E1)
  position_side / is_perp— Long/Short/Spot/Edge from Direction (E5, F2.10)
  pnl_per_notional       — return on notional; robust to size heterogeneity (E1, E6)
  fee_bps / fee_drag     — trading cost in bps and as a share of gross PnL (F2.14)
  size_z / is_large_trade— trade size vs the ACCOUNT'S OWN history: separates
                           "aggressive trader" from "unusually aggressive today" (E3, E6)
  account_tenure_days    — days since the account's first trade in-sample (E3)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LONG_DIRS = {"Open Long", "Close Long"}
SHORT_DIRS = {"Open Short", "Close Short"}
LARGE_TRADE_Z = 2.0


def add_trade_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # --- classifiers ---
    df["pnl_bearing"] = df["Closed PnL"] != 0                      # D6 / F2.9
    df["is_win"] = (df["Closed PnL"] > 0).astype("boolean").mask(~df["pnl_bearing"])
    df["is_perp"] = ~df["is_spot"] & ~df["is_edge_direction"]
    df["position_side"] = np.select(
        [df["Direction"].isin(LONG_DIRS), df["Direction"].isin(SHORT_DIRS), df["is_spot"]],
        ["Long", "Short", "Spot"], default="Edge",
    )

    # --- performance normalized by notional (E1/E6: PnL & size are heavy-tailed) ---
    size = df["Size USD"].where(df["Size USD"] > 0)
    df["pnl_per_notional"] = (df["Closed PnL"] / size).where(df["pnl_bearing"])

    # --- trading cost (F2.14: negative fees are maker rebates) ---
    df["fee_bps"] = (df["Fee"] / size) * 1e4
    gross = df["Closed PnL"].abs().where(df["pnl_bearing"] & (df["Closed PnL"] != 0))
    df["fee_drag"] = (df["Fee"] / gross)

    # --- self-normalized size vs the account's own history (E3/E6) ---
    logsize = np.log(size)
    g = logsize.groupby(df["Account"])
    mu, sd = g.transform("mean"), g.transform("std")
    df["size_z"] = ((logsize - mu) / sd).where(sd > 0)
    df["is_large_trade"] = (df["size_z"] > LARGE_TRADE_Z).astype("boolean").mask(df["size_z"].isna())

    # --- account tenure at time of trade (left-censored at dataset start) ---
    first_ts = df.groupby("Account")["ts_ist"].transform("min")
    df["account_tenure_days"] = (df["ts_ist"] - first_ts).dt.days

    return df
