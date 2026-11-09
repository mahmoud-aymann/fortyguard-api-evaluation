#!/usr/bin/env python3
"""Print basic distribution stats from data/houston_tiles.csv."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "houston_tiles.csv"
OUT_PATH = ROOT / "docs" / "tile_stats.json"


def main() -> None:
    if not CSV_PATH.is_file():
        raise SystemExit(f"Missing {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    col = "average_temperature_c"
    if col not in df.columns:
        raise SystemExit(f"Column {col} not found")

    temps = df[col].dropna()
    stats = {
        "n_tiles": int(len(temps)),
        "min_c": round(float(temps.min()), 2),
        "mean_c": round(float(temps.mean()), 2),
        "median_c": round(float(temps.median()), 2),
        "max_c": round(float(temps.max()), 2),
        "std_c": round(float(temps.std()), 2),
        "p25_c": round(float(temps.quantile(0.25)), 2),
        "p75_c": round(float(temps.quantile(0.75)), 2),
        "range_c": round(float(temps.max() - temps.min()), 2),
    }
    print("Houston tile temperature summary (°C)")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
