#!/usr/bin/env python3
"""Re-run punted arbitrations until none remain (or quota dies)."""
import json, glob, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SET = ["base_url", "docs_url", "auth_type", "auth_details", "free_tier",
       "free_tier_limits", "paid_plans", "rate_limits", "cors",
       "example_request", "example_response_snippet", "description"]

for rnd in range(1, 11):
    punts = 0
    for f in sorted(glob.glob(str(ROOT / "data" / "audit-fix" / "*.json"))):
        r = json.loads(Path(f).read_text())
        if (all(r.get(k) is None for k in SET) and r.get("status") is None
                and "http" not in r.get("resolution_notes", "")):
            os.remove(f)
            punts += 1
    print(f"[round {rnd}] purged {punts} punts", flush=True)
    if punts == 0:
        print("converged", flush=True)
        sys.exit(0)
    rc = subprocess.run(["python3", "pipeline/runner.py", "pipeline/jobs-arbitrate.jsonl",
                         "--concurrency", "8"], cwd=ROOT).returncode
    if rc == 42:
        print("quota exhausted", flush=True)
        sys.exit(42)
print("max rounds reached", flush=True)
sys.exit(1)
