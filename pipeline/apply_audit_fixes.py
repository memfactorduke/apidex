#!/usr/bin/env python3
"""Apply arbitration rulings (data/audit-fix/) to data/final/ entries.

Punted rulings (all-null, no evidence URL in notes) are ignored — the entry
keeps its double-verified values. Defunct rulings remove the entry.
"""
import json, glob
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SET = {
    "base_url": lambda e, v: e.__setitem__("base_url", v),
    "docs_url": lambda e, v: e.__setitem__("docs_url", v),
    "auth_type": lambda e, v: e["auth"].__setitem__("type", v),
    "auth_details": lambda e, v: e["auth"].__setitem__("details", v),
    "free_tier": lambda e, v: e["pricing"].__setitem__("free_tier", v),
    "free_tier_limits": lambda e, v: e["pricing"].__setitem__("free_tier_limits", v),
    "paid_plans": lambda e, v: e["pricing"].__setitem__("paid_plans", v),
    "rate_limits": lambda e, v: e.__setitem__("rate_limits", v),
    "cors": lambda e, v: e.__setitem__("cors", v),
    "example_request": lambda e, v: e["example"].__setitem__("request", v),
    "example_response_snippet": lambda e, v: e["example"].__setitem__("response_snippet", v),
    "description": lambda e, v: e.__setitem__("description", v),
}

applied = upheld = punts = dropped = 0
for f in sorted(glob.glob(str(ROOT / "data" / "audit-fix" / "*.json"))):
    r = json.loads(Path(f).read_text())
    fields = {k: r.get(k) for k in SET}
    all_null = all(v is None for v in fields.values()) and r.get("status") is None
    if all_null and "http" not in r.get("resolution_notes", ""):
        punts += 1
        continue
    fin = ROOT / "data" / "final" / f"{r['id']}.json"
    if not fin.exists():
        continue
    if r.get("status") == "defunct":
        fin.unlink()
        dropped += 1
        print(f"dropped (audit-confirmed defunct): {r['id']}")
        continue
    entry = json.loads(fin.read_text())
    corrected = []
    for k, v in fields.items():
        if v is not None:
            SET[k](entry, v)
            corrected.append(k)
    if r.get("status") is not None:
        entry["status"] = r["status"]
    entry["verification"]["audit"] = {
        "auditor": "gpt-5.6-offline", "arbiter": "grok-4.5-live-web",
        "date": date.today().isoformat(),
        "corrected": corrected,
        "upheld_original": corrected == [],
    }
    fin.write_text(json.dumps(entry, indent=2))
    applied += 1 if corrected else 0
    upheld += 1 if not corrected else 0

print(f"corrected={applied} upheld={upheld} punts_ignored={punts} dropped={dropped}")
