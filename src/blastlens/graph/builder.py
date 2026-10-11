"""Build a deterministic dependency graph from a supported format subset."""

from __future__ import annotations

from pathlib import Path

from blastlens.graph.parsers import iac, k8s, services
from blastlens.schema import DependencyGraph, GraphEdge, GraphNode


def build_graph(root: Path | str) -> DependencyGraph:
    root = Path(root).resolve()
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    analyzed: list[str] = []
    skipped: list[str] = [
        "helm-charts",
        "docker-compose",
        "openapi-runtime-calls",
        "dynamic-service-discovery",
    ]

    if (root / "services").is_dir():
        n, e = services.parse_service_tree(root)
        nodes.extend(n)
        edges.extend(e)
        analyzed.append("service.yaml (depends_on, configs, env hostnames)")

    if (root / "k8s").is_dir():
        n, e = k8s.parse_k8s_tree(root)
        nodes.extend(n)
        edges.extend(e)
        analyzed.append("kubernetes (Deployment/Service selectors, ConfigMap/Secret refs)")

    if (root / "terraform").is_dir():
        n, e = iac.parse_iac_tree(root)
        nodes.extend(n)
        edges.extend(e)
        analyzed.append("terraform (resource blocks + depends_on only)")

    # dedupe nodes by id (first wins; later may fill path)
    by_id: dict[str, GraphNode] = {}
    for n in nodes:
        if n.id in by_id:
            prev = by_id[n.id]
            if not prev.path and n.path:
                by_id[n.id] = n
            continue
        by_id[n.id] = n

    # drop edges to nowhere only for *dangling invented* targets? keep them —
    # verifier uses missing targets as drop/observe signals.
    # ensure edge endpoints exist as stub nodes so path search works for declared deps
    for e in edges:
        for endpoint in (e.source, e.target):
            if endpoint not in by_id:
                kind = endpoint.split(":", 1)[0] if ":" in endpoint else "unknown"
                by_id[endpoint] = GraphNode(id=endpoint, kind=kind, path="")

    return DependencyGraph(
        nodes=list(by_id.values()),
        edges=edges,
        analyzed_formats=analyzed,
        skipped_formats=skipped,
        root=str(root),
    )
