"""Parse a tiny Terraform subset: resource blocks + explicit depends_on only.

We do not evaluate HCL expressions. Unsupported constructs are ignored, not invented.
"""

from __future__ import annotations

import re
from pathlib import Path

from blastlens.schema import EdgeKind, GraphEdge, GraphNode

_RESOURCE_RE = re.compile(
    r'resource\s+"(?P<type>[^"]+)"\s+"(?P<name>[^"]+)"\s*\{',
    re.MULTILINE,
)
_DEPENDS_RE = re.compile(
    r"depends_on\s*=\s*\[(?P<body>[^\]]*)\]",
    re.MULTILINE | re.DOTALL,
)
_REF_RE = re.compile(r"(?P<type>[a-z0-9_]+)\.(?P<name>[a-zA-Z0-9_-]+)")


def parse_iac_tree(root: Path) -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    tf_dir = root / "terraform"
    if not tf_dir.is_dir():
        return nodes, edges

    for path in sorted(tf_dir.rglob("*.tf")):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in _RESOURCE_RE.finditer(text):
            rtype, rname = m.group("type"), m.group("name")
            nid = f"iac:{rtype}.{rname}"
            nodes.append(GraphNode(id=nid, kind="iac-resource", path=rel, labels={"type": rtype}))

        for dep_m in _DEPENDS_RE.finditer(text):
            # attach depends_on edges to the nearest preceding resource (simple scan)
            body = dep_m.group("body")
            preceding = None
            for m in _RESOURCE_RE.finditer(text):
                if m.start() < dep_m.start():
                    preceding = m
            if not preceding:
                continue
            src = f"iac:{preceding.group('type')}.{preceding.group('name')}"
            for ref in _REF_RE.finditer(body):
                tgt = f"iac:{ref.group('type')}.{ref.group('name')}"
                edges.append(
                    GraphEdge(
                        source=src,
                        target=tgt,
                        kind=EdgeKind.IAC_REF,
                        evidence=f"{rel}#depends_on:{tgt}",
                    )
                )

        # soft refs: resource.foo.bar string mentions elsewhere in file
        declared = {n.id for n in nodes if n.path == rel}
        for nid in list(declared):
            # extract type.name from nid
            short = nid.removeprefix("iac:")
            for other in declared:
                if other == nid:
                    continue
                other_short = other.removeprefix("iac:")
                # only count if the file literally references other_short near this resource — skip; too noisy
                _ = short, other_short

    return nodes, edges
