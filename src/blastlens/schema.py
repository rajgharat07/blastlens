"""Data contracts for evidence, proposals, verified findings, and gates."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Tier(str, Enum):
    VERIFIED = "verified"
    MODEL_OBSERVED = "model-observed"
    DROPPED = "dropped"


class GateOutcome(str, Enum):
    PASS = "pass"
    APPROVAL_REQUIRED = "approval-required"
    BLOCKED = "blocked"


class Criticality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EdgeKind(str, Enum):
    SERVICE_CALL = "service-call"
    K8S_SELECTOR = "k8s-selector"
    K8S_CONFIGMAP = "k8s-configmap"
    K8S_SECRET = "k8s-secret"
    IAC_REF = "iac-ref"
    SHARED_CONFIG = "shared-config"


class GraphNode(BaseModel):
    id: str
    kind: str  # service | k8s-service | k8s-deployment | configmap | secret | iac-resource
    path: str = ""
    labels: dict[str, str] = Field(default_factory=dict)
    criticality: Criticality = Criticality.MEDIUM


class GraphEdge(BaseModel):
    source: str
    target: str
    kind: EdgeKind
    evidence: str  # human-readable locator: file:line or path#key
    weight: float = 1.0


class DependencyGraph(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    analyzed_formats: list[str] = Field(default_factory=list)
    skipped_formats: list[str] = Field(default_factory=list)
    root: str = ""

    def node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}

    def neighbors(self, node_id: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.source == node_id or e.target == node_id]

    def path_exists(self, a: str, b: str, *, max_hops: int = 4) -> list[GraphEdge] | None:
        """BFS undirected path; returns edges if found."""
        if a == b:
            return []
        ids = self.node_ids()
        if a not in ids or b not in ids:
            return None
        adj: dict[str, list[GraphEdge]] = {n: [] for n in ids}
        for e in self.edges:
            adj.setdefault(e.source, []).append(e)
            adj.setdefault(e.target, []).append(e)
        seen = {a}
        queue: list[tuple[str, list[GraphEdge]]] = [(a, [])]
        while queue:
            cur, path = queue.pop(0)
            if len(path) >= max_hops:
                continue
            for e in adj.get(cur, []):
                nxt = e.target if e.source == cur else e.source
                if nxt in seen:
                    continue
                new_path = path + [e]
                if nxt == b:
                    return new_path
                seen.add(nxt)
                queue.append((nxt, new_path))
        return None


class ChangedFile(BaseModel):
    path: str
    status: str = "modified"  # added | modified | deleted
    touches: list[str] = Field(default_factory=list)  # inferred node ids


class ChangeSet(BaseModel):
    files: list[ChangedFile] = Field(default_factory=list)
    summary: str = ""
    source: str = ""  # path to diff or "git"


class EvidenceBundle(BaseModel):
    graph: DependencyGraph
    change: ChangeSet
    changed_nodes: list[str] = Field(default_factory=list)
    catalog: dict[str, Criticality] = Field(default_factory=dict)


class ProposedImpact(BaseModel):
    target: str
    severity: Criticality = Criticality.MEDIUM
    rationale: str = ""
    failure_modes: list[str] = Field(default_factory=list)


class ImpactProposal(BaseModel):
    """Agent (or local heuristic) output — never trusted until verified."""

    changed_services: list[str] = Field(default_factory=list)
    impacts: list[ProposedImpact] = Field(default_factory=list)
    narrative: str = ""
    proposer: str = "unknown"  # worker-agent | heuristic | file


class EvidenceRef(BaseModel):
    kind: str
    detail: str
    edge: GraphEdge | None = None


class VerifiedImpact(BaseModel):
    target: str
    tier: Tier
    severity: Criticality
    rationale: str = ""
    failure_modes: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    drop_reason: str = ""


class RiskScore(BaseModel):
    """Heuristic score 0–100 from explicit inputs — not an outage probability."""

    value: int
    label: str  # low | medium | high | critical
    factors: dict[str, Any] = Field(default_factory=dict)
    formula: str = ""


class GateDecision(BaseModel):
    outcome: GateOutcome
    reasons: list[str] = Field(default_factory=list)
    policy: dict[str, Any] = Field(default_factory=dict)


class AnalysisReport(BaseModel):
    findings: list[VerifiedImpact] = Field(default_factory=list)
    risk: RiskScore
    gate: GateDecision
    narrative: str = ""
    analyzed_formats: list[str] = Field(default_factory=list)
    skipped_formats: list[str] = Field(default_factory=list)
    changed_nodes: list[str] = Field(default_factory=list)
    proposer: str = ""
    version: str = "0.1.0"
