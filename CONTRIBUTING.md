# Contributing

Thanks for improving BlastLens.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

## Guidelines

- Keep parsers small and documented. Prefer expanding tests/fixtures over silent heuristics.
- Verification tiers must stay honest: unknown ≠ false.
- Risk score and gate stay deterministic — never let a model set them.
- No secrets in the repo. Use `.env.example` as the template only.
- Human comments only where a competent engineer would leave a “why”.

## PR checklist

- [ ] Tests pass (`pytest`)
- [ ] Eval still honest (`python eval/run_eval.py`)
- [ ] Docs mention any new analyzed format (and what is still skipped)
