from pathlib import Path

from blastlens.pipeline import run_analyze
from blastlens.schema import GateOutcome, Tier

ROOT = Path(__file__).resolve().parents[1]
SHOP = ROOT / "examples" / "shopfleet"
DIFF = ROOT / "examples" / "changes" / "risky-checkout.diff"
PROPOSAL = ROOT / "examples" / "changes" / "proposals" / "risky-checkout.json"


def test_analyze_writes_artifacts(tmp_path: Path):
    report = run_analyze(SHOP, DIFF, tmp_path, proposal_path=PROPOSAL)
    assert (tmp_path / "evidence.json").exists()
    assert (tmp_path / "proposal.json").exists()
    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "report.html").exists()
    assert report.gate.outcome in {GateOutcome.BLOCKED, GateOutcome.APPROVAL_REQUIRED}
    assert any(f.tier == Tier.VERIFIED for f in report.findings)
    assert any(f.tier == Tier.MODEL_OBSERVED for f in report.findings)
    assert any(f.tier == Tier.DROPPED for f in report.findings)
