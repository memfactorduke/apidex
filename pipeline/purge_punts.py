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

# --only <file>: restrict to these slugs (one per line) so a purge pass can
# never touch round-1 adjudications/finals.
only = None
if "--only" in sys.argv:
    only = set(open(sys.argv[sys.argv.index("--only") + 1]).read().split())

n = 0
for f in sorted(glob.glob("data/adjudicate/*.json")):
    a = json.load(open(f))
    if only is not None and a.get("id") not in only:
        continue
    if all(a.get(k) is None for k in FIELDS) and "http" not in a.get("resolution_notes", ""):
        os.remove(f)
        fin = f"data/final/{a['id']}.json"
        if os.path.exists(fin):
            os.remove(fin)
        n += 1
        print(f"purged punt: {a['id']}")
print(n)
sys.exit(0)
