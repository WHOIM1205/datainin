"""Smoke/unit test for the Module 13 figure helper (_boot_effect)."""
import importlib.util
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location("build_stat_figures", ROOT / "scripts" / "build_stat_figures.py")
bsf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bsf)

from src.stats import cliffs_delta, paired_rank_biserial


def test_boot_effect_paired_ordered_and_bounded():
    x = np.array([1.0, 2, 3, 4, 5, 6, 7, 8])
    y = x + 5
    lo, hi = bsf._boot_effect(paired_rank_biserial, y, x, n=300)
    assert lo <= hi
    assert -1.0 <= lo <= 1.0 and -1.0 <= hi <= 1.0


def test_boot_effect_independent_ordered():
    a = np.array([1.0, 2, 3, 4, 5])
    b = np.array([6.0, 7, 8, 9, 10])
    lo, hi = bsf._boot_effect(cliffs_delta, b, a, n=300)
    assert lo <= hi
    assert lo > 0    # b clearly larger than a
