#!/usr/bin/env python3
"""
FortyGuard Temperature API demo (unofficial evaluation helper).

Reads FORTYGUARD_API_KEY from the environment or a local .env file.
Submits a small Houston heatmap, polls until complete, writes CSV + plot.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
BASE_URL = "https://api.fortyguard.com/v1"
POLL_INTERVAL_S = 5
POLL_TIMEOUT_S = 180

# ~1 km² box downtown Houston, TX (US coverage)
HOUSTON_AOI = {
    "type": "Polygon",
    "coordinates": [[
        [-95.3700, 29.7500],
        [-95.3600, 29.7500],
        [-95.3600, 29.7600],
        [-95.3700, 29.7600],
        [-95.3700, 29.7500],
    ]],
}


def load_dotenv(path: Path) -> None:
    """Minimal .env loader (no python-dotenv dependency)."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


load_dotenv(ROOT / ".env")

API_KEY = os.getenv("FORTYGUARD_API_KEY")


def require_key() -> str:
    if not API_KEY:
        sys.exit(
            "FORTYGUARD_API_KEY missing.\n"
            "Copy .env.example to .env and set your trial key, "
            "or export FORTYGUARD_API_KEY."
        )
    return API_KEY


def headers(json_body: bool = False) -> dict:
    h = {"api-key": require_key()}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def submit_heatmap(
    polygon_aoi: dict,
    start_date: str = "2024-07-15",
    start_time: str = "14:00",
    filter_type: int = 1,
    granularity: int = 100,
) -> str:
    payload = {
        "polygon_aoi": polygon_aoi,
        "date_time": {
            "start_date": start_date,
            "start_time": start_time,
            "filter_type": filter_type,
        },
        "granularity": granularity,
    }
    t0 = time.time()
    r = requests.post(
        f"{BASE_URL}/heatmap",
        headers=headers(True),
        json=payload,
        timeout=90,
    )
    elapsed = round(time.time() - t0, 2)
    if r.status_code != 200:
        raise RuntimeError(f"submit failed HTTP {r.status_code}: {r.text[:500]}")
    data = r.json()["data"]
    activity_id = data["activity_id"]
    print(f"Submitted heatmap activity_id={activity_id} submit_s={elapsed}")
    return activity_id


def poll_status(activity_id: str) -> dict:
    url = f"{BASE_URL}/status/{activity_id}"
    t0 = time.time()
    while True:
        elapsed = time.time() - t0
        if elapsed > POLL_TIMEOUT_S:
            raise TimeoutError(f"activity {activity_id} not done in {POLL_TIMEOUT_S}s")
        r = requests.get(url, headers=headers(), timeout=60)
        body = r.json()
        status = (body.get("data") or {}).get("status", "")
        print(f"  status={status} t={elapsed:.1f}s http={r.status_code}")
        if isinstance(status, str) and status.lower() in ("completed", "succeeded"):
            return body
        if isinstance(status, str) and status.lower() in ("failed", "error"):
            raise RuntimeError(f"activity failed: {json.dumps(body)[:800]}")
        time.sleep(POLL_INTERVAL_S)


def tiles_to_dataframe(result: dict) -> pd.DataFrame:
    features = (result.get("map_data") or {}).get("features") or []
    rows = []
    for f in features:
        props = f.get("properties") or {}
        rows.append(
            {
                "tile_id": props.get("tile_id"),
                "average_temperature_c": props.get("average_temperature"),
                "min_temperature_c": props.get("min_temperature"),
                "max_temperature_c": props.get("max_temperature"),
            }
        )
    return pd.DataFrame(rows)


def plot_tiles(df: pd.DataFrame, stats: dict, out_path: Path) -> None:
    temps = df["average_temperature_c"].dropna()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    axes[0].hist(
        temps,
        bins=min(12, max(5, len(temps) // 5)),
        color="#e4572e",
        edgecolor="white",
    )
    axes[0].set_title("Houston tile average temperatures")
    axes[0].set_xlabel("Temperature (°C)")
    axes[0].set_ylabel("Tile count")
    if stats:
        ts = stats.get("temperature_stats") or {}
        axes[0].axvline(
            ts.get("mean", temps.mean()),
            color="#2e294e",
            linestyle="--",
            label="mean",
        )
        axes[0].legend()

    axes[1].scatter(df["tile_id"], df["average_temperature_c"], c=temps, cmap="hot", s=28)
    axes[1].set_title("Temperature by tile_id")
    axes[1].set_xlabel("tile_id")
    axes[1].set_ylabel("Average °C")

    ts = (stats or {}).get("temperature_stats") or {}
    fig.suptitle(
        "FortyGuard heatmap — Houston 2024-07-15 14:00, 100 m\n"
        f"n={len(temps)}  min={ts.get('minimum', temps.min()):.2f}  "
        f"max={ts.get('maximum', temps.max()):.2f}  "
        f"mean={ts.get('mean', temps.mean()):.2f} °C",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    print(f"Wrote {out_path}")


def main() -> None:
    require_key()
    activity_id = submit_heatmap(HOUSTON_AOI)
    body = poll_status(activity_id)
    result = body["data"]["result"]
    stats = result.get("stats_data") or {}
    df = tiles_to_dataframe(result)
    if df.empty:
        raise RuntimeError("no tiles in map_data")

    data_dir = ROOT / "data"
    docs_dir = ROOT / "docs"
    data_dir.mkdir(exist_ok=True)
    docs_dir.mkdir(exist_ok=True)

    out_csv = data_dir / "houston_tiles.csv"
    df.to_csv(out_csv, index=False)
    print(f"Wrote {out_csv} rows={len(df)}")
    print(df["average_temperature_c"].describe().to_string())

    plot_path = docs_dir / "plot.png"
    plot_tiles(df, stats, plot_path)
    print("Done.")


if __name__ == "__main__":
    main()
