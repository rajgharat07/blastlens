"""Tier agent claims against repository evidence.

Trust model (unknown ≠ false):
- verified: a supported, traceable dependency path or direct reference backs the claim
- model-observed: plausible, but available evidence does not establish it
- dropped: malformed, invalid target, or contradicts explicit evidence under a documented rule
"""

from __future__ import annotations

from blastlens.schema import (
    DependencyGraph,
    EvidenceBundle,
    EvidenceRef,
    ImpactProposal,
    Tier,
    VerifiedImpact,
)


_ALLOWED_KINDS = {
    "service",
    "k8s-deploy",
    "k8s-svc",
    "configmap",
    "secret",
    "config",
    "iac",
}


def verify_proposal(evidence: EvidenceBundle, proposal: ImpactProposal) -> list[VerifiedImpact]:
    graph = evidence.graph
    known = graph.node_ids()
    changed = set(evidence.changed_nodes)
    out: list[VerifiedImpact] = []

    for claim in proposal.impacts:
        raw = (claim.target or "").strip()
        ok, target, drop_reason = _coerce_target(raw)
        finding = VerifiedImpact(
            target=target or raw or "(empty)",
            tier=Tier.MODEL_OBSERVED,
            severity=claim.severity,
            rationale=claim.rationale,
            failure_modes=list(claim.failure_modes),
        )

        if not ok:
            finding.tier = Tier.DROPPED
            finding.drop_reason = drop_reason
            out.append(finding)
            continue

        if target not in known:
            # not in analyzed graph — unknown, not false
            finding.tier = Tier.MODEL_OBSERVED
            finding.evidence.append(
                EvidenceRef(
                    kind="missing-node",
                    detail="target not present in analyzed graph; parsers may not cover this resource",
                )
            )
            out.append(finding)
            continue

        if target in changed:
            finding.tier = Tier.VERIFIED
            finding.evidence.append(
                EvidenceRef(kind="direct-change", detail=f"{target} appears in the change set")
            )
            out.append(finding)
            continue

        # contradiction before "no path": claiming a direct depends_on the manifests deny
        if _contradicts_declared_deps(graph, changed, target, claim.rationale):
            finding.tier = Tier.DROPPED
            finding.drop_reason = (
                "contradicts declared depends_on: no edge and rationale claims a direct dependency"
            )
            out.append(finding)
            continue

        best_path = None
        best_src = None
        for src in changed:
            path = graph.path_exists(src, target)
            if path is not None and (best_path is None or len(path) < len(best_path)):
                best_path = path
                best_src = src

        if best_path is not None and best_src is not None:
            finding.tier = Tier.VERIFIED
            if len(best_path) == 0:
                finding.evidence.append(
                    EvidenceRef(kind="direct-change", detail=f"{target} in change set")
                )
            else:
                finding.evidence.append(
                    EvidenceRef(
                        kind="path-summary",
                        detail=f"{best_src} → {target} ({len(best_path)} hop(s))",
                    )
                )
                for e in best_path:
                    finding.evidence.append(
                        EvidenceRef(kind="dependency-path", detail=e.evidence, edge=e)
                    )
            out.append(finding)
            continue

        # no path in the analyzed graph — unknown, stay model-observed
        finding.tier = Tier.MODEL_OBSERVED
        finding.evidence.append(
            EvidenceRef(
                kind="no-path",
                detail=(
                    "no dependency path found within analyzed formats; "
                    "this is insufficient evidence, not proof of no impact"
                ),
            )
        )
        out.append(finding)

    return out


def _coerce_target(raw: str) -> tuple[bool, str, str]:
    if not raw:
        return False, "", "malformed target; empty"
    if any(ch.isspace() for ch in raw) or "!" in raw:
        return False, raw, "malformed target; unexpected characters"
    if ":" not in raw:
        return True, f"service:{raw}", ""
    kind, _, name = raw.partition(":")
    if kind not in _ALLOWED_KINDS or not name:
        return False, raw, f"malformed target; unsupported kind or empty name ({kind!r})"
    return True, raw, ""


def _contradicts_declared_deps(
    graph: DependencyGraph,
    changed: set[str],
    target: str,
    rationale: str,
) -> bool:
    """Drop only when the claim clearly asserts a direct edge the manifests deny."""
    text = (rationale or "").lower()
    asserts_direct = any(
        phrase in text
        for phrase in ("direct dependency", "depends_on", "directly depends", "direct depends")
    )
    if not asserts_direct:
        return False
    if not target.startswith("service:"):
        return False
    for src in changed:
        if not src.startswith("service:"):
            continue
        # if any SERVICE_CALL edge exists either way, not a contradiction
        for e in graph.edges:
            if {e.source, e.target} == {src, target}:
                return False
        # both nodes known, no edge, claim said direct → contradict
        if src in graph.node_ids() and target in graph.node_ids():
            return True
    return False
