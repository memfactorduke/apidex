#!/usr/bin/env python3
"""Drive adjudication to convergence: purge punts -> reconcile -> generate ->
run fleet, repeating until no punts remain and the conflict queue is empty.

While the wave-2 verifier fleet is still running, new conflicts keep arriving;
in that case an empty round sleeps and polls rather than exiting.
"""
import subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_ROUNDS = 60


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)


def verify_fleet_running():
    return subprocess.run(["pgrep", "-f", "jobs-verify"], capture_output=True).returncode == 0


for rnd in range(1, MAX_ROUNDS + 1):
    purged = int(run(["python3", "pipeline/purge_punts.py"]).stdout.strip().splitlines()[-1])
    run(["python3", "pipeline/reconcile.py", "--emit-queue"])
    gen = run(["python3", "pipeline/gen_adjudicate_jobs.py"]).stdout
    njobs = int(gen.split("wrote ")[1].split(" ")[0])
    print(f"[round {rnd}] purged={purged} queued={njobs}", flush=True)
    if njobs == 0:
        if verify_fleet_running():
            print(f"[round {rnd}] queue empty, verifiers still running — sleeping 300s", flush=True)
            time.sleep(300)
            continue
        print("converged: no punts, no conflicts, verifiers done", flush=True)
        sys.exit(0)
    r = subprocess.run(["python3", "pipeline/runner.py", "pipeline/jobs-adjudicate.jsonl",
                        "--concurrency", "4"], cwd=ROOT)
    if r.returncode == 42:
        print("quota exhausted during adjudication", flush=True)
        sys.exit(42)
print("max rounds reached", flush=True)
sys.exit(1)
