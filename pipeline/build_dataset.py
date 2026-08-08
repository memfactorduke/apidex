#!/usr/bin/env python3
"""Bundle data/final/*.json into mcp-server/data/apis.json."""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    apis = [json.loads(f.read_text())
            for f in sorted((ROOT / "data" / "final").glob("*.json"))]
    apis = [a for a in apis if a.get("status") != "defunct"]
    out = {"generated": date.today().isoformat(), "count": len(apis), "apis": apis}
    dest = ROOT / "mcp-server" / "data" / "apis.json"
    dest.write_text(json.dumps(out, indent=1))
    cats = {}
    for a in apis:
        cats[a["category"]] = cats.get(a["category"], 0) + 1
    print(f"bundled {len(apis)} APIs into {dest}")
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")


if __name__ == "__main__":
    main()
