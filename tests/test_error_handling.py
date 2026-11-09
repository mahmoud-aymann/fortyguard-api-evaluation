"""
Lightweight checks for documented FortyGuard API error behavior.

Runs against the live API only when FORTYGUARD_API_KEY is set.
Uses no paid heatmap credits — only rejected requests.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://api.fortyguard.com/v1"


def _load_dotenv(path: Path) -> None:
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


_load_dotenv(ROOT / ".env")
API_KEY = os.getenv("FORTYGUARD_API_KEY")
HAS_KEY = bool(API_KEY)


# Small Cairo polygon (outside US coverage)
CAIRO_AOI = {
    "type": "Polygon",
    "coordinates": [[
        [31.2200, 30.0400],
        [31.2300, 30.0400],
        [31.2300, 30.0500],
        [31.2200, 30.0500],
        [31.2200, 30.0400],
    ]],
}


@unittest.skipUnless(HAS_KEY, "FORTYGUARD_API_KEY not set; skipping live API tests")
class TestErrorHandling(unittest.TestCase):
    def test_401_on_bad_key(self) -> None:
        r = requests.post(
            f"{BASE_URL}/heatmap",
            headers={"api-key": "not-a-real-key", "Content-Type": "application/json"},
            json={
                "polygon_aoi": CAIRO_AOI,
                "date_time": {
                    "start_date": "2024-07-15",
                    "start_time": "14:00",
                    "filter_type": 1,
                },
                "granularity": 100,
            },
            timeout=60,
        )
        self.assertEqual(r.status_code, 401)
        body = r.json()
        self.assertTrue(body.get("error") or body.get("status_code") == 401)

    def test_422_on_missing_fields(self) -> None:
        r = requests.post(
            f"{BASE_URL}/heatmap",
            headers={"api-key": API_KEY, "Content-Type": "application/json"},
            json={"granularity": 100},
            timeout=60,
        )
        self.assertEqual(r.status_code, 422)
        body = r.json()
        # Docs / observed: field name called out in response
        text = str(body).lower()
        self.assertTrue("polygon_aoi" in text or "required" in text)

    def test_400_out_of_coverage_cairo(self) -> None:
        r = requests.post(
            f"{BASE_URL}/heatmap",
            headers={"api-key": API_KEY, "Content-Type": "application/json"},
            json={
                "polygon_aoi": CAIRO_AOI,
                "date_time": {
                    "start_date": "2024-07-15",
                    "start_time": "14:00",
                    "filter_type": 1,
                },
                "granularity": 100,
            },
            timeout=60,
        )
        self.assertEqual(r.status_code, 400)
        body = r.json()
        self.assertEqual(body.get("code"), "OUT_OF_COVERAGE")


if __name__ == "__main__":
    unittest.main()
