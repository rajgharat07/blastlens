"""Parse service.yaml declarations for service-to-service + shared config refs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from blastlens.schema import EdgeKind, GraphEdge, GraphNode


def _load(path: Path) -> dict[str, Any] | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def parse_service_tree(root: Path) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Expect services/<name>/service.yaml with depends_on / env / configs keys."""
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    services_dir = root / "services"
    if not services_dir.is_dir():
        return nodes, edges

    for svc_dir in sorted(p for p in services_dir.iterdir() if p.is_dir()):
        manifest = svc_dir / "service.yaml"
        if not manifest.exists():
            continue
        data = _load(manifest)
        if not data:
            continue
        name = str(data.get("name") or svc_dir.name)
        node_id = f"service:{name}"
        labels = {str(k): str(v) for k, v in (data.get("labels") or {}).items()}
        nodes.append(
            GraphNode(
                id=node_id,
                kind="service",
                path=str(manifest.relative_to(root)).replace("\\", "/"),
                labels=labels,
            )
        )

        for dep in data.get("depends_on") or []:
            dep_name = str(dep)
            edges.append(
                GraphEdge(
                    source=node_id,
                    target=f"service:{dep_name}",
                    kind=EdgeKind.SERVICE_CALL,
                    evidence=f"{manifest.relative_to(root).as_posix()}#depends_on:{dep_name}",
                )
            )

        for cfg in data.get("configs") or []:
            cfg_name = str(cfg)
            cfg_id = f"config:{cfg_name}"
            if not any(n.id == cfg_id for n in nodes):
                nodes.append(GraphNode(id=cfg_id, kind="shared-config", path=""))
            edges.append(
                GraphEdge(
                    source=node_id,
                    target=cfg_id,
                    kind=EdgeKind.SHARED_CONFIG,
                    evidence=f"{manifest.relative_to(root).as_posix()}#configs:{cfg_name}",
                )
            )

        for key, val in (data.get("env") or {}).items():
            # env values that look like service hostnames: HOST=payments-api
            text = str(val)
            if text.endswith("-api") or text.endswith("-worker") or text.endswith("-svc"):
                edges.append(
                    GraphEdge(
                        source=node_id,
                        target=f"service:{text}",
                        kind=EdgeKind.SERVICE_CALL,
                        evidence=f"{manifest.relative_to(root).as_posix()}#env.{key}",
                    )
                )

    return nodes, edges
