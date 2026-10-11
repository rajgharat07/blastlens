"""Thin tool interface for Worker Agents / MCP-style wrappers.

Pipeline-first is the supported path: evidence → agent proposal file → verify.
These helpers keep the contract stable if you later expose an MCP server.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from blastlens.pipeline import build_evidence, run_analyze
from blastlens.schema import ImpactProposal


TOOLS = [
    {
        "name": "blastlens_build_evidence",
        "description": "Build deterministic dependency evidence for a repo + change diff.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "change": {"type": "string"},
                "out": {"type": "string"},
            },
            "required": ["repo", "change", "out"],
        },
    },
    {
        "name": "blastlens_verify_proposal",
        "description": "Verify an impact proposal JSON against evidence; write report + gate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "change": {"type": "string"},
                "proposal": {"type": "string"},
                "out": {"type": "string"},
            },
            "required": ["repo", "change", "proposal", "out"],
        },
    },
]


def tool_manifest() -> dict[str, Any]:
    return {
        "name": "blastlens",
        "version": "0.1.0",
        "description": "Evidence-first blast-radius tools for Harness Worker Agents",
        "tools": TOOLS,
        "notes": (
            "Preferred integration is pipeline-first shared workspace files, "
            "not remote invocation of a laptop CLI. See docs/HARNESS.md."
        ),
    }


def dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "blastlens_build_evidence":
        evidence = build_evidence(Path(args["repo"]), Path(args["change"]))
        out = Path(args["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(evidence.model_dump_json(indent=2), encoding="utf-8")
        return {"ok": True, "evidence": str(out), "changed_nodes": evidence.changed_nodes}

    if name == "blastlens_verify_proposal":
        report = run_analyze(
            Path(args["repo"]),
            Path(args["change"]),
            Path(args["out"]),
            proposal_path=Path(args["proposal"]),
            use_heuristic=False,
        )
        return {
            "ok": True,
            "gate": report.gate.outcome.value,
            "risk": report.risk.value,
            "report": str(Path(args["out"]) / "report.json"),
        }

    raise ValueError(f"unknown tool: {name}")


def validate_proposal_dict(data: dict[str, Any]) -> ImpactProposal:
    return ImpactProposal.model_validate(data)


def write_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tool_manifest(), indent=2), encoding="utf-8")
