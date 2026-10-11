"""JSON + standalone HTML report writers."""

from __future__ import annotations

import json
from pathlib import Path

from blastlens.schema import AnalysisReport, Tier

_TIER_COLOR = {
    Tier.VERIFIED: "#3dd68c",
    Tier.MODEL_OBSERVED: "#e8c46a",
    Tier.DROPPED: "#e97b77",
}


def write_json(report: AnalysisReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")


def write_html(report: AnalysisReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for f in report.findings:
        color = _TIER_COLOR[f.tier]
        ev = "<br>".join(e.detail for e in f.evidence) or f.drop_reason or "—"
        rows.append(
            f"<tr>"
            f"<td><code>{_esc(f.target)}</code></td>"
            f"<td><span class='tier' style='color:{color}'>{f.tier.value}</span></td>"
            f"<td>{f.severity.value}</td>"
            f"<td>{_esc(f.rationale)}</td>"
            f"<td class='ev'>{ev}</td>"
            f"</tr>"
        )

    gate_color = {
        "pass": "#3dd68c",
        "approval-required": "#e8c46a",
        "blocked": "#e97b77",
    }.get(report.gate.outcome.value, "#f2f2eb")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>BlastLens report</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin:0; font-family: ui-monospace, Cascadia Mono, Menlo, monospace;
         background:#121f1c; color:#f2f2eb; padding:2rem; }}
  h1 {{ font-size:1.6rem; margin:0 0 .25rem; }}
  .sub {{ color:#9ab5ae; margin-bottom:1.5rem; }}
  .cards {{ display:flex; gap:1rem; flex-wrap:wrap; margin-bottom:1.5rem; }}
  .card {{ background:#1e332e; border:1px solid #2a453e; border-radius:8px;
           padding:1rem 1.25rem; min-width:160px; }}
  .card .v {{ font-size:1.4rem; font-weight:700; }}
  table {{ width:100%; border-collapse:collapse; background:#1e332e; }}
  th, td {{ text-align:left; padding:.65rem .75rem; border-bottom:1px solid #2a453e;
            vertical-align:top; font-size:.85rem; }}
  th {{ color:#9ab5ae; font-weight:600; }}
  .tier {{ font-weight:700; text-transform:uppercase; font-size:.75rem; }}
  .ev {{ color:#9ab5ae; max-width:28rem; }}
  code {{ color:#a8d5c8; }}
  .gate {{ color:{gate_color}; font-weight:700; }}
  ul.reasons {{ color:#9ab5ae; }}
</style>
</head>
<body>
  <h1>BlastLens</h1>
  <p class="sub">Repository evidence validates what it can. Unknowns stay unknown.</p>
  <div class="cards">
    <div class="card"><div class="v">{report.risk.value}</div>risk ({report.risk.label})</div>
    <div class="card"><div class="v gate">{report.gate.outcome.value}</div>gate</div>
    <div class="card"><div class="v">{sum(1 for f in report.findings if f.tier==Tier.VERIFIED)}</div>verified</div>
    <div class="card"><div class="v">{sum(1 for f in report.findings if f.tier==Tier.MODEL_OBSERVED)}</div>model-observed</div>
    <div class="card"><div class="v">{sum(1 for f in report.findings if f.tier==Tier.DROPPED)}</div>dropped</div>
  </div>
  <p>{_esc(report.narrative)}</p>
  <p class="sub">Changed nodes: {", ".join(f"<code>{_esc(n)}</code>" for n in report.changed_nodes) or "—"}
  · proposer: {_esc(report.proposer)}</p>
  <table>
    <thead><tr><th>Target</th><th>Tier</th><th>Severity</th><th>Rationale</th><th>Evidence</th></tr></thead>
    <tbody>
      {"".join(rows) or "<tr><td colspan=5>No findings</td></tr>"}
    </tbody>
  </table>
  <h2 style="margin-top:1.5rem;font-size:1rem;">Gate reasons</h2>
  <ul class="reasons">{"".join(f"<li>{_esc(r)}</li>" for r in report.gate.reasons)}</ul>
  <h2 style="margin-top:1.5rem;font-size:1rem;">Analyzed formats</h2>
  <ul class="reasons">{"".join(f"<li>{_esc(x)}</li>" for x in report.analyzed_formats)}</ul>
  <h2 style="margin-top:1rem;font-size:1rem;">Not analyzed</h2>
  <ul class="reasons">{"".join(f"<li>{_esc(x)}</li>" for x in report.skipped_formats)}</ul>
  <p class="sub" style="margin-top:2rem;">Heuristic risk score — not an outage probability.
  Formula: {_esc(report.risk.formula)}</p>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def _esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def dump_evidence_json(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(obj, "model_dump"):
        path.write_text(json.dumps(obj.model_dump(mode="json"), indent=2), encoding="utf-8")
    else:
        path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
