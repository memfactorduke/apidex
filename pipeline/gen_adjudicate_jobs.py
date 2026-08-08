#!/usr/bin/env python3
"""Generate Phase 3 adjudicator jobs from data/adjudicate-queue.jsonl."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROMPT = """You are the final adjudicator for one entry in a verified public-API directory. A researcher wrote the entry; two independent verifiers then checked it and flagged the following fields as possibly incorrect: {fields}.

ORIGINAL ENTRY:
{entry}

VERIFIER A VERDICTS (docs-first reviewer):
{va}

VERIFIER B VERDICTS (adversarial reviewer):
{vb}

Use web search to settle each disputed field against CURRENT (2026) official sources — docs, pricing pages, changelogs. You are the last line of defense; your ruling ships.

Output rules:
- For each DISPUTED field, output the correct final value. For every other field output null (null means "keep the original").
- example_request / example_response_snippet: only non-null if the example was disputed; if so, provide a corrected working curl and realistic snippet.
- status: null unless you conclude the API is degraded/defunct.
- resolution_notes: one short paragraph on what you ruled and on what evidence.
- id: exactly "{slug}"."""


def main():
    queue = ROOT / "data" / "adjudicate-queue.jsonl"
    jobs = []
    for line in queue.read_text().splitlines():
        if not line.strip():
            continue
        c = json.loads(line)
        slug = c["slug"]
        jobs.append({
            "id": f"adjudicate-{slug}",
            "prompt": PROMPT.format(
                fields=", ".join(c["fields"]), slug=slug,
                entry=json.dumps(c["entry"], indent=1),
                va=json.dumps(c["va"]["verdicts"], indent=1),
                vb=json.dumps(c["vb"]["verdicts"], indent=1)),
            "schema": str(ROOT / "schema" / "adjudicate.schema.json"),
            "out": str(ROOT / "data" / "adjudicate" / f"{slug}.json"),
        })
    out = ROOT / "pipeline" / "jobs-adjudicate.jsonl"
    out.write_text("\n".join(json.dumps(j) for j in jobs) + "\n")
    print(f"wrote {len(jobs)} adjudicator jobs to {out}")


if __name__ == "__main__":
    main()
