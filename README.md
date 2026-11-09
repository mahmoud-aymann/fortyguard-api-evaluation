# FortyGuard Temperature API — small evaluation project

Unofficial, personal evaluation helper for the [FortyGuard Temperature API](https://docs-api.fortyguard.com/docs/introduction).

Built while reviewing the product as part of a hiring process (Machine Learning Engineer internship application). It uses **free trial credits** only. It is **not** affiliated with FortyGuard and is not a production client.

## What it does

1. Submits a small (~1 km²) Houston heatmap request
2. Polls `GET /status/{activity_id}` until the job completes
3. Writes tile temperatures to `data/houston_tiles.csv`
4. Saves a simple plot to `docs/plot.png`
5. Optionally checks a few documented error responses (401 / 422 / 400)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# put your trial key in .env as FORTYGUARD_API_KEY=...
```

Auth header used by the REST API: `api-key: <your key>`.

## How to run

```bash
# Live demo — uses trial credits (one small heatmap)
python fg_demo.py

# Offline summary of the saved CSV
python scripts/analyze_tiles.py

# Error-handling checks (skip if no key; no successful heatmap calls)
python -m unittest tests.test_error_handling -v
```

## Example results (real run)

Area: downtown Houston, TX · ~1 km² polygon · granularity **100 m**  
Datetime: **2024-07-15 14:00** (filter_type=1)

| Metric | Value |
|--------|-------|
| Tiles returned | **77** |
| Min / mean / max (°C) | **33.54 / 34.16 / 35.27** |
| End-to-end wait | **~22–23 s** (submit + poll) |

See `data/houston_tiles.csv` and `docs/plot.png`.

### Async flow

```
POST /v1/heatmap  →  { activity_id }
GET  /v1/status/{activity_id}  until status == Completed
```

The response `result` includes `map_data` (GeoJSON features / tiles) and `stats_data`.

## Short API observations

These are notes from a short trial, not a full audit:

- There is no simple “temperature at a lat/lon” endpoint; heatmaps cover an AOI. `env_params` expects you to supply temperature inputs for derived indices.
- REST auth uses the `api-key` header; the MCP path documented by FortyGuard uses `Bearer` — different auth styles across products.
- Completed heatmap results I saw did not include uncertainty / confidence / accuracy-tier fields (even though the dashboard mentions an accuracy index).
- The usage endpoint asked for the API key again in the request body, even when the header was already set.
- Published rate limits were not found in the docs I read; coverage for heatmap calls is US-only (Cairo returned `OUT_OF_COVERAGE`).

## Project layout

```
fg_demo.py                 # main demo script
data/houston_tiles.csv     # sample output
docs/plot.png              # sample plot
docs/tile_stats.json       # from analyze_tiles.py
scripts/analyze_tiles.py   # offline CSV summary
tests/test_error_handling.py
.env.example
requirements.txt
```

## Disclaimer

This repository is a learning / evaluation artifact. Please do not treat it as official FortyGuard documentation. Keep your API key private; never commit `.env`.
