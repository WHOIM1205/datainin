"""
Reproducible data acquisition.

Both datasets are public Google Drive files (links from the assignment PDF).
This script re-fetches them into data/raw/ so the pipeline is reproducible from
scratch. It handles Google Drive's large-file confirm-token interstitial.

Run:  python data/download.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parent / "raw"

# (Google Drive file id, output filename) from the assignment PDF.
FILES = {
    "1PgQC0tO8XN-wqkNyghWc_-mnrYv_nhSf": "fear_greed.csv",
    "1IAfLZwu6rJzyWKgBToqwSmmVYU6VbjVs": "hyperliquid_trades.csv",
}


def fetch(file_id: str, out_name: str) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / out_name
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    # curl -L follows Drive's redirect; small files download directly. For files
    # large enough to trigger the virus-scan interstitial, add a &confirm=t retry.
    subprocess.run(["curl", "-sL", url, "-o", str(out)], check=True)
    # If we got an HTML interstitial instead of data, retry with confirm=t.
    head = out.read_bytes()[:200]
    if head.lstrip().startswith((b"<", b"<!DOCTYPE", b"<html")):
        confirm_url = url + "&confirm=t"
        subprocess.run(["curl", "-sL", confirm_url, "-o", str(out)], check=True)
    print(f"  {out_name}: {out.stat().st_size:,} bytes")
    return out


def main() -> None:
    print("Downloading datasets to data/raw/ ...")
    for fid, name in FILES.items():
        fetch(fid, name)
    print("Done. If a file looks like HTML, the Drive link may require manual download.")


if __name__ == "__main__":
    sys.exit(main())
