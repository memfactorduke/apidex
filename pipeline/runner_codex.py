#!/usr/bin/env python3
"""Parallel Codex (GPT-5.6 Sol) fleet runner — the Codex-sub-burning sibling of
runner.py. Reads the same JSONL job format (id, prompt, out; no schema support),
runs `codex exec -s read-only`, extracts the last JSON object from stdout.
"""
import argparse, json, re, subprocess, threading, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIMIT_RE = re.compile(r"rate.?limit|429|too many requests|usage limit|quota|capacity|overloaded", re.I)
BACKOFFS = [120, 300, 600, 900, 1800]
MAX_WAVES = 6
CALL_TIMEOUT = 1500

pause_lock = threading.Lock()
pause_until = 0.0
waves = 0
stats_lock = threading.Lock()
stats = {"ok": 0, "failed": 0, "skipped": 0, "tokens": 0}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def last_json(stdout):
    """Extract the last decodable JSON object from stdout."""
    dec = json.JSONDecoder()
    best = None
    i = stdout.find("{")
    while i != -1:
        try:
            obj, end = dec.raw_decode(stdout, i)
            best = obj
            i = stdout.find("{", end)
        except ValueError:
            i = stdout.find("{", i + 1)
    if best is None:
        raise ValueError("no JSON object in stdout")
    return best


def wait_paused():
    while True:
        with pause_lock:
            rem = pause_until - time.time()
        if rem <= 0:
            return
        time.sleep(min(rem, 15))


def trigger_pause():
    global pause_until, waves
    with pause_lock:
        if time.time() >= pause_until:
            delay = BACKOFFS[min(waves, len(BACKOFFS) - 1)]
            waves += 1
            pause_until = time.time() + delay
            log(f"RATE-LIMIT wave {waves}: paused {delay}s")
        return waves < MAX_WAVES


def run_job(job):
    global waves
    out_path = Path(job["out"])
    if out_path.exists():
        with stats_lock:
            stats["skipped"] += 1
        return "skipped"
    attempts = 0
    while attempts < 3:
        wait_paused()
        attempts += 1
        t0 = time.time()
        try:
            r = subprocess.run(["codex", "exec", "-s", "read-only", job["prompt"]],
                               capture_output=True, text=True, timeout=CALL_TIMEOUT,
                               cwd=ROOT / "pipeline" / "agent-cwd")
        except subprocess.TimeoutExpired:
            log(f"{job['id']}: timeout (attempt {attempts})")
            continue
        if r.returncode != 0:
            blob = r.stderr + r.stdout[-300:]
            if LIMIT_RE.search(blob):
                if not trigger_pause():
                    return "quota_exhausted"
                attempts -= 1
                continue
            log(f"{job['id']}: rc={r.returncode} (attempt {attempts}): {blob.strip()[:200]}")
            time.sleep(10)
            continue
        try:
            result = last_json(r.stdout)
        except ValueError as e:
            log(f"{job['id']}: parse failure (attempt {attempts}): {e}")
            continue
        with pause_lock:
            waves = 0
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2))
        m = re.search(r"tokens used\s*\n?\s*([\d,]+)", r.stdout)
        toks = int(m.group(1).replace(",", "")) if m else 0
        with stats_lock:
            stats["ok"] += 1
            stats["tokens"] += toks
        log(f"{job['id']}: OK in {round(time.time()-t0)}s ({toks} tok) "
            f"[done {stats['ok']}, failed {stats['failed']}]")
        return "ok"
    with stats_lock:
        stats["failed"] += 1
    log(f"{job['id']}: FAILED")
    return "failed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs")
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()
    jobs = [json.loads(l) for l in Path(args.jobs).read_text().splitlines() if l.strip()]
    log(f"codex fleet start: {len(jobs)} jobs, concurrency {args.concurrency}")
    exhausted = False
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futs = {pool.submit(run_job, j): j for j in jobs}
        for fut in as_completed(futs):
            if fut.result() == "quota_exhausted":
                exhausted = True
                for f in futs:
                    f.cancel()
                break
    log(f"codex fleet done: ok={stats['ok']} failed={stats['failed']} "
        f"skipped={stats['skipped']} tokens={stats['tokens']}")
    sys.exit(42 if exhausted else (0 if stats["failed"] == 0 else 1))


if __name__ == "__main__":
    main()
