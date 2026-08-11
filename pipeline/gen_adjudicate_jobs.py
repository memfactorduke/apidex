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
- You must reach a VERDICT for every disputed field NOW, in this response — never output notes describing what you are "about to" or "currently" verifying. An all-null ruling with no cited evidence is invalid work.
- For each DISPUTED field, output the correct final value. For every other field output null (null means "keep the original"). Null for a disputed field is only acceptable if resolution_notes cites the specific evidence that the ORIGINAL value is right.
- If you cannot confirm a disputed field either way, rule WITH the verifier's correction (or "unknown"/conservative value) rather than keeping an unconfirmed original.
- example_request / example_response_snippet: only non-null if the example was disputed; if so, provide a corrected working curl and realistic snippet.
- status: null unless you conclude the API is degraded/defunct. If its domains do not respond at all, it is defunct.
- resolution_notes: for EACH disputed field: your verdict and the evidence URL.
- id: exactly "{slug}"."""


def main():
    machine = {}
    mc = ROOT / "logs" / "machine_check.jsonl"
    if mc.exists():
        for line in mc.read_text().splitlines():
            r = json.loads(line)
            machine[r["id"]] = r
    queue = ROOT / "data" / "adjudicate-queue.jsonl"
    jobs = []
    for line in queue.read_text().splitlines():
        if not line.strip():
            continue
        c = json.loads(line)
        slug = c["slug"]
        prompt_extra = ""
        m = machine.get(slug)
        if m and m["flags"]:
            prompt_extra = ("\n\nAUTOMATED CURL CHECKS (may be bot-detection false positives, "
                            f"but HTTP 0 usually means a dead domain): base_url returned "
                            f"HTTP {m['base_http']}, docs_url HTTP {m['docs_http']}. "
                            f"Flags: {'; '.join(m['flags'])}")
        jobs.append({
            "id": f"adjudicate-{slug}",
            "prompt": PROMPT.format(
                fields=", ".join(c["fields"]), slug=slug,
                entry=json.dumps(c["entry"], indent=1),
                va=json.dumps(c["va"].get("verdicts", {}), indent=1),
                vb=json.dumps(c["vb"].get("verdicts", {}), indent=1)) + prompt_extra,
            "schema": str(ROOT / "schema" / "adjudicate.schema.json"),
            "out": str(ROOT / "data" / "adjudicate" / f"{slug}.json"),
        })
    out = ROOT / "pipeline" / "jobs-adjudicate.jsonl"
    out.write_text("\n".join(json.dumps(j) for j in jobs) + "\n")
    print(f"wrote {len(jobs)} adjudicator jobs to {out}")


if __name__ == "__main__":
    main()
