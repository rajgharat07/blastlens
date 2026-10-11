"""Deterministic heuristic risk score — not an outage probability."""

from __future__ import annotations

from blastlens.schema import Criticality, RiskScore, Tier, VerifiedImpact

_CRIT_WEIGHT = {
    Criticality.LOW: 1,
    Criticality.MEDIUM: 2,
    Criticality.HIGH: 4,
    Criticality.CRITICAL: 6,
}

_TIER_WEIGHT = {
    Tier.VERIFIED: 1.0,
    Tier.MODEL_OBSERVED: 0.45,  # unknowns still elevate review, never treated as safe
    Tier.DROPPED: 0.0,
}

_FORMULA = (
    "score = min(100, round(12 * sum(criticality_weight * tier_weight) "
    "+ 8 * verified_high_or_critical_count + 5 * observed_count))"
)


def score_findings(findings: list[VerifiedImpact]) -> RiskScore:
    raw = 0.0
    verified_hot = 0
    observed = 0
    for f in findings:
        raw += _CRIT_WEIGHT[f.severity] * _TIER_WEIGHT[f.tier]
        if f.tier == Tier.VERIFIED and f.severity in {Criticality.HIGH, Criticality.CRITICAL}:
            verified_hot += 1
        if f.tier == Tier.MODEL_OBSERVED:
            observed += 1

    value = int(min(100, round(12 * raw + 8 * verified_hot + 5 * observed)))
    if value >= 75:
        label = "critical"
    elif value >= 50:
        label = "high"
    elif value >= 25:
        label = "medium"
    else:
        label = "low"

    return RiskScore(
        value=value,
        label=label,
        factors={
            "weighted_impact_sum": round(raw, 3),
            "verified_high_or_critical": verified_hot,
            "model_observed_count": observed,
            "finding_count": len(findings),
        },
        formula=_FORMULA,
    )
