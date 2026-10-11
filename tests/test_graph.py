from pathlib import Path

from blastlens.graph.builder import build_graph

ROOT = Path(__file__).resolve().parents[1]
SHOP = ROOT / "examples" / "shopfleet"


def test_shopfleet_has_service_edges():
    g = build_graph(SHOP)
    ids = g.node_ids()
    assert "service:checkout-api" in ids
    assert "service:payments-api" in ids
    kinds = {(e.source, e.target, e.kind.value) for e in g.edges}
    assert ("service:checkout-api", "service:payments-api", "service-call") in kinds
    assert ("service:checkout-api", "service:inventory-api", "service-call") in kinds


def test_k8s_selector_and_configmap():
    g = build_graph(SHOP)
    assert any(e.kind.value == "k8s-selector" for e in g.edges)
    assert any(
        e.target == "configmap:shared-pricing" or e.source == "configmap:shared-pricing"
        for e in g.edges
    )


def test_terraform_depends_on():
    g = build_graph(SHOP)
    assert "iac:aws_sqs_queue.checkout_events" in g.node_ids()
    assert any(e.kind.value == "iac-ref" for e in g.edges)


def test_analyzed_formats_documented():
    g = build_graph(SHOP)
    assert g.analyzed_formats
    assert "helm-charts" in g.skipped_formats


def test_path_exists():
    g = build_graph(SHOP)
    path = g.path_exists("service:checkout-api", "service:payments-api")
    assert path is not None
    assert len(path) >= 1
