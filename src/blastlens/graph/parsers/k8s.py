"""Parse a small, documented Kubernetes subset.

Supported:
- Deployment → Service via label selector match
- Deployment envFrom / volumes → ConfigMap / Secret names
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from blastlens.schema import EdgeKind, GraphEdge, GraphNode


def _docs(path: Path) -> list[dict[str, Any]]:
    try:
        raw = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
    except (OSError, yaml.YAMLError):
        return []
    return [d for d in raw if isinstance(d, dict)]


def parse_k8s_tree(root: Path) -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    k8s_dir = root / "k8s"
    if not k8s_dir.is_dir():
        return nodes, edges

    deployments: list[tuple[str, dict[str, str], dict[str, Any], str]] = []
    services: list[tuple[str, dict[str, str], str]] = []

    for path in sorted(set(k8s_dir.rglob("*.yaml")) | set(k8s_dir.rglob("*.yml"))):
        rel = path.relative_to(root).as_posix()
        for doc in _docs(path):
            kind = str(doc.get("kind") or "")
            meta = doc.get("metadata") or {}
            name = str(meta.get("name") or "")
            if not name:
                continue

            if kind == "Deployment":
                tmpl = ((doc.get("spec") or {}).get("template") or {})
                labels = {
                    str(k): str(v)
                    for k, v in ((tmpl.get("metadata") or {}).get("labels") or {}).items()
                }
                nid = f"k8s-deploy:{name}"
                nodes.append(GraphNode(id=nid, kind="k8s-deployment", path=rel, labels=labels))
                deployments.append((name, labels, doc, rel))
                # link deploy name → service:{name} when naming aligns
                edges.append(
                    GraphEdge(
                        source=nid,
                        target=f"service:{name}",
                        kind=EdgeKind.K8S_SELECTOR,
                        evidence=f"{rel}#Deployment/{name}→service:{name}",
                        weight=0.5,
                    )
                )
                _config_refs(doc, nid, rel, nodes, edges)

            elif kind == "Service":
                selector = {
                    str(k): str(v)
                    for k, v in ((doc.get("spec") or {}).get("selector") or {}).items()
                }
                nid = f"k8s-svc:{name}"
                nodes.append(GraphNode(id=nid, kind="k8s-service", path=rel, labels=selector))
                services.append((name, selector, rel))

            elif kind == "ConfigMap":
                nodes.append(GraphNode(id=f"configmap:{name}", kind="configmap", path=rel))
            elif kind == "Secret":
                nodes.append(GraphNode(id=f"secret:{name}", kind="secret", path=rel))

    for dep_name, dep_labels, _doc, dep_rel in deployments:
        for svc_name, selector, svc_rel in services:
            if selector and all(dep_labels.get(k) == v for k, v in selector.items()):
                edges.append(
                    GraphEdge(
                        source=f"k8s-svc:{svc_name}",
                        target=f"k8s-deploy:{dep_name}",
                        kind=EdgeKind.K8S_SELECTOR,
                        evidence=f"{svc_rel}#selector matches {dep_rel}",
                    )
                )

    return nodes, edges


def _config_refs(
    doc: dict[str, Any],
    deploy_id: str,
    rel: str,
    nodes: list[GraphNode],
    edges: list[GraphEdge],
) -> None:
    containers = (
        ((doc.get("spec") or {}).get("template") or {}).get("spec") or {}
    ).get("containers") or []
    for c in containers:
        for env_from in c.get("envFrom") or []:
            if "configMapRef" in env_from:
                name = str((env_from["configMapRef"] or {}).get("name") or "")
                if name:
                    cid = f"configmap:{name}"
                    if not any(n.id == cid for n in nodes):
                        nodes.append(GraphNode(id=cid, kind="configmap", path=""))
                    edges.append(
                        GraphEdge(
                            source=deploy_id,
                            target=cid,
                            kind=EdgeKind.K8S_CONFIGMAP,
                            evidence=f"{rel}#envFrom.configMapRef:{name}",
                        )
                    )
            if "secretRef" in env_from:
                name = str((env_from["secretRef"] or {}).get("name") or "")
                if name:
                    sid = f"secret:{name}"
                    if not any(n.id == sid for n in nodes):
                        nodes.append(GraphNode(id=sid, kind="secret", path=""))
                    edges.append(
                        GraphEdge(
                            source=deploy_id,
                            target=sid,
                            kind=EdgeKind.K8S_SECRET,
                            evidence=f"{rel}#envFrom.secretRef:{name}",
                        )
                    )
        for env in c.get("env") or []:
            value_from = env.get("valueFrom") or {}
            cm = (value_from.get("configMapKeyRef") or {}).get("name")
            if cm:
                cid = f"configmap:{cm}"
                if not any(n.id == cid for n in nodes):
                    nodes.append(GraphNode(id=cid, kind="configmap", path=""))
                edges.append(
                    GraphEdge(
                        source=deploy_id,
                        target=cid,
                        kind=EdgeKind.K8S_CONFIGMAP,
                        evidence=f"{rel}#env.valueFrom.configMapKeyRef:{cm}",
                    )
                )
            sec = (value_from.get("secretKeyRef") or {}).get("name")
            if sec:
                sid = f"secret:{sec}"
                if not any(n.id == sid for n in nodes):
                    nodes.append(GraphNode(id=sid, kind="secret", path=""))
                edges.append(
                    GraphEdge(
                        source=deploy_id,
                        target=sid,
                        kind=EdgeKind.K8S_SECRET,
                        evidence=f"{rel}#env.valueFrom.secretKeyRef:{sec}",
                    )
                )
