#!/usr/bin/env python3
"""Apply regenerated use_cases (data/usecase-fix/) to data/final/ entries."""
import json, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

applied = skipped = 0
for f in sorted(glob.glob(str(ROOT / "data" / "usecase-fix" / "*.json"))):
    r = json.loads(Path(f).read_text())
    us = r.get("use_cases", [])
    us = [u.strip() for u in us if isinstance(u, str) and len(u.strip()) > 8]
    us = list(dict.fromkeys(us))[:6]
    if len(us) < 2:
        print(f"skip {r.get('id')}: unusable fix ({us})")
        skipped += 1
        continue
    fin = ROOT / "data" / "final" / f"{r['id']}.json"
    entry = json.loads(fin.read_text())
    entry["use_cases"] = us
    fin.write_text(json.dumps(entry, indent=2))
    applied += 1
    print(f"fixed {r['id']}: {us[0]!r} +{len(us)-1} more")
print(f"applied={applied} skipped={skipped}")
