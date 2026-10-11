# Harness integration (pipeline-first)

BlastLens is designed so a **Harness pipeline** owns execution. A tool manifest alone does **not** make a local CLI remotely callable.

## Supported flow

```
Checkout
  → Run: blastlens evidence  → out/evidence.json
  → Worker Agent: read evidence + diff → out/proposal.json
  → Run: blastlens verify    → out/report/{report.json,report.html} + gate exit code
  → Publish report artifact / require approval on exit 2 / fail on exit 1
```

Files in the shared workspace are the contract between steps.

## What you configure in the UI

1. **Project** under your account (`app.harness.io`).
2. **Model connector** for the Worker Agent (Harness AI / your provider). Store keys in **Harness secrets**, never in git.
3. **Git connector** to the repo under analysis (needed for real PRs; the bundled `examples/` works for a demo without remote).
4. **Worker Agent** from `harness/worker-agent.yaml` + prompt in `harness/worker-agent-prompt.md`.
5. **Pipeline** from `harness/pipeline.yaml` (adjust identifiers / step types to match your Harness version).

The live **worker agent URL** is whatever Harness shows after the agent is created — paste that into your submission form; do not invent one in this repo.

## Gate exit codes

| Code | Outcome | Suggested Harness handling |
| --- | --- | --- |
| 0 | `pass` | Continue |
| 2 | `approval-required` | Approval step / manual review |
| 1 | `blocked` | Fail the pipeline |

High-severity **model-observed** claims require approval by default — unknowns are not treated as safe.

## Optional MCP later

`harness/tool-manifest.json` documents the same operations if you later wrap BlastLens in a reachable MCP server and attach an MCP connector. That is optional. Pipeline-first is the path this repo ships and tests locally.

## Secrets

Never commit tokens. Use Harness Secret Manager (or equivalent) for git credentials and model keys.
