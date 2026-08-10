#!/usr/bin/env python3
"""Generate Phase 1 researcher jobs from data/seeds/merged.jsonl."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROMPT = """You are researching ONE public API for a rigorously verified developer directory. Accuracy matters more than completeness — a wrong fact is far worse than "unknown".

API: {name}
Domain: {base_domain}
Suggested docs: {docs_url}
Category: {cat}
Context: {why}

Use web search heavily — check the official docs, pricing page, and any status/changelog pages. Every field must reflect CURRENT (2026) reality. Field rules:
- id: exactly "{slug}". category: exactly "{cat}".
- status: "operational" unless you find evidence the API is degraded or shut down. If defunct, still fill the schema as best you can and set status to "defunct".
- base_url: the actual API root endpoint developers call (e.g. https://api.example.com/v2) — NOT the marketing homepage.
- docs_url: the current documentation page (verify it; correct the suggested one if stale).
- auth: how developers authenticate, concretely (e.g. "API key via X-Api-Key header, self-serve signup").
- pricing.free_tier_limits: concrete numbers from the pricing page ("1,000 req/day free") or "no free tier" / "unknown".
- rate_limits: the published limits, or "not published".
- example.request: a single curl command that would genuinely work against a real endpoint (use YOUR_API_KEY placeholder). Get the path, params, and headers right — this will be tested. example.response_snippet: abbreviated realistic response from the docs.
- cors: "yes" only if docs confirm browser calls work; "unknown" if not determinable.
- use_cases: 2-6 short concrete tasks a coding agent might reach for this API for (powers task-based search, so phrase them as needs: "get current weather for a city").
- sources: the URLs you actually consulted.
- researcher_confidence: "high" only if official docs directly confirmed base_url, auth, pricing, and the example; "medium" if minor gaps; "low" if significant uncertainty or the API looks dead."""


def main():
    import sys
    merged = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "seeds" / "merged.jsonl"
    out_name = sys.argv[2] if len(sys.argv) > 2 else "jobs-research.jsonl"
    seeds = [json.loads(l) for l in merged.read_text().splitlines() if l.strip()]
    # Round-robin across categories so a mid-phase quota death still leaves
    # every category evenly covered.
    by_cat = {}
    for s in seeds:
        by_cat.setdefault(s["category"], []).append(s)
    ordered, i = [], 0
    while any(by_cat.values()):
        for cat in sorted(by_cat):
            if by_cat[cat]:
                ordered.append(by_cat[cat].pop(0))
    jobs = []
    for s in ordered:
        docs = s["docs_url"] if len(s["docs_url"]) > 11 else "(unknown — locate the official docs)"
        jobs.append({
            "id": f"research-{s['slug']}",
            "prompt": PROMPT.format(name=s["name"], base_domain=s["base_domain"],
                                    docs_url=docs, cat=s["category"],
                                    why=s["why_notable"], slug=s["slug"]),
            "schema": str(ROOT / "schema" / "entry.schema.json"),
            "out": str(ROOT / "data" / "research" / f"{s['slug']}.json"),
        })
    out = ROOT / "pipeline" / out_name
    out.write_text("\n".join(json.dumps(j) for j in jobs) + "\n")
    print(f"wrote {len(jobs)} researcher jobs to {out}")


if __name__ == "__main__":
    main()
