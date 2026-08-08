#!/usr/bin/env python3
"""Deterministic verification pass over researched entries.

Checks per entry:
- validates against schema/entry.schema.json
- base_url domain resolves and responds (any HTTP status < 500 counts as alive:
  API roots legitimately 404/401/403)
- docs_url responds < 400 after redirects
- https flag consistent with base_url scheme

Writes logs/machine_check.jsonl and prints a summary. Entries with flags go to
data/rework-queue.txt for agent rework.
"""
import concurrent.futures as cf
import json, subprocess, sys
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "entry.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)
UA = "Mozilla/5.0 (compatible; apidex-verifier/1.0)"


def http_status(url, method="GET"):
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-L",
             "--max-time", "20", "-A", UA, "-X", method, url],
            capture_output=True, text=True, timeout=30)
        return int(r.stdout.strip() or 0)
    except Exception:
        return 0


def check_entry(path):
    entry = json.loads(path.read_text())
    flags = []
    schema_errors = [f"{'/'.join(map(str, e.path))}: {e.message[:80]}"
                     for e in VALIDATOR.iter_errors(entry)]
    if schema_errors:
        flags.append(f"schema: {'; '.join(schema_errors[:3])}")
    base_code = http_status(entry.get("base_url", ""))
    docs_code = http_status(entry.get("docs_url", ""))
    if base_code == 0 or base_code >= 500:
        flags.append(f"base_url dead (http {base_code})")
    if docs_code == 0 or docs_code >= 400:
        flags.append(f"docs_url bad (http {docs_code})")
    if entry.get("https") and not entry.get("base_url", "").startswith("https://"):
        flags.append("https flag inconsistent with base_url")
    if entry.get("status") == "defunct":
        flags.append("researcher marked defunct")
    return {"id": entry.get("id", path.stem), "file": path.name,
            "base_http": base_code, "docs_http": docs_code, "flags": flags}


def main():
    files = sorted((ROOT / "data" / "research").glob("*.json"))
    if not files:
        sys.exit("no research files yet")
    results = []
    with cf.ThreadPoolExecutor(max_workers=16) as pool:
        for res in pool.map(check_entry, files):
            results.append(res)
            mark = "FLAG" if res["flags"] else "ok"
            print(f"{mark:4} {res['id']}: base={res['base_http']} docs={res['docs_http']}"
                  + (f" | {'; '.join(res['flags'])}" if res["flags"] else ""), flush=True)
    log = ROOT / "logs" / "machine_check.jsonl"
    log.write_text("\n".join(json.dumps(r) for r in results) + "\n")
    flagged = [r for r in results if r["flags"]]
    (ROOT / "data" / "rework-queue.txt").write_text(
        "\n".join(r["id"] for r in flagged) + ("\n" if flagged else ""))
    print(f"\n{len(results)} checked, {len(flagged)} flagged -> data/rework-queue.txt")


if __name__ == "__main__":
    main()
