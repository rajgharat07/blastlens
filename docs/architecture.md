# Architecture

Thesis: *The agent predicts the blast radius. Repository evidence validates what it can. Unknowns stay unknown.*

## Pipeline

```
change (diff)
  + repo files
      → graph builders (deterministic)
      → evidence.json
      → impact proposal (Worker Agent or local heuristic)
      → verifier (tiers)
      → heuristic risk score + gate
      → report.json / report.html
```

## Layers

1. **Evidence** — parsers build a dependency graph from a *documented subset*:
   - `services/*/service.yaml` (`depends_on`, `configs`, hostname-like `env`)
   - Kubernetes Deployments/Services (selectors) + ConfigMap/Secret refs
   - Terraform `resource` blocks + `depends_on` only
2. **Proposal** — an agent (or offline heuristic) claims impacted targets. Claims are untrusted.
3. **Verify** — each claim becomes:
   - **verified** — traceable path / direct change backs it
   - **model-observed** — plausible, evidence insufficient (including “no path found”)
   - **dropped** — malformed, or contradicts explicit declared dependencies
4. **Score + gate** — deterministic formulas/policy. The model never sets the score or gate.

## Trust rebuttal

> Isn't this just an LLM wrapper?

No. The product is the trust loop. Remove the agent and you still have evidence + a local heuristic. Remove verification and you get untrusted guesses. Static repo analysis does **not** claim to prove runtime behavior — it validates what the analyzed formats can support.
