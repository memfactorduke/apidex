#!/usr/bin/env python3
"""Merge Phase 0 seed lists: dedupe by slug and base_domain, emit merged.jsonl."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEEDS = ROOT / "data" / "seeds"


def norm_domain(d):
    d = re.sub(r"^https?://", "", d.lower()).strip("/")
    return re.sub(r"^(www|api|docs|developer|developers)\.", "", d)


def main():
    seen_slug, seen_domain, merged = {}, {}, []
    files = sorted(SEEDS.glob("*.json"))
    for f in files:
        data = json.loads(f.read_text())
        cat = data["category"]
        for a in data["apis"]:
            slug = a["slug"]
            dom = norm_domain(a["base_domain"])
            if slug in seen_slug or dom in seen_domain:
                continue
            seen_slug[slug] = cat
            seen_domain[dom] = slug
            merged.append({
                "slug": slug, "name": a["name"], "category": cat,
                "base_domain": a["base_domain"], "docs_url": a["docs_url"],
                "free_tier": a["free_tier"], "why_notable": a["why_notable"],
            })
    out = SEEDS / "merged.jsonl"
    out.write_text("\n".join(json.dumps(m) for m in merged) + "\n")
    cats = {}
    for m in merged:
        cats[m["category"]] = cats.get(m["category"], 0) + 1
    print(f"{len(merged)} unique APIs from {len(files)} categories")
    for c, n in sorted(cats.items()):
        print(f"  {c}: {n}")


if __name__ == "__main__":
    main()
