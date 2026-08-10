#!/usr/bin/env python3
"""Merge research entries with verifier verdicts (and adjudicator rulings).

Decision rules per entry:
- Both verifiers pass, zero "incorrect" verdicts  -> finalize (verification: "double-confirmed")
- Any "incorrect" verdict, no adjudication yet    -> conflict queue (data/adjudicate-queue.jsonl)
- Adjudication file exists                        -> apply non-null rulings, finalize
  (verification: "adjudicated")
- Entry or adjudication says defunct              -> drop (logged)

Finalized entries land in data/final/<slug>.json with a verification block:
which fields were confirmed by both, by one, corrected, or unverifiable.

Run with --emit-queue to (re)build the adjudication queue.
"""
import json, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["base_url", "docs_url", "auth_type", "free_tier", "free_tier_limits",
          "rate_limits", "cors", "example", "description"]

APPLY = {  # adjudicator field -> how to set it on the entry
    "base_url": lambda e, v: e.__setitem__("base_url", v),
    "docs_url": lambda e, v: e.__setitem__("docs_url", v),
    "auth_type": lambda e, v: e["auth"].__setitem__("type", v),
    "free_tier": lambda e, v: e["pricing"].__setitem__("free_tier", v),
    "free_tier_limits": lambda e, v: e["pricing"].__setitem__("free_tier_limits", v),
    "rate_limits": lambda e, v: e.__setitem__("rate_limits", v),
    "example_request": lambda e, v: e["example"].__setitem__("request", v),
    "example_response_snippet": lambda e, v: e["example"].__setitem__("response_snippet", v),
    "description": lambda e, v: e.__setitem__("description", v),
    "status": lambda e, v: e.__setitem__("status", v),
}


def load(p):
    try:
        return json.loads(p.read_text())
    except FileNotFoundError:
        return None


def main():
    emit_queue = "--emit-queue" in sys.argv
    # --skip-existing: never rewrite an entry that already shipped. Round-1
    # finals carry audit-arbitration corrections that exist nowhere in
    # research/verify/adjudicate inputs; rebuilding them would erase those.
    skip_existing = "--skip-existing" in sys.argv
    finals, conflicts, dropped, waiting, preserved = 0, [], [], 0, 0
    for f in sorted((ROOT / "data" / "research").glob("*.json")):
        entry = load(f)
        slug = entry["id"]
        if skip_existing and (ROOT / "data" / "final" / f"{slug}.json").exists():
            preserved += 1
            continue
        if entry.get("status") == "defunct":
            dropped.append((slug, "researcher: defunct"))
            continue
        va = load(ROOT / "data" / "verify" / f"{slug}.a.json")
        vb = load(ROOT / "data" / "verify" / f"{slug}.b.json")
        if va is None or vb is None:
            waiting += 1
            continue
        adj = load(ROOT / "data" / "adjudicate" / f"{slug}.json")
        def v_of(v, fld):
            return v.get("verdicts", {}).get(fld, {}).get("verdict", "unverifiable")
        verdicts = {fld: (v_of(va, fld), v_of(vb, fld)) for fld in FIELDS}
        incorrect = [fld for fld, (a, b) in verdicts.items() if "incorrect" in (a, b)]
        if incorrect and adj is None:
            conflicts.append({"slug": slug, "fields": incorrect,
                              "va": va, "vb": vb, "entry": entry})
            continue
        mode = "double-confirmed"
        corrected = []
        if adj is not None:
            if adj.get("status") == "defunct":
                dropped.append((slug, "adjudicator: defunct"))
                continue
            mode = "adjudicated"
            for fld, setter in APPLY.items():
                v = adj.get(fld)
                if v is not None:
                    setter(entry, v)
                    corrected.append(fld)
        entry["verification"] = {
            "mode": mode,
            "last_checked": date.today().isoformat(),
            "fields": {fld: {"a": a, "b": b} for fld, (a, b) in verdicts.items()},
            "confirmed_by_both": [fld for fld, (a, b) in verdicts.items()
                                  if a == b == "confirm"],
            "corrected": corrected,
            "unverifiable": [fld for fld, (a, b) in verdicts.items()
                             if a == "unverifiable" and b == "unverifiable"],
        }
        (ROOT / "data" / "final" / f"{slug}.json").write_text(json.dumps(entry, indent=2))
        finals += 1
    if emit_queue:
        q = ROOT / "data" / "adjudicate-queue.jsonl"
        q.write_text("\n".join(json.dumps(c) for c in conflicts) + ("\n" if conflicts else ""))
    print(f"finalized={finals} conflicts={len(conflicts)} waiting={waiting} "
          f"dropped={len(dropped)} preserved={preserved}")
    for slug, why in dropped:
        print(f"  dropped {slug}: {why}")


if __name__ == "__main__":
    main()
