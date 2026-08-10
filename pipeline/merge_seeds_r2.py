#!/usr/bin/env python3
"""Merge round-2 seed lists, deduping against everything round 1 already
covered (shipped entries, all researched slugs/domains, round-1 seeds)."""
import json, re, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def norm_domain(d):
    d = re.sub(r"^https?://", "", str(d).lower()).strip("/").split("/")[0]
    return re.sub(r"^(www|api|docs|developer|developers)\.", "", d)


def main():
    seen_slug, seen_domain = set(), set()
    # round-1 coverage: shipped + researched (incl. dropped defunct) + seeded
    for f in glob.glob(str(ROOT / "data" / "final" / "*.json")) + \
             glob.glob(str(ROOT / "data" / "research" / "*.json")):
        e = json.loads(Path(f).read_text())
        seen_slug.add(e["id"])
        seen_domain.add(norm_domain(e.get("base_url", "")))
    merged_r1 = ROOT / "data" / "seeds" / "merged.jsonl"
    for line in merged_r1.read_text().splitlines():
        if not line.strip():
            continue
        s = json.loads(line)
        seen_slug.add(s["slug"])
        seen_domain.add(norm_domain(s["base_domain"]))

    merged, dropped = [], 0
    for f in sorted(glob.glob(str(ROOT / "data" / "seeds-r2" / "*.json"))):
        data = json.loads(Path(f).read_text())
        cat = data["category"]
        for a in data["apis"]:
            slug, dom = a["slug"], norm_domain(a["base_domain"])
            if slug in seen_slug or dom in seen_domain:
                dropped += 1
                continue
            seen_slug.add(slug)
            seen_domain.add(dom)
            merged.append({
                "slug": slug, "name": a["name"], "category": cat,
                "base_domain": a["base_domain"], "docs_url": a["docs_url"],
                "free_tier": a["free_tier"], "why_notable": a["why_notable"],
            })
    out = ROOT / "data" / "seeds-r2" / "merged.jsonl"
    out.write_text("\n".join(json.dumps(m) for m in merged) + "\n")
    cats = {}
    for m in merged:
        cats[m["category"]] = cats.get(m["category"], 0) + 1
    print(f"{len(merged)} new unique APIs ({dropped} deduped away)")
    for c, n in sorted(cats.items()):
        print(f"  {c}: {n}")


if __name__ == "__main__":
    main()
