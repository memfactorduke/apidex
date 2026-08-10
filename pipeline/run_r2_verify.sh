#!/bin/bash
# Chain: wait for round-2 research fleet → machine checks → dual-verify fleet →
# adjudication loop → reconcile (new entries only) → rebuild dataset → tests.
set -e
cd "$(dirname "$0")/.."

while pgrep -f "runner.py pipeline/jobs-research-r2" > /dev/null; do sleep 60; done
echo "[chain] research fleet done"

echo "[chain] machine checks (all research entries, fresh liveness sweep)"
pipeline/.venv/bin/python3 pipeline/machine_check.py > logs/machine_check_r2.log 2>&1 || true
tail -1 logs/machine_check_r2.log

echo "[chain] generating verify jobs (round-1 outputs exist, runner skips them)"
python3 pipeline/gen_verify_jobs.py
python3 pipeline/runner.py pipeline/jobs-verify.jsonl --concurrency 8

echo "[chain] adjudication loop"
python3 pipeline/adjudicate_loop.py

echo "[chain] final reconcile (new entries only)"
python3 pipeline/reconcile.py --skip-existing

echo "[chain] rebuild dataset + tests"
python3 pipeline/build_dataset.py
cd mcp-server && npm test 2>&1 | tail -4
