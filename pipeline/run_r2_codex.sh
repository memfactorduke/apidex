#!/bin/bash
# Codex (GPT-5.6 Sol) finishes what the Grok quota death left: remaining
# dual-verify jobs, then adjudication of all round-2 conflicts, then
# reconcile (new entries only) → dataset rebuild → tests.
set -e
cd "$(dirname "$0")/.."
VENVPY=pipeline/.venv/bin/python3

python3 -c "import json,pathlib; print('\n'.join(json.loads(l)['slug'] for l in pathlib.Path('data/seeds-r2/merged.jsonl').read_text().splitlines() if l.strip()))" > /tmp/r2-slugs.txt

echo "[codex-chain] phase 1: verify remainder (validate-and-rerun loop)"
for i in 1 2 3; do
  python3 pipeline/codexify_jobs.py pipeline/jobs-verify.jsonl pipeline/jobs-verify-codex.jsonl
  n=$(grep -c . pipeline/jobs-verify-codex.jsonl || true)
  echo "[codex-chain] verify round $i: $n jobs"
  if [ "$n" -eq 0 ]; then break; fi
  python3 pipeline/runner_codex.py pipeline/jobs-verify-codex.jsonl --concurrency 6 || true
  $VENVPY pipeline/validate_outputs.py schema/verify.schema.json --jobs pipeline/jobs-verify-codex.jsonl | tail -1
done

echo "[codex-chain] phase 2: adjudication loop"
for i in 1 2 3 4 5; do
  python3 pipeline/reconcile.py --emit-queue --skip-existing
  python3 pipeline/gen_adjudicate_jobs.py
  python3 pipeline/codexify_jobs.py pipeline/jobs-adjudicate.jsonl pipeline/jobs-adjudicate-codex.jsonl
  n=$(grep -c . pipeline/jobs-adjudicate-codex.jsonl || true)
  echo "[codex-chain] adjudicate round $i: $n jobs"
  if [ "$n" -eq 0 ]; then break; fi
  python3 pipeline/runner_codex.py pipeline/jobs-adjudicate-codex.jsonl --concurrency 6 || true
  $VENVPY pipeline/validate_outputs.py schema/adjudicate.schema.json --jobs pipeline/jobs-adjudicate-codex.jsonl | tail -1
  python3 pipeline/purge_punts.py --only /tmp/r2-slugs.txt | tail -1
done

echo "[codex-chain] final reconcile (new entries only)"
python3 pipeline/reconcile.py --skip-existing

echo "[codex-chain] rebuild dataset + tests"
python3 pipeline/build_dataset.py
cd mcp-server && npm test 2>&1 | tail -4
