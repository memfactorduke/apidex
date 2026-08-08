#!/usr/bin/env python3
"""Generate Phase 2 verifier jobs: two independent Grok verifiers per entry.

Verifier A is docs-first ("trace every claim to official docs").
Verifier B is adversarial ("assume at least one field is wrong; find it").
Diverse lenses catch more than two identical passes.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

COMMON = """You are verifying one entry in a public-API directory. The entry below was written by another AI researcher, whose known failure mode is confident hallucination — plausible-looking base URLs, invented rate limits, outdated pricing.

ENTRY UNDER REVIEW:
{entry_json}

Use web search to check the entry against CURRENT (2026) official sources. For each field in the verdicts object:
- "confirm" only if you located an authoritative source that supports the claim.
- "incorrect" if the source contradicts it — put the right value in "correction" and the URL in "source".
- "unverifiable" if you genuinely could not determine it. NEVER confirm something you did not check.

Field notes: auth_type refers to the auth.type value; free_tier to pricing.free_tier; free_tier_limits to pricing.free_tier_limits; example means the curl request's method/path/params/headers are consistent with current docs; description means the prose contains no false claims.

overall: "fail" if any field is "incorrect" or the API appears dead; else "pass". Set id to exactly "{slug}".
"""

LENS_A = "\nYour approach: docs-first. Open the official documentation, pricing, and auth pages and trace every single claim back to them methodically.\n"
LENS_B = "\nYour approach: adversarial. Assume at least one field in this entry is WRONG — your job is to find it. Actively hunt for shutdown notices, pricing changes, endpoint migrations, and deprecated versions before trusting anything.\n"


def main():
    jobs = []
    for f in sorted((ROOT / "data" / "research").glob("*.json")):
        entry = json.loads(f.read_text())
        if entry.get("status") == "defunct":
            continue
        slug = entry["id"]
        base = COMMON.format(entry_json=json.dumps(entry, indent=1), slug=slug)
        for tag, lens in (("a", LENS_A), ("b", LENS_B)):
            jobs.append({
                "id": f"verify-{slug}-{tag}",
                "prompt": base + lens,
                "schema": str(ROOT / "schema" / "verify.schema.json"),
                "out": str(ROOT / "data" / "verify" / f"{slug}.{tag}.json"),
            })
    out = ROOT / "pipeline" / "jobs-verify.jsonl"
    out.write_text("\n".join(json.dumps(j) for j in jobs) + "\n")
    print(f"wrote {len(jobs)} verifier jobs to {out}")


if __name__ == "__main__":
    main()
