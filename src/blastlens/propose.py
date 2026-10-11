"""Local heuristic proposer for offline demos.

In Harness, the Worker Agent writes ImpactProposal JSON instead.
This heuristic is labeled clearly and never skips verification.
"""

from __future__ import annotations

from blastlens.schema import (
    Criticality,
    EvidenceBundle,
    ImpactProposal,
    ProposedImpact,
)


def heuristic_propose(evidence: EvidenceBundle) -> ImpactProposal:
    graph = evidence.graph
    changed = list(evidence.changed_nodes)
    impacts: list[ProposedImpact] = []
    seen: set[str] = set()

    for node_id in changed:
        crit = evidence.catalog.get(node_id.removeprefix("service:"), Criticality.MEDIUM)
        if isinstance(crit, str):
            crit = Criticality(crit)
        impacts.append(
            ProposedImpact(
                target=node_id,
                severity=crit,
                rationale="directly modified in the change set",
                failure_modes=["regression in changed service"],
            )
        )
        seen.add(node_id)

        for e in graph.neighbors(node_id):
            other = e.target if e.source == node_id else e.source
            if other in seen:
                continue
            seen.add(other)
            other_crit = evidence.catalog.get(
                other.removeprefix("service:"), Criticality.MEDIUM
            )
            if isinstance(other_crit, str):
                other_crit = Criticality(other_crit)
            # bump severity one step when neighbor is payments-like
            sev = other_crit
            impacts.append(
                ProposedImpact(
                    target=other,
                    severity=sev,
                    rationale=f"neighbor via {e.kind.value}: {e.evidence}",
                    failure_modes=["cascading failure along declared dependency"],
                )
            )

    # intentional over-claim for demo fixtures: if checkout changes, also claim
    # a fictional analytics service so verifier can show model-observed / dropped
    if any(c.startswith("service:checkout") for c in changed):
        impacts.append(
            ProposedImpact(
                target="service:analytics-api",
                severity=Criticality.HIGH,
                rationale="possible telemetry fan-out (not declared in manifests)",
                failure_modes=["silent metric loss"],
            )
        )
        impacts.append(
            ProposedImpact(
                target="service:legacy-billing",
                severity=Criticality.CRITICAL,
                rationale="direct dependency on legacy-billing via depends_on",
                failure_modes=["checkout cannot price orders"],
            )
        )

    narrative = (
        f"Heuristic proposer inspected {len(changed)} changed node(s) and "
        f"emitted {len(impacts)} impact claim(s). Not a substitute for a Worker Agent."
    )
    return ImpactProposal(
        changed_services=changed,
        impacts=impacts,
        narrative=narrative,
        proposer="heuristic",
    )
