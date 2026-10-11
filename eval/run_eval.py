"""Tiny honest eval: precision of Verified claims vs known-good edges in shopfleet.

Run: python eval/run_eval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from blastlens.pipeline import build_evidence, load_proposal  # noqa: E402
from blastlens.schema import Tier  # noqa: E402
from blastlens.verify import verify_proposal  # noqa: E402

SHOP = ROOT / "examples" / "shopfleet"
DIFF = ROOT / "examples" / "changes" / "risky-checkout.diff"
PROPOSAL = ROOT / "examples" / "changes" / "proposals" / "risky-checkout.json"

# Known-good: targets that SHOULD be verified given shopfleet edges + this diff
KNOWN_GOOD_VERIFIED = {
    "service:checkout-api",
    "service:payments-api",
    "service:inventory-api",
    "service:notify-worker",
}


def main() -> int:
    evidence = build_evidence(SHOP, DIFF)
    proposal = load_proposal(PROPOSAL)
    findings = verify_proposal(evidence, proposal)
    verified = {f.target for f in findings if f.tier == Tier.VERIFIED}

    true_pos = verified & KNOWN_GOOD_VERIFIED
    false_pos = verified - KNOWN_GOOD_VERIFIED
    false_neg = KNOWN_GOOD_VERIFIED - verified

    precision = len(true_pos) / len(verified) if verified else 0.0
    recall = len(true_pos) / len(KNOWN_GOOD_VERIFIED) if KNOWN_GOOD_VERIFIED else 0.0

    result = {
        "fixture": "examples/shopfleet + risky-checkout",
        "verified_targets": sorted(verified),
        "known_good": sorted(KNOWN_GOOD_VERIFIED),
        "true_positives": sorted(true_pos),
        "false_positives": sorted(false_pos),
        "false_negatives": sorted(false_neg),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "notes": (
            "Eval only covers Verified precision/recall against declared edges in the "
            "bundled fixture. It does not claim production accuracy."
        ),
    }
    out = ROOT / "eval" / "last_result.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    # fail CI-ish if precision collapses
    return 0 if precision >= 0.99 and recall >= 0.99 else 1


if __name__ == "__main__":
    raise SystemExit(main())
