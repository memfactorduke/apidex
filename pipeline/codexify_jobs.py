#!/usr/bin/env python3
"""Convert Grok fleet jobs (grammar-constrained via --json-schema) into Codex
jobs: bake the schema into the prompt as explicit output instructions, and
filter to jobs whose output doesn't exist yet.

Usage: codexify_jobs.py <in.jsonl> <out.jsonl>
"""
import json, sys
from pathlib import Path


def main():
    src, dst = sys.argv[1], sys.argv[2]
    jobs = []
    for line in Path(src).read_text().splitlines():
        if not line.strip():
            continue
        j = json.loads(line)
        if Path(j["out"]).exists():
            continue
        schema = json.loads(Path(j["schema"]).read_text())
        j["prompt"] += (
            "\n\nOUTPUT FORMAT — MANDATORY: after your research, output exactly one JSON "
            "object as the LAST thing in your response, conforming to this JSON Schema "
            "(all required fields present, no extra properties, correct types/enums):\n"
            + json.dumps(schema)
            + "\nNo prose, no markdown fences after the JSON object."
        )
        del j["schema"]
        jobs.append(j)
    Path(dst).write_text("\n".join(json.dumps(j) for j in jobs) + ("\n" if jobs else ""))
    print(f"wrote {len(jobs)} codex jobs to {dst}")


if __name__ == "__main__":
    main()
