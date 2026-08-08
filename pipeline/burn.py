#!/usr/bin/env python3
"""Quota burn meter: aggregate logs/usage.jsonl."""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
by_phase = defaultdict(lambda: {"jobs": 0, "tokens": 0, "cost": 0.0})
total = {"jobs": 0, "tokens": 0, "cost": 0.0}
log = ROOT / "logs" / "usage.jsonl"
if log.exists():
    for line in log.read_text().splitlines():
        r = json.loads(line)
        phase = r["id"].split("-", 1)[0]
        for agg in (by_phase[phase], total):
            agg["jobs"] += 1
            agg["tokens"] += r.get("tokens", 0)
            agg["cost"] += r.get("cost_usd") or 0
for phase, a in sorted(by_phase.items()):
    print(f"{phase:12} {a['jobs']:5} jobs  {a['tokens']/1e6:8.2f}M tok  ${a['cost']:8.2f}")
print(f"{'TOTAL':12} {total['jobs']:5} jobs  {total['tokens']/1e6:8.2f}M tok  ${total['cost']:8.2f} (API-equivalent value)")
