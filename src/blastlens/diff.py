"""Ingest a unified diff or an explicit file list into a ChangeSet."""

from __future__ import annotations

import re
from pathlib import Path

from blastlens.schema import ChangeSet, ChangedFile, DependencyGraph

_DIFF_FILE_RE = re.compile(r"^\+\+\+\s+(?:b/)?(.+)$", re.MULTILINE)
_DIFF_GIT_RE = re.compile(r"^diff --git a/(.+) b/(.+)$", re.MULTILINE)


def parse_unified_diff(text: str, *, source: str = "") -> ChangeSet:
    files: dict[str, ChangedFile] = {}
    for m in _DIFF_GIT_RE.finditer(text):
        path = m.group(2).replace("\\", "/")
        files[path] = ChangedFile(path=path, status="modified")
    for m in _DIFF_FILE_RE.finditer(text):
        path = m.group(1).strip()
        if path == "/dev/null":
            continue
        path = path.replace("\\", "/")
        files.setdefault(path, ChangedFile(path=path, status="modified"))
    return ChangeSet(files=list(files.values()), summary=f"{len(files)} file(s) changed", source=source)


def load_change(path: Path | str) -> ChangeSet:
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix in {".diff", ".patch"} or text.lstrip().startswith("diff --git"):
        return parse_unified_diff(text, source=str(path))
    # plain newline-separated file list
    files = [
        ChangedFile(path=line.strip().replace("\\", "/"), status="modified")
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return ChangeSet(files=files, summary=f"{len(files)} file(s) listed", source=str(path))


def map_files_to_nodes(change: ChangeSet, graph: DependencyGraph) -> list[str]:
    """Map changed paths onto graph node ids using path prefixes and naming heuristics."""
    touched: set[str] = set()
    path_index = {n.path: n.id for n in graph.nodes if n.path}

    for f in change.files:
        p = f.path.replace("\\", "/")
        f.touches = []
        if p in path_index:
            f.touches.append(path_index[p])
            touched.add(path_index[p])
            continue
        # services/<name>/...
        parts = p.split("/")
        if len(parts) >= 2 and parts[0] == "services":
            nid = f"service:{parts[1]}"
            f.touches.append(nid)
            touched.add(nid)
        # k8s manifests that match node paths by prefix
        for n in graph.nodes:
            if n.path and (p == n.path or p.startswith(n.path.rsplit("/", 1)[0] + "/")):
                if n.id not in f.touches:
                    f.touches.append(n.id)
                    touched.add(n.id)
        # basename stem match for k8s/terraform filenames
        stem = Path(p).stem
        for n in graph.nodes:
            if n.id.endswith(f":{stem}") or n.id.endswith(f".{stem}"):
                if n.id not in f.touches:
                    f.touches.append(n.id)
                    touched.add(n.id)

    return sorted(touched)
