#!/usr/bin/env python3
"""Print a compact summary of a Dify DSL YAML file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from validate_dify_dsl import (
    allowed_outputs_for,
    iter_selector_fields,
    iter_template_refs_with_path,
    node_data,
    node_type,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a Dify DSL YAML file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"ERROR: file not found: {path}")
        return 1
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: cannot parse YAML: {exc}")
        return 1
    if not isinstance(data, dict):
        print("ERROR: root must be a mapping")
        return 1

    app = data.get("app") if isinstance(data.get("app"), dict) else {}
    workflow = data.get("workflow") if isinstance(data.get("workflow"), dict) else {}
    graph = workflow.get("graph") if isinstance(workflow.get("graph"), dict) else {}
    nodes = [n for n in graph.get("nodes", []) if isinstance(n, dict)]
    edges = [e for e in graph.get("edges", []) if isinstance(e, dict)]

    print(f"App: {app.get('name', '<unnamed>')}")
    print(f"Mode: {app.get('mode', '<missing>')}")
    print(f"Version: {data.get('version', '<missing>')}")
    print(f"Nodes: {len(nodes)}  Edges: {len(edges)}")
    print()

    node_ids = {str(n.get("id")): n for n in nodes if n.get("id") is not None}
    print("Nodes:")
    for node in nodes:
        node_id = str(node.get("id", "<missing>"))
        nodetype = node_type(node) or "<missing>"
        title = node_data(node).get("title", "")
        outputs = allowed_outputs_for(node)
        if outputs is None:
            output_text = "dynamic"
        elif outputs:
            output_text = ", ".join(sorted(outputs))
        else:
            output_text = "-"
        print(f"  {node_id:>16}  {nodetype:<22} {title}  -> {output_text}")

    print()
    print("Edges:")
    for edge in edges:
        print(
            f"  {edge.get('source')} -{edge.get('sourceHandle')}-> "
            f"{edge.get('target')}  ({edge.get('data', {}).get('sourceType')} -> "
            f"{edge.get('data', {}).get('targetType')})"
        )

    print()
    print("References:")
    for node in nodes:
        node_id = str(node.get("id", "<missing>"))
        data_obj = node_data(node)
        selectors = list(iter_selector_fields(data_obj, set(node_ids)))
        refs = list(iter_template_refs_with_path(data_obj))
        if not selectors and not refs:
            continue
        print(f"  {node_id} ({node_type(node)}):")
        for selector, selector_path in selectors:
            print(f"    selector {selector_path}: {selector}")
        for ref, key, ref_path in refs:
            print(f"    template {ref_path}: {ref}.{key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
