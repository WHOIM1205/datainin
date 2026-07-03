"""Unit tests for the Module 4 EDA helpers (prep, direction categorisation, Gini)."""
import importlib.util
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # headless
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load scripts/run_eda.py as a module (scripts/ is not a package).
_spec = importlib.util.spec_from_file_location("run_eda", ROOT / "scripts" / "run_eda.py")
run_eda = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_eda)


def _trades():
    return pd.DataFrame({
        "Account": ["a", "a", "b", "c", "c"],
        "Direction": ["Open Long", "Close Short", "Open Short", "Buy", "Auto-Deleveraging"],
        "Closed PnL": [0.0, 5.0, -3.0, 0.0, 2.0],
        "is_spot": [False, False, False, True, False],
        "is_edge_direction": [False, False, False, False, True],
    })


def test_prep_adds_expected_columns():
    df = run_eda.prep(_trades())
    for c in ["pnl_bearing", "is_perp", "direction_cat"]:
        assert c in df.columns


def test_direction_cat_mapping():
    df = run_eda.prep(_trades())
    # Open Long -> Long; Close Short -> Short(? no) : Close Short is not in SHORT_DIRS -> falls to Spot/Edge
    assert df["direction_cat"].tolist() == ["Long", "Short", "Short", "Spot", "Edge"]
    # NOTE: Close Short is a long-increasing action but classified by position type below.


def test_pnl_bearing_and_perp_flags():
    df = run_eda.prep(_trades())
    assert df["pnl_bearing"].tolist() == [False, True, True, False, True]
    # perp = not spot and not edge
    assert df["is_perp"].tolist() == [True, True, True, False, False]


def test_gini_bounds():
    # perfect equality -> Gini ~ 0
    lx, ly, g_eq = run_eda.lorenz_gini(np.array([10, 10, 10, 10]))
    assert abs(g_eq) < 1e-9
    # maximal concentration -> Gini closer to 1
    _, _, g_hi = run_eda.lorenz_gini(np.array([0, 0, 0, 100]))
    assert g_hi > 0.6
    assert g_hi > g_eq
