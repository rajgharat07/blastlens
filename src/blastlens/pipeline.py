"""End-to-end analyze pipeline used by CLI and Harness steps."""

from __future__ import annotations

from pathlib import Path

import yaml

from blastlens.diff import load_change, map_files_to_nodes
from blastlens.gate import decide_gate
from blastlens.graph.builder import build_graph
from blastlens.propose import heuristic_propose
from blastlens.report import dump_evidence_json, write_html, write_json
from blastlens.schema import (
    AnalysisReport,
    Criticality,
    EvidenceBundle,
    ImpactProposal,
)
from blastlens.scoring import score_findings
from blastlens.verify import verify_proposal


def load_catalog(root: Path) -> dict[str, Criticality]:
    path = root / ".blastlens" / "catalog.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    services = data.get("services") or {}
    out: dict[str, Criticality] = {}
    for name, meta in services.items():
        if isinstance(meta, str):
            out[name] = Criticality(meta)
        elif isinstance(meta, dict) and "criticality" in meta:
            out[name] = Criticality(str(meta["criticality"]))
    return out


def build_evidence(repo: Path, change_path: Path) -> EvidenceBundle:
    graph = build_graph(repo)
    change = load_change(change_path)
    changed_nodes = map_files_to_nodes(change, graph)
    catalog = load_catalog(repo)
    # apply catalog criticality onto service nodes
    for n in graph.nodes:
        if n.kind == "service":
            key = n.id.removeprefix("service:")
            if key in catalog:
                n.criticality = catalog[key]
    return EvidenceBundle(
        graph=graph,
        change=change,
        changed_nodes=changed_nodes,
        catalog=catalog,
    )


def load_proposal(path: Path) -> ImpactProposal:
    return ImpactProposal.model_validate_json(path.read_text(encoding="utf-8"))


def run_analyze(
    repo: Path,
    change_path: Path,
    out_dir: Path,
    *,
    proposal_path: Path | None = None,
    use_heuristic: bool = True,
) -> AnalysisReport:
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence = build_evidence(repo, change_path)
    dump_evidence_json(evidence, out_dir / "evidence.json")

    if proposal_path:
        proposal = load_proposal(proposal_path)
    elif use_heuristic:
        proposal = heuristic_propose(evidence)
    else:
        raise ValueError("proposal_path required when use_heuristic is False")

    (out_dir / "proposal.json").write_text(proposal.model_dump_json(indent=2), encoding="utf-8")

    findings = verify_proposal(evidence, proposal)
    risk = score_findings(findings)
    gate = decide_gate(findings, risk)

    report = AnalysisReport(
        findings=findings,
        risk=risk,
        gate=gate,
        narrative=proposal.narrative,
        analyzed_formats=evidence.graph.analyzed_formats,
        skipped_formats=evidence.graph.skipped_formats,
        changed_nodes=evidence.changed_nodes,
        proposer=proposal.proposer,
    )
    write_json(report, out_dir / "report.json")
    write_html(report, out_dir / "report.html")
    return report
