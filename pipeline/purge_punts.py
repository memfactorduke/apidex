#!/usr/bin/env python3
"""Delete punted adjudications: all-null rulings whose notes cite no URL.

A legitimate all-null ruling ("originals confirmed") must cite evidence; the
prompt requires a URL per disputed field. No 'http' in the notes => punt.
Also removes the corresponding stale final so it can't ship unadjudicated.
Prints the number purged (0 = converged).
"""
import json, glob, os, sys

FIELDS = ["base_url", "docs_url", "auth_type", "free_tier", "free_tier_limits",
          "rate_limits", "cors", "example_request", "example_response_snippet",
          "description", "status"]

n = 0
for f in sorted(glob.glob("data/adjudicate/*.json")):
    a = json.load(open(f))
    if all(a.get(k) is None for k in FIELDS) and "http" not in a["resolution_notes"]:
        os.remove(f)
        fin = f"data/final/{a['id']}.json"
        if os.path.exists(fin):
            os.remove(fin)
        n += 1
        print(f"purged punt: {a['id']}")
print(n)
sys.exit(0)
