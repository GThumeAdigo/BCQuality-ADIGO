#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


LAYERS = ("microsoft", "community", "custom")
PRECEDENCE = {layer: index for index, layer in enumerate(LAYERS)}


def parse_frontmatter(path: Path) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    parts = text.split("---", 2)
    if len(parts) != 3:
        return None
    value = yaml.safe_load(parts[1]) or {}
    return value if isinstance(value, dict) else None


def load_action_skills(root: Path, enabled_layers: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for layer in enabled_layers:
        skill_root = root / layer / "skills"
        if not skill_root.is_dir():
            continue
        for path in sorted(skill_root.rglob("*.md")):
            frontmatter = parse_frontmatter(path)
            if not frontmatter or frontmatter.get("kind") != "action-skill":
                continue
            records.append({
                "id": frontmatter.get("id"),
                "version": frontmatter.get("version"),
                "path": path.relative_to(root).as_posix(),
                "layer": layer,
                "inputs": frontmatter.get("inputs", []),
                "bc-version": frontmatter.get("bc-version"),
                "technologies": frontmatter.get("technologies"),
                "countries": frontmatter.get("countries"),
                "application-area": frontmatter.get("application-area"),
            })
    return records


def normalize_layers(value: Any) -> list[str]:
    layers = list(LAYERS) if value is None else value
    if not isinstance(layers, list) or not all(isinstance(layer, str) for layer in layers):
        raise ValueError("enabled-layers must be an array of layer names")
    if len(layers) != len(set(layers)):
        raise ValueError("enabled-layers contains duplicates")
    unknown = [layer for layer in layers if layer not in LAYERS]
    if unknown:
        raise ValueError(f"unknown enabled layer(s): {', '.join(unknown)}")
    return [layer for layer in LAYERS if layer in layers]


def expand_bc_versions(value: Any) -> str | set[int]:
    if value == ["all"]:
        return "all"
    versions: set[int] = set()
    for item in value or []:
        if isinstance(item, int) and not isinstance(item, bool):
            versions.add(item)
            continue
        match = re.fullmatch(r"(\d+)\.\.(\d*)", str(item))
        if not match:
            continue
        start = int(match.group(1))
        if not match.group(2):
            return f"{start}.."
        versions.update(range(start, int(match.group(2)) + 1))
    return versions


def dimension_matches(name: str, declared: Any, supplied: Any) -> bool:
    if supplied is None or declared is None:
        return True
    supplied_values = supplied if isinstance(supplied, list) else [supplied]
    if "unknown" in supplied_values:
        return True
    if name == "bc-version":
        expanded = expand_bc_versions(declared)
        target = supplied_values[0]
        if expanded == "all":
            return True
        if isinstance(expanded, str) and expanded.endswith(".."):
            return isinstance(target, int) and target >= int(expanded[:-2])
        return target in expanded
    if name == "countries" and "w1" in declared:
        return True
    if name == "application-area" and "all" in declared:
        return True
    return bool(set(declared) & set(supplied_values))


def route_exact(root: Path, task_context: dict[str, Any]) -> dict[str, Any]:
    requested_id = task_context.get("requested-skill-id")
    if not isinstance(requested_id, str) or not requested_id:
        return {
            "skill": {"id": "entry", "version": 1},
            "outcome": "failed",
            "outcome-reason": "requested-skill-id is required by the exact reference router",
            "dispatch": [],
            "skipped": [],
        }
    try:
        enabled_layers = normalize_layers(task_context.get("enabled-layers"))
    except ValueError as exc:
        return {
            "skill": {"id": "entry", "version": 1},
            "outcome": "failed",
            "outcome-reason": str(exc),
            "dispatch": [],
            "skipped": [],
        }
    inputs = task_context.get("inputs-available")
    if not isinstance(inputs, list) or not inputs or not all(isinstance(item, str) for item in inputs):
        return {
            "skill": {"id": "entry", "version": 1},
            "outcome": "failed",
            "outcome-reason": "inputs-available must be a non-empty array of strings",
            "dispatch": [],
            "skipped": [],
        }

    disabled = task_context.get("disabled-skills", [])
    if not isinstance(disabled, list) or not all(isinstance(item, str) for item in disabled):
        return {
            "skill": {"id": "entry", "version": 1},
            "outcome": "failed",
            "outcome-reason": "disabled-skills must be an array of repo-relative paths",
            "dispatch": [],
            "skipped": [],
        }

    candidates = [
        record for record in load_action_skills(root, enabled_layers)
        if record["id"] == requested_id
    ]
    skipped: list[dict[str, Any]] = []
    relevant: list[dict[str, Any]] = []
    dimensions = ("bc-version", "technologies", "countries", "application-area")
    for record in candidates:
        reason = None
        if record["path"] in disabled:
            reason = "configuration"
        elif not set(inputs) & set(record["inputs"]):
            reason = "inputs-unsatisfied"
        elif any(not dimension_matches(name, record[name], task_context.get(name)) for name in dimensions):
            reason = "filter-mismatch"
        if reason:
            skipped.append({"skill": {"id": record["id"], "path": record["path"]}, "reason": reason})
        else:
            relevant.append(record)

    by_layer: dict[str, list[dict[str, Any]]] = {}
    for record in relevant:
        by_layer.setdefault(record["layer"], []).append(record)
    duplicate_layers = [layer for layer, records in by_layer.items() if len(records) > 1]
    if duplicate_layers:
        return {
            "skill": {"id": "entry", "version": 1},
            "outcome": "failed",
            "outcome-reason": f"duplicate exact skill id within layer(s): {', '.join(duplicate_layers)}",
            "dispatch": [],
            "skipped": skipped,
        }

    if not relevant:
        return {
            "skill": {"id": "entry", "version": 1},
            "outcome": "no-match",
            "outcome-reason": f"No relevant action skill has exact id '{requested_id}'.",
            "dispatch": [],
            "skipped": skipped,
        }

    winner = max(relevant, key=lambda record: PRECEDENCE[record["layer"]])
    for record in relevant:
        if record is winner:
            continue
        skipped.append({
            "skill": {"id": record["id"], "path": record["path"]},
            "reason": "layer-precedence",
            "superseded-by": {"id": winner["id"], "path": winner["path"], "version": winner["version"]},
        })
    return {
        "skill": {"id": "entry", "version": 1},
        "outcome": "routed",
        "dispatch": [{
            "skill": {"id": winner["id"], "version": winner["version"], "path": winner["path"]},
            "rationale": f"Exact requested-skill-id '{requested_id}' matched after filters and layer precedence.",
            "inputs": [item for item in inputs if item in winner["inputs"]],
        }],
        "skipped": skipped,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic BCQuality exact-id Entry router.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--task-context", required=True, help="JSON file containing task-context or the context object itself.")
    args = parser.parse_args(argv)
    document = json.loads(Path(args.task_context).read_text(encoding="utf-8"))
    context = document.get("task-context", document)
    result = route_exact(Path(args.root).resolve(), context)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 1 if result["outcome"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
