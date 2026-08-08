#!/usr/bin/env python3
"""Generate cross-family audit jobs: GPT-5.6 Sol (Codex) audits Grok-built entries.

Batches of 10 entries per call. The auditor is from a different model family,
so shared-blind-spot errors that survived Grok-verifies-Grok have a chance of
being caught here.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BATCH = 10

PROMPT = """You are an independent auditor reviewing entries from a public-API directory that was researched and verified by a different AI system. Your job is to catch residual errors, not to rubber-stamp. Use web search if available; otherwise apply your own knowledge of these APIs.

For each entry check: is base_url the real current API root? Is the auth type right? Are free-tier/pricing claims plausible and current? Is the example curl syntactically correct AND consistent with that API's real interface (paths, params, headers)? Does anything suggest the API is dead or the entry conflates products?

ENTRIES:
{entries}

Respond with ONLY this JSON (no markdown fences, no prose):
{{"audits": [{{"id": "<entry id>", "issues": [{{"field": "<field name>", "problem": "<what is wrong>", "suggestion": "<correct value or action>", "confidence": "high|medium|low"}}]}}]}}

One audits element per entry, in order. issues must be [] for entries you found no problems in. Only report real problems — style nitpicks and "could be more detailed" are not issues. If you could not assess an entry at all, give it one issue with field "unassessable" and confidence "low"."""


def main():
    finals = sorted((ROOT / "data" / "final").glob("*.json"))
    jobs = []
    for i in range(0, len(finals), BATCH):
        batch = finals[i:i + BATCH]
        entries = []
        for f in batch:
            e = json.loads(f.read_text())
            slim = {k: e[k] for k in ["id", "name", "base_url", "docs_url", "auth",
                                      "pricing", "rate_limits", "example", "status",
                                      "description"]}
            entries.append(slim)
        jobs.append({
            "id": f"audit-{i // BATCH:03d}",
            "prompt": PROMPT.format(entries=json.dumps(entries, indent=1)),
            "out": str(ROOT / "data" / "audit" / f"batch-{i // BATCH:03d}.json"),
        })
    out = ROOT / "pipeline" / "jobs-audit.jsonl"
    out.write_text("\n".join(json.dumps(j) for j in jobs) + "\n")
    print(f"wrote {len(jobs)} audit jobs ({len(finals)} entries) to {out}")


if __name__ == "__main__":
    main()
