from blastlens.gate import decide_gate, exit_code
from blastlens.schema import Criticality, GateOutcome, Tier, VerifiedImpact
from blastlens.scoring import score_findings


def _f(target: str, tier: Tier, sev: Criticality) -> VerifiedImpact:
    return VerifiedImpact(target=target, tier=tier, severity=sev)


def test_score_increases_with_verified_critical():
    low = score_findings([_f("service:a", Tier.VERIFIED, Criticality.LOW)])
    hot = score_findings([_f("service:payments-api", Tier.VERIFIED, Criticality.CRITICAL)])
    assert hot.value > low.value
    assert "probability" not in hot.formula.lower()


def test_gate_blocked_on_verified_critical():
    findings = [_f("service:payments-api", Tier.VERIFIED, Criticality.CRITICAL)]
    risk = score_findings(findings)
    gate = decide_gate(findings, risk)
    assert gate.outcome == GateOutcome.BLOCKED
    assert exit_code(gate) == 1


def test_gate_approval_on_observed_high():
    findings = [_f("service:analytics-api", Tier.MODEL_OBSERVED, Criticality.HIGH)]
    risk = score_findings(findings)
    gate = decide_gate(findings, risk)
    assert gate.outcome == GateOutcome.APPROVAL_REQUIRED
    assert exit_code(gate) == 2


def test_gate_pass_when_clean():
    findings = [_f("service:notify-worker", Tier.VERIFIED, Criticality.LOW)]
    risk = score_findings(findings)
    # force low risk path with empty-ish policy override
    gate = decide_gate(findings, risk, policy={"approval_on_risk_at_least": 99})
    assert gate.outcome == GateOutcome.PASS
    assert exit_code(gate) == 0


def test_dropped_does_not_block():
    findings = [_f("service:legacy-billing", Tier.DROPPED, Criticality.CRITICAL)]
    risk = score_findings(findings)
    gate = decide_gate(findings, risk, policy={"approval_on_risk_at_least": 99})
    assert gate.outcome == GateOutcome.PASS
