#!/usr/bin/env python3
"""Parallel Grok fleet runner.

Reads a JSONL jobs file, runs each job as `grok -p ... -m grok-4.5 --sandbox
read-only --json-schema <schema>`, writes the constrained JSON to the job's out
path. Restartable: jobs whose out file already exists are skipped.

Rate-limit strategy: on a limit/capacity error the whole fleet pauses (shared
backoff with escalating waits). If the fleet hits MAX_CONSECUTIVE_LIMIT_WAVES
pauses with no successful job in between, we assume the weekly quota is
exhausted and exit 42 — mission accomplished.

Usage: runner.py jobs.jsonl --concurrency 8 --usage-log logs/usage.jsonl
"""
import argparse, json, os, re, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_CWD = ROOT / "pipeline" / "agent-cwd"
LIMIT_RE = re.compile(r"rate.?limit|429|too many requests|capacity|overloaded|quota|usage limit|limit (reached|exceeded)", re.I)
BACKOFFS = [120, 300, 600, 900, 1800]
MAX_CONSECUTIVE_LIMIT_WAVES = 6
CALL_TIMEOUT = 1200  # 20 min per agent call

pause_lock = threading.Lock()
pause_until = 0.0
limit_waves = 0        # consecutive fleet pauses with no success in between
stats_lock = threading.Lock()
stats = {"ok": 0, "failed": 0, "skipped": 0, "tokens": 0, "cost": 0.0}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def decode_envelope(stdout):
    """Find the result envelope (object with a 'text' key) in stdout, which may
    contain multiple concatenated JSON documents or stray non-JSON lines."""
    dec = json.JSONDecoder()
    i = stdout.find("{")
    while i != -1:
        try:
            obj, end = dec.raw_decode(stdout, i)
        except ValueError:
            i = stdout.find("{", i + 1)
            continue
        if isinstance(obj, dict) and "text" in obj:
            return obj
        i = stdout.find("{", end)
    raise ValueError("no envelope with 'text' key in stdout")


def wait_if_paused():
    while True:
        with pause_lock:
            remaining = pause_until - time.time()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 15))


def trigger_pause():
    """Fleet-wide backoff. Returns False if we've decided quota is exhausted."""
    global pause_until, limit_waves
    with pause_lock:
        if time.time() >= pause_until:  # first worker to report this wave
            wave = min(limit_waves, len(BACKOFFS) - 1)
            delay = BACKOFFS[wave]
            limit_waves += 1
            pause_until = time.time() + delay
            log(f"RATE-LIMIT wave {limit_waves}: fleet paused {delay}s")
        return limit_waves < MAX_CONSECUTIVE_LIMIT_WAVES


def note_success():
    global limit_waves
    with pause_lock:
        limit_waves = 0


def run_job(job, usage_log):
    out_path = Path(job["out"])
    if out_path.exists():
        with stats_lock:
            stats["skipped"] += 1
        return "skipped"
    schema = Path(job["schema"]).read_text()
    cmd = ["grok", "-p", job["prompt"], "-m", "grok-4.5",
           "--sandbox", "read-only", "--json-schema", schema,
           "--cwd", str(AGENT_CWD)]
    attempts = 0
    while attempts < 3:
        wait_if_paused()
        attempts += 1
        t0 = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=CALL_TIMEOUT)
        except subprocess.TimeoutExpired:
            log(f"{job['id']}: timeout (attempt {attempts})")
            continue
        # Rate-limit detection ONLY on failure output (stderr / failed stdout).
        # Successful output legitimately talks about API rate limits — never
        # scan it for limit patterns.
        if r.returncode != 0 or not r.stdout.strip():
            err_blob = r.stderr + ("" if r.stdout.strip() else "\n" + r.stdout)
            if r.returncode != 0:
                err_blob += "\n" + r.stdout[-500:]
            if LIMIT_RE.search(err_blob):
                if not trigger_pause():
                    return "quota_exhausted"
                attempts -= 1  # limit waits don't consume attempts
                continue
            log(f"{job['id']}: error rc={r.returncode} (attempt {attempts}): {err_blob.strip()[:200]}")
            time.sleep(10)
            continue
        try:
            envelope = decode_envelope(r.stdout)
            # text may carry trailing junk after the schema-constrained JSON
            inner, _ = json.JSONDecoder().raw_decode(envelope["text"].strip())
        except (ValueError, KeyError) as e:
            log(f"{job['id']}: parse failure (attempt {attempts}): {e}")
            continue
        note_success()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(inner, indent=2))
        usage = envelope.get("usage", {})
        rec = {"id": job["id"], "tokens": usage.get("total_tokens", 0),
               "output_tokens": usage.get("output_tokens", 0),
               "cost_usd": envelope.get("total_cost_usd", 0),
               "secs": round(time.time() - t0)}
        with stats_lock:
            stats["ok"] += 1
            stats["tokens"] += rec["tokens"]
            stats["cost"] += rec["cost_usd"] or 0
            with open(usage_log, "a") as f:
                f.write(json.dumps(rec) + "\n")
        log(f"{job['id']}: OK in {rec['secs']}s ({rec['tokens']} tok, ${rec['cost_usd']:.3f}) "
            f"[done {stats['ok']}, failed {stats['failed']}]")
        return "ok"
    with stats_lock:
        stats["failed"] += 1
    log(f"{job['id']}: FAILED after {attempts} attempts")
    return "failed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--usage-log", default=str(ROOT / "logs" / "usage.jsonl"))
    args = ap.parse_args()
    jobs = [json.loads(l) for l in Path(args.jobs).read_text().splitlines() if l.strip()]
    log(f"fleet start: {len(jobs)} jobs, concurrency {args.concurrency}")
    exhausted = False
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futs = {pool.submit(run_job, j, args.usage_log): j for j in jobs}
        for fut in as_completed(futs):
            if fut.result() == "quota_exhausted":
                exhausted = True
                for f in futs:
                    f.cancel()
                break
    log(f"fleet done: ok={stats['ok']} failed={stats['failed']} skipped={stats['skipped']} "
        f"tokens={stats['tokens']} cost=${stats['cost']:.2f}")
    if exhausted:
        log("QUOTA EXHAUSTED — mission accomplished")
        sys.exit(42)
    sys.exit(0 if stats["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
