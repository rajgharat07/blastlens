"""BlastLens CLI — pipeline steps and one-shot analyze."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

from blastlens import __version__
from blastlens.agent import tool_manifest, write_manifest
from blastlens.gate import exit_code
from blastlens.pipeline import build_evidence, load_proposal, run_analyze
from blastlens.propose import heuristic_propose
from blastlens.report import dump_evidence_json, write_html, write_json
from blastlens.schema import AnalysisReport
from blastlens.scoring import score_findings
from blastlens.verify import verify_proposal
from blastlens.gate import decide_gate

app = typer.Typer(
    name="blastlens",
    help="Evidence-first blast-radius analysis. Unknowns stay unknown.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Print package version."""
    rprint(__version__)


@app.command()
def evidence(
    repo: Path = typer.Option(..., exists=True, file_okay=False, help="Repo root to analyze"),
    change: Path = typer.Option(..., exists=True, dir_okay=False, help="Unified diff or file list"),
    out: Path = typer.Option(Path("out/evidence.json"), help="Evidence JSON path"),
) -> None:
    """Build deterministic dependency evidence (no LLM)."""
    bundle = build_evidence(repo, change)
    dump_evidence_json(bundle, out)
    rprint(
        f"[green]evidence[/green] nodes={len(bundle.graph.nodes)} "
        f"edges={len(bundle.graph.edges)} changed={bundle.changed_nodes}"
    )
    rprint(f"wrote {out}")


@app.command()
def propose(
    evidence_path: Path = typer.Option(..., "--evidence", exists=True, dir_okay=False),
    out: Path = typer.Option(Path("out/proposal.json")),
) -> None:
    """Emit a local heuristic proposal (offline demo only)."""
    from blastlens.schema import EvidenceBundle

    bundle = EvidenceBundle.model_validate_json(evidence_path.read_text(encoding="utf-8"))
    proposal = heuristic_propose(bundle)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(proposal.model_dump_json(indent=2), encoding="utf-8")
    rprint(f"[yellow]heuristic proposal[/yellow] claims={len(proposal.impacts)} → {out}")


@app.command()
def verify(
    evidence_path: Path = typer.Option(..., "--evidence", exists=True, dir_okay=False),
    proposal: Path = typer.Option(..., exists=True, dir_okay=False),
    out: Path = typer.Option(Path("out/report"), file_okay=False),
) -> None:
    """Verify a proposal against evidence; write report + evaluate gate."""
    from blastlens.schema import EvidenceBundle

    bundle = EvidenceBundle.model_validate_json(evidence_path.read_text(encoding="utf-8"))
    prop = load_proposal(proposal)
    findings = verify_proposal(bundle, prop)
    risk = score_findings(findings)
    gate = decide_gate(findings, risk)
    report = AnalysisReport(
        findings=findings,
        risk=risk,
        gate=gate,
        narrative=prop.narrative,
        analyzed_formats=bundle.graph.analyzed_formats,
        skipped_formats=bundle.graph.skipped_formats,
        changed_nodes=bundle.changed_nodes,
        proposer=prop.proposer,
    )
    out.mkdir(parents=True, exist_ok=True)
    write_json(report, out / "report.json")
    write_html(report, out / "report.html")
    rprint(
        f"[cyan]gate={gate.outcome.value}[/cyan] risk={risk.value} "
        f"findings={len(findings)} → {out}"
    )
    raise typer.Exit(code=exit_code(gate))


@app.command()
def analyze(
    repo: Path = typer.Option(..., exists=True, file_okay=False),
    change: Path = typer.Option(..., exists=True, dir_okay=False),
    out: Path = typer.Option(Path("out/run"), file_okay=False),
    proposal: Optional[Path] = typer.Option(
        None, help="Agent proposal JSON; omit to use local heuristic proposer"
    ),
) -> None:
    """One-shot: evidence → proposal → verify → report → gate exit code."""
    report = run_analyze(
        repo,
        change,
        out,
        proposal_path=proposal,
        use_heuristic=proposal is None,
    )
    rprint(
        f"[bold]BlastLens[/bold] gate=[cyan]{report.gate.outcome.value}[/cyan] "
        f"risk={report.risk.value} ({report.risk.label})"
    )
    for f in report.findings:
        rprint(f"  {f.tier.value:16} {f.severity.value:8} {f.target}")
    rprint(f"report: {out / 'report.html'}")
    raise typer.Exit(code=exit_code(report.gate))


@app.command("tool-manifest")
def tool_manifest_cmd(
    out: Path = typer.Option(Path("harness/tool-manifest.json")),
) -> None:
    """Write the agent tool manifest JSON."""
    write_manifest(out)
    rprint(json.dumps(tool_manifest(), indent=2))


if __name__ == "__main__":
    app()
