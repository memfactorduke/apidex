#!/usr/bin/env python3
"""Validate fleet output files against a schema; DELETE invalid ones so the
next runner pass regenerates them (skip-if-exists semantics).

Usage: validate_outputs.py <schema.json> <file> [file...]
       validate_outputs.py <schema.json> --jobs <jobs.jsonl>   # validate each job's `out`
Prints '<n_deleted>' as the last line.
"""
import json, sys
from pathlib import Path
from jsonschema import Draft202012Validator


def main():
    validator = Draft202012Validator(json.loads(Path(sys.argv[1]).read_text()))
    if sys.argv[2] == "--jobs":
        files = [json.loads(l)["out"] for l in Path(sys.argv[3]).read_text().splitlines() if l.strip()]
        files = [f for f in files if Path(f).exists()]
    else:
        files = sys.argv[2:]
    deleted = 0
    for f in files:
        p = Path(f)
        try:
            errs = list(validator.iter_errors(json.loads(p.read_text())))
        except Exception as e:
            errs = [e]
        if errs:
            print(f"invalid {p.name}: {str(errs[0])[:120]}")
            p.unlink()
            deleted += 1
    print(deleted)


if __name__ == "__main__":
    main()
