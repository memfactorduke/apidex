#!/usr/bin/env python3
"""Generate final-arbitration jobs: Grok (live web) settles Codex audit disputes."""
import json, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROMPT = """You are the final arbiter for one entry in a verified public-API directory. The entry was researched and double-verified earlier today with live web access. A second AI system from a different model family then audited it WITHOUT web access, from its training knowledge, and disputed the fields below. Its knowledge may be stale (pricing and rate limits change constantly) — or it may have caught a real error the verifiers missed (renamed endpoints, decommissioned products).

Settle each dispute NOW with live web search against current official sources. Recency wins: what the official docs say today is the truth.

CURRENT ENTRY:
{entry}

AUDITOR'S DISPUTES:
{issues}

Output rules:
- Reach a verdict on every disputed field in this response. Never write notes about what you are "about to" verify — an all-null output whose notes cite no evidence URL is invalid work.
- Output the corrected value for fields where the auditor is right; null where the original stands (resolution_notes must cite the evidence URL either way).
- Fields not disputed: null.
- status: "defunct" if the API/product has genuinely been shut down; else null.
- resolution_notes: per disputed field: who was right and the evidence URL.
- id: exactly "{slug}"."""


def main():
    jobs = []
    for f in sorted(glob.glob(str(ROOT / "data" / "audit" / "*.json"))):
        d = json.loads(Path(f).read_text())
        for a in d.get("audits", []):
            issues = [i for i in a.get("issues", []) if i.get("field") != "unassessable"]
            if not issues:
                continue
            slug = a["id"]
            entry_path = ROOT / "data" / "final" / f"{slug}.json"
            if not entry_path.exists():
                continue
            entry = json.loads(entry_path.read_text())
            slim = {k: entry[k] for k in ["id", "name", "base_url", "docs_url", "auth",
                                          "pricing", "rate_limits", "example", "status",
                                          "description"]}
            jobs.append({
                "id": f"arbitrate-{slug}",
                "prompt": PROMPT.format(entry=json.dumps(slim, indent=1),
                                        issues=json.dumps(issues, indent=1), slug=slug),
                "schema": str(ROOT / "schema" / "audit_fix.schema.json"),
                "out": str(ROOT / "data" / "audit-fix" / f"{slug}.json"),
            })
    out = ROOT / "pipeline" / "jobs-arbitrate.jsonl"
    out.write_text("\n".join(json.dumps(j) for j in jobs) + "\n")
    print(f"wrote {len(jobs)} arbitration jobs to {out}")


if __name__ == "__main__":
    main()
