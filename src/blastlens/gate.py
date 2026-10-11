"""Explicit gate outcomes from verified findings — model never decides the gate."""

from __future__ import annotations

from blastlens.schema import (
    Criticality,
    GateDecision,
    GateOutcome,
    RiskScore,
    Tier,
    VerifiedImpact,
)

DEFAULT_POLICY = {
    "block_on_verified_critical": True,
    "approval_on_verified_high": True,
    "approval_on_model_observed_high": True,
    "approval_on_risk_at_least": 50,
}


def decide_gate(
    findings: list[VerifiedImpact],
    risk: RiskScore,
    *,
    policy: dict | None = None,
) -> GateDecision:
    pol = {**DEFAULT_POLICY, **(policy or {})}
    reasons: list[str] = []

    verified_critical = [
        f
        for f in findings
        if f.tier == Tier.VERIFIED and f.severity == Criticality.CRITICAL
    ]
    verified_high = [
        f for f in findings if f.tier == Tier.VERIFIED and f.severity == Criticality.HIGH
    ]
    observed_high = [
        f
        for f in findings
        if f.tier == Tier.MODEL_OBSERVED
        and f.severity in {Criticality.HIGH, Criticality.CRITICAL}
    ]

    if pol.get("block_on_verified_critical") and verified_critical:
        reasons.append(
            "blocked: verified critical impact on "
            + ", ".join(f.target for f in verified_critical)
        )
        return GateDecision(outcome=GateOutcome.BLOCKED, reasons=reasons, policy=pol)

    need_approval = False
    if pol.get("approval_on_verified_high") and verified_high:
        need_approval = True
        reasons.append(
            "approval-required: verified high impact on "
            + ", ".join(f.target for f in verified_high)
        )
    if pol.get("approval_on_model_observed_high") and observed_high:
        need_approval = True
        reasons.append(
            "approval-required: high/critical claim lacks graph evidence (model-observed) on "
            + ", ".join(f.target for f in observed_high)
        )
    threshold = int(pol.get("approval_on_risk_at_least") or 50)
    if risk.value >= threshold:
        need_approval = True
        reasons.append(f"approval-required: heuristic risk score {risk.value} >= {threshold}")

    if need_approval:
        return GateDecision(outcome=GateOutcome.APPROVAL_REQUIRED, reasons=reasons, policy=pol)

    reasons.append("pass: no configured blocking or approval condition was met")
    return GateDecision(outcome=GateOutcome.PASS, reasons=reasons, policy=pol)


def exit_code(decision: GateDecision) -> int:
    if decision.outcome == GateOutcome.PASS:
        return 0
    if decision.outcome == GateOutcome.APPROVAL_REQUIRED:
        return 2
    return 1  # blocked
