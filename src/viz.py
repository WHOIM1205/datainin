"""
Shared visualization styling for the whole project.

One palette, one style, applied everywhere so every figure reads as one system.
Colors are the dataviz-skill reference palette, validated for CVD safety
(validate_palette.js): Fear↔Greed passes at ΔE 13.3 (deutan); the Long/Short/Spot
trio passes; every categorical chart ships a legend + direct labels (relief rule),
so identity is never colour-alone.

`save_fig` exports PNG (raster, GitHub preview) AND SVG (vector) at high DPI with a
descriptive filename.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

# ---- Project palette (roles → validated hex) ----
PALETTE = {
    # sentiment regime = diverging pair with a gray (neutral) midpoint
    "Fear": "#e34948",
    "Greed": "#008300",
    "Neutral": "#898781",
    # trade direction / market type = categorical identity
    "Long": "#2a78d6",
    "Short": "#eb6834",
    "Spot": "#1baf7a",
    # single-series + accent
    "primary": "#2a78d6",   # default single series (blue)
    "accent": "#eb6834",    # secondary line, e.g. moving average (orange)
}
# chart chrome / ink (light surface)
INK = {
    "surface": "#fcfcfb", "primary": "#0b0b0b", "secondary": "#52514e",
    "muted": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7",
}

FIG_DPI = 200  # high-DPI raster suitable for GitHub


def apply_style() -> None:
    """Apply the project-wide matplotlib style. Call once before plotting."""
    mpl.rcParams.update({
        "figure.facecolor": INK["surface"],
        "axes.facecolor": INK["surface"],
        "savefig.facecolor": INK["surface"],
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Segoe UI", "Arial"],
        "font.size": 11,
        "axes.titlesize": 13, "axes.titleweight": "bold",
        "axes.titlecolor": INK["primary"],
        "axes.labelsize": 11, "axes.labelcolor": INK["secondary"],
        "axes.edgecolor": INK["axis"], "axes.linewidth": 1.0,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": INK["grid"], "grid.linewidth": 0.8,
        "xtick.color": INK["muted"], "ytick.color": INK["muted"],
        "xtick.labelcolor": INK["secondary"], "ytick.labelcolor": INK["secondary"],
        "legend.frameon": False, "legend.fontsize": 10,
        "figure.titlesize": 14, "figure.titleweight": "bold",
    })


def save_fig(fig, figures_dir: Path | str, stem: str) -> dict:
    """Export a figure as PNG + SVG at high DPI. `stem` is a descriptive filename base."""
    figures_dir = Path(figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    for ext in ("png", "svg"):
        p = figures_dir / f"{stem}.{ext}"
        fig.savefig(p, dpi=FIG_DPI, bbox_inches="tight")
        out[ext] = p
    plt.close(fig)
    return out
