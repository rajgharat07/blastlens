from pathlib import Path

from blastlens.pipeline import build_evidence, load_proposal
from blastlens.schema import Criticality, ImpactProposal, ProposedImpact, Tier
from blastlens.verify import verify_proposal

ROOT = Path(__file__).resolve().parents[1]
SHOP = ROOT / "examples" / "shopfleet"
DIFF = ROOT / "examples" / "changes" / "risky-checkout.diff"
PROPOSAL = ROOT / "examples" / "changes" / "proposals" / "risky-checkout.json"


def test_tiers_on_fixture_proposal():
    evidence = build_evidence(SHOP, DIFF)
    proposal = load_proposal(PROPOSAL)
    findings = {f.target: f for f in verify_proposal(evidence, proposal)}

    assert findings["service:checkout-api"].tier == Tier.VERIFIED
    assert findings["service:payments-api"].tier == Tier.VERIFIED
    assert findings["service:inventory-api"].tier == Tier.VERIFIED
    # notify-worker has edge to checkout — path exists
    assert findings["service:notify-worker"].tier == Tier.VERIFIED
    # analytics missing from graph → observed, not dropped
    assert findings["service:analytics-api"].tier == Tier.MODEL_OBSERVED
    # legacy-billing asserts direct depends_on that manifests deny
    assert findings["service:legacy-billing"].tier == Tier.DROPPED
    assert findings["totally invalid!!"].tier == Tier.DROPPED


def test_no_path_is_observed_not_dropped():
    evidence = build_evidence(SHOP, DIFF)
    proposal = ImpactProposal(
        impacts=[
            ProposedImpact(
                target="service:analytics-api",
                severity=Criticality.HIGH,
                rationale="gut feel only",
            )
        ],
        proposer="test",
    )
    findings = verify_proposal(evidence, proposal)
    assert findings[0].tier == Tier.MODEL_OBSERVED
    detail = findings[0].evidence[0].detail
    assert "not present in analyzed graph" in detail or "insufficient evidence" in detail
