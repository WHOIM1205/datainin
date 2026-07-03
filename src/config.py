"""Load the single source of truth (config.yaml) and expose paths."""
from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(path: Path | str | None = None) -> dict:
    """Load config.yaml as a dict."""
    p = Path(path) if path else CONFIG_PATH
    with open(p) as f:
        return yaml.safe_load(f)


def resolve(rel: str) -> Path:
    """Resolve a config-relative path against the project root."""
    return PROJECT_ROOT / rel
