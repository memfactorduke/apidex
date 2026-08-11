#!/usr/bin/env python3
"""Content lint over data/final/: catches decoder-degenerate values that pass
schema validation (duplicate/placeholder/echoed-example use_cases, stub URLs).
Exit 1 if anything is flagged."""
import json, glob, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEATHER_STUB = "get current weather for a city"
WEATHERISH = {"weather-environment", "science-space", "travel-hospitality",
              "transportation", "agriculture", "energy-utilities", "geo-maps",
              "iot-devices", "fun-novelty", "government-open-data", "data-analytics"}
PLACEHOLDER = ("pending", "placeholder", "tbd", "unknown", "research", "verifying")

bad = 0
for f in sorted(glob.glob(str(ROOT / "data" / "final" / "*.json"))):
    e = json.loads(Path(f).read_text())
    flags = []
    us = e.get("use_cases", [])
    if len(set(us)) < len(us):
        flags.append("duplicate use_cases")
    if any(len(u.strip()) < 9 for u in us):
        flags.append("trivial/empty use_case")
    if any(u.strip().lower() in PLACEHOLDER for u in us):
        flags.append("placeholder use_case")
    if WEATHER_STUB in us and e["category"] not in WEATHERISH:
        flags.append("echoed weather example in non-weather category")
    for k in ("base_url", "docs_url"):
        if e.get(k, "").rstrip("/") in ("https:/", "http:/", "https://", "http://", ""):
            flags.append(f"stub {k}")
    if flags:
        bad += 1
        print(f"LINT {e['id']} ({e['category']}): {'; '.join(flags)}")
print(f"{bad} entries flagged")
sys.exit(1 if bad else 0)
