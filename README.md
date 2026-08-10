# apidex — build pipeline

This repo builds **[apidex](mcp-server/)**: an MCP server giving coding agents a verified
directory of public APIs. The dataset is produced by a fleet of Grok 4.5 agents orchestrated
by Claude (Fable 5), with every fact cross-checked by independent verification passes.

**Browse the directory:** https://memfactorduke.github.io/apidex/ · **Install:**
`claude mcp add apidex -- npx -y apidex`

## Layout

- `mcp-server/` — the publishable npm package (`npx apidex`), TypeScript MCP server
- `site/` — the static directory site (zero-dep SSG), deployed to GitHub Pages on push
- `schema/` — JSON Schemas constraining every agent's output (`--json-schema` decoding)
- `pipeline/` — fleet runner + per-phase job generators
- `data/` — pipeline artifacts: `seeds/` → `research/` → `verify/` → `adjudicate/` → `final/`
- `logs/` — fleet logs, usage/burn tracking, machine-check results

## Pipeline

```
gen_seed_jobs.py ─▶ runner.py ─▶ data/seeds/           (22 category listers)
merge_seeds.py                                          (dedupe → merged.jsonl)
gen_research_jobs.py ─▶ runner.py ─▶ data/research/    (1 researcher per API)
machine_check.py                                        (curl liveness + schema, deterministic)
gen_verify_jobs.py ─▶ runner.py ─▶ data/verify/        (2 independent verifiers per API)
reconcile.py --emit-queue                               (merge verdicts; conflicts → queue)
gen_adjudicate_jobs.py ─▶ runner.py ─▶ data/adjudicate/ (3rd agent settles disputes)
reconcile.py                                            (apply rulings → data/final/)
build_dataset.py ─▶ mcp-server/data/apis.json
```

`runner.py` executes jobs as parallel `grok -p … --json-schema` calls with fleet-wide
rate-limit backoff; it is restartable (skips jobs whose output exists). `pipeline/burn.py`
shows cumulative token/cost burn.
