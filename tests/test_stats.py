"""Unit tests for src.stats — effect sizes, bootstrap ordering, paired builders."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.stats import (MIN_DAYS, _paired, account_regime_metrics,
                       boot_ci_paired_median, cliffs_delta, cramers_v,
                       paired_rank_biserial)


def test_cliffs_delta_bounds():
    assert cliffs_delta([4, 5, 6], [1, 2, 3]) == 1.0     # first group entirely larger
    assert cliffs_delta([1, 2, 3], [4, 5, 6]) == -1.0
    assert cliffs_delta([1, 2, 3], [1, 2, 3]) == 0.0


def test_paired_rank_biserial_sign():
    assert paired_rank_biserial([3, 4, 5], [1, 1, 1]) == 1.0    # x>y always
    assert paired_rank_biserial([1, 1, 1], [3, 4, 5]) == -1.0
    assert paired_rank_biserial([2, 2, 2], [2, 2, 2]) == 0.0


def test_cramers_v_bounds():
    indep = np.array([[10, 10], [10, 10]])
    assoc = np.array([[20, 0], [0, 20]])
    assert cramers_v(indep) == 0.0
    assert cramers_v(assoc) > 0.99


def test_boot_ci_ordered():
    lo, hi = boot_ci_paired_median([1, 2, 3, 4, 5], [3, 4, 5, 6, 7], n=500)
    assert lo <= hi


def _account_day_merged():
    rows = []
    # A: 6 Fear + 6 Greed days -> qualifies
    for i in range(6):
        rows.append(("A", "Fear", 1.0 * i, 1, 2, 3))
        rows.append(("A", "Greed", 2.0 * i, 2, 2, 4))
    # B: 6 Fear + 2 Greed -> excluded (Greed < MIN_DAYS)
    for i in range(6):
        rows.append(("B", "Fear", 5.0, 1, 1, 1))
    for i in range(2):
        rows.append(("B", "Greed", 9.0, 1, 1, 1))
    return pd.DataFrame(rows, columns=["Account", "sentiment_side", "daily_pnl",
                                       "win_count", "pnl_trade_count", "trade_count"])


def test_account_regime_metrics_rates():
    arm = account_regime_metrics(_account_day_merged())
    a_greed = arm.loc[("A", "Greed")]
    assert a_greed["n_days"] == 6
    assert a_greed["win_rate"] == 2 / 2         # win_count/pnl_trade_count per row summed: 12/12
    assert a_greed["trades_per_day"] == 24 / 6  # trade_count sum 24 over 6 days


def test_paired_filters_min_days():
    arm = account_regime_metrics(_account_day_merged())
    fear, greed, n = _paired(arm, "median_daily_pnl")
    assert n == 1                                # only A qualifies (B has <MIN_DAYS Greed)
    assert MIN_DAYS == 5
