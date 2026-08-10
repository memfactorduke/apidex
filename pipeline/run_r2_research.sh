#!/bin/bash
# Chain: wait for round-2 seed fleet → merge → gen research jobs → research fleet.
set -e
cd "$(dirname "$0")/.."

while pgrep -f "runner.py pipeline/jobs-seed-r2" > /dev/null; do sleep 30; done
echo "[chain] seed fleet done, merging"
python3 pipeline/merge_seeds_r2.py
python3 pipeline/gen_research_jobs.py data/seeds-r2/merged.jsonl jobs-research-r2.jsonl
echo "[chain] launching research fleet"
python3 pipeline/runner.py pipeline/jobs-research-r2.jsonl --concurrency 8
