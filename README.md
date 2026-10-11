# BlastLens

**The agent predicts the blast radius. Repository evidence validates what it can. Unknowns stay unknown.**

BlastLens helps you answer *what might break if this change ships?* without treating an LLM guess as truth. A Harness Worker Agent (or a local heuristic) proposes impact claims; deterministic repository evidence tiers every claim into **verified**, **model-observed**, or **dropped**; a documented heuristic risk score and gate decide pass / approval-required / blocked.

This is static repository analysis of a **documented format subset**. It does not prove runtime behavior.

## Why

AI blast-radius answers hallucinate dependencies. Naive graph tools over-report. Operators need an impact set that is **evidence-backed**, with honest uncertainty when parsers cannot see a path.

## How it works

```
diff + repo
   → dependency evidence (no LLM)
   → impact proposal (Worker Agent)
   → verifier tiers each claim
   → heuristic risk score + gate
   → report.json / report.html
```

| Tier | Rule |
| --- | --- |
| **verified** | A supported, traceable dependency path or direct change backs the claim |
| **model-observed** | Plausible, but available evidence does not establish it (including “no path found”) |
| **dropped** | Malformed, invalid target, or contradicts explicit declared dependencies |

Unknown is not the same as false. A high-severity model-observed claim still requires approval by default.

## Quickstart

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

blastlens analyze `
  --repo examples\shopfleet `
  --change examples\changes\risky-checkout.diff `
  --proposal examples\changes\proposals\risky-checkout.json `
  --out out\demo
```

Open `out/demo/report.html`. Exit codes: `0` pass · `2` approval-required · `1` blocked.

Pipeline-shaped steps (what Harness runs):

```powershell
blastlens evidence --repo examples\shopfleet --change examples\changes\risky-checkout.diff --out out\evidence.json
# Worker Agent writes out\proposal.json (or use the bundled proposal / heuristic)
blastlens verify --evidence out\evidence.json --proposal examples\changes\proposals\risky-checkout.json --out out\report
```

## Example output (bundled fixture)

Against `examples/shopfleet` + `risky-checkout.diff` + the sample agent proposal:

| Target | Tier | Severity |
| --- | --- | --- |
| `service:checkout-api` | verified | high |
| `service:payments-api` | verified | critical |
| `service:inventory-api` | verified | medium |
| `service:notify-worker` | verified | low |
| `service:analytics-api` | model-observed | high |
| `service:legacy-billing` | dropped | critical |
| `totally invalid!!` | dropped | high |

Gate: **blocked** (verified critical impact on payments). Heuristic risk score is documented in the report — not an outage probability.

```text
$ python eval/run_eval.py
precision 1.0 · recall 1.0  (Verified claims vs known-good edges in the fixture)
```

## Supported evidence formats

| Analyzed | Not analyzed (by design) |
| --- | --- |
| `services/*/service.yaml` (`depends_on`, `configs`, hostname-like `env`) | Helm charts |
| Kubernetes Deployment/Service selectors, ConfigMap/Secret refs | docker-compose |
| Terraform `resource` + `depends_on` only | OpenAPI/runtime call graphs, service mesh discovery |

Every report lists `analyzed_formats` and `skipped_formats`.

## Harness Worker Agent (pipeline-first)

Preferred integration is a **real pipeline**, not a pretend remote CLI:

1. Checkout  
2. `blastlens evidence` → `out/evidence.json`  
3. Worker Agent reads evidence + diff → writes `out/proposal.json`  
4. `blastlens verify` → report + gate  

See [`docs/HARNESS.md`](docs/HARNESS.md) and files under [`harness/`](harness/).

## CLI

| Command | Purpose |
| --- | --- |
| `blastlens evidence` | Build graph + change mapping |
| `blastlens propose` | Offline heuristic proposal (demo only) |
| `blastlens verify` | Tier claims, score, gate |
| `blastlens analyze` | One-shot pipeline |
| `blastlens tool-manifest` | Emit agent tool manifest JSON |

## Scope & limits

- Evidence is only as complete as the parsers and the files you point at.
- No path found ⇒ **model-observed**, never silent “safe”.
- Risk score is a **heuristic** from criticality × tier weights + policy inputs.
- Bundled eval is small and fixture-bound — it does not claim production accuracy.

## Develop

```powershell
pip install -e ".[dev]"
pytest
python eval\run_eval.py
```

## License

MIT — see [LICENSE](LICENSE).
