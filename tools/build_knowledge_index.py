#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


LAYERS = ("microsoft", "community", "custom")


def normalize_layers(root: Path, requested: list[str] | None) -> list[str]:
    if requested is None:
        return [layer for layer in LAYERS if (root / layer).is_dir()]
    if len(requested) != len(set(requested)):
        raise ValueError("enabled layers contain duplicates")
    unknown = [layer for layer in requested if layer not in LAYERS]
    if unknown:
        raise ValueError(f"unknown enabled layer(s): {', '.join(unknown)}")
    return [layer for layer in LAYERS if layer in requested]


def parse_markdown(path: Path) -> tuple[dict[str, Any], str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing frontmatter")
    parts = text.split("---", 2)
    if len(parts) != 3:
        raise ValueError("unterminated frontmatter")
    frontmatter = yaml.safe_load(parts[1]) or {}
    if not isinstance(frontmatter, dict):
        raise ValueError("frontmatter is not a mapping")
    body = parts[2]
    title_match = re.search(r"^#\s+(.+?)\s*$", body, re.MULTILINE)
    description_match = re.search(r"^##\s+Description\s*$\n(.*?)(?=^##\s|\Z)", body, re.MULTILINE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""
    description = " ".join(description_match.group(1).split()) if description_match else ""
    return frontmatter, title, description


def lean_description(text: str, maximum: int = 120) -> str:
    sentence = re.match(r"^(.*?[.!?])(?:\s|$)", text)
    value = sentence.group(1) if sentence else text
    if len(value) <= maximum:
        return value
    cut = value[:maximum]
    boundary = cut.rfind(" ")
    if boundary > 40:
        cut = cut[:boundary]
    return cut.rstrip() + "…"


def source_tree_digest(root: Path, paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_index(
    root: Path,
    enabled_layers: list[str] | None = None,
    knowledge_allow: list[str] | None = None,
    knowledge_deny: list[str] | None = None,
    full_index: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    effective_layers = normalize_layers(root, enabled_layers)
    paths = [
        path
        for layer in effective_layers
        for path in sorted((root / layer / "knowledge").rglob("*.md"))
        if path.is_file()
    ]
    articles: list[dict[str, Any]] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        layer = relative.split("/", 1)[0]
        try:
            frontmatter, title, description = parse_markdown(path)
            articles.append({
                "path": relative,
                "layer": layer,
                "domain": frontmatter.get("domain", ""),
                "bc-version": frontmatter.get("bc-version", []),
                "technologies": frontmatter.get("technologies", []),
                "countries": frontmatter.get("countries", []),
                "application-area": frontmatter.get("application-area", []),
                "keywords": frontmatter.get("keywords", []),
                "title": title,
                "description": description if full_index else lean_description(description),
                "parsed": True,
            })
        except (OSError, UnicodeError, ValueError, yaml.YAMLError):
            domain = relative.split("/knowledge/", 1)[1].split("/", 1)[0] if "/knowledge/" in relative else ""
            articles.append({
                "path": relative,
                "layer": layer,
                "domain": domain,
                "bc-version": [],
                "technologies": [],
                "countries": [],
                "application-area": [],
                "keywords": [],
                "title": "",
                "description": "",
                "parsed": False,
            })
    return {
        "version": 2,
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sourceTreeDigest": source_tree_digest(root, paths),
        "enabledLayers": effective_layers,
        "knowledgeAllow": knowledge_allow or [],
        "knowledgeDeny": knowledge_deny or [],
        "articleCount": len(articles),
        "articles": articles,
    }


def parse_enabled_layers(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None
    return [item for value in values for item in value.split(",") if item]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the BCQuality knowledge index.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--index-path")
    parser.add_argument("--enabled-layer", action="append")
    parser.add_argument("--knowledge-allow", action="append", default=[])
    parser.add_argument("--knowledge-deny", action="append", default=[])
    parser.add_argument("--full-index", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        index = build_index(
            root,
            parse_enabled_layers(args.enabled_layer),
            args.knowledge_allow,
            args.knowledge_deny,
            args.full_index,
        )
    except ValueError as exc:
        parser.error(str(exc))
    output = Path(args.index_path).resolve() if args.index_path else root / "knowledge-index.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(index, ensure_ascii=False, indent=2 if args.full_index else None, separators=None if args.full_index else (",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"BCQuality index: {index['articleCount']} article(s). Index: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
