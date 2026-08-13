#!/usr/bin/env python3
"""Readable reference parser for Property Graph Markdown 0.3.0."""

from __future__ import annotations

import argparse
import datetime as _datetime
import hashlib
import json
import math
import posixpath
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import unquote, urlsplit

try:  # Optional, but preferred when available.
    import yaml as _yaml  # type: ignore
except Exception:  # pragma: no cover - exercised only when PyYAML is absent.
    _yaml = None

from markdown_it import MarkdownIt  # type: ignore


IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CLASS_EXPRESSION_RE = re.compile(
    r"^:(?P<class>[A-Za-z][A-Za-z0-9_]*)(?:[ \t]+(?P<props>\{.*\}))?$"
)


@dataclass
class Link:
    label: str
    destination: str


@dataclass
class Node:
    id: str
    labels: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    relationships: List["Relationship"] = field(default_factory=list)


@dataclass
class Relationship:
    id: str
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Graph:
    nodes: Dict[str, Node] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def relationships(self) -> List[Relationship]:
        return [relationship for node in self.nodes.values() for relationship in node.relationships]

    def ensure_node(self, node_id: str) -> Node:
        if node_id not in self.nodes:
            self.nodes[node_id] = Node(id=node_id)
        return self.nodes[node_id]


def parse_corpus(path: str | Path) -> Graph:
    root = Path(path)
    files = list(_markdown_files(root))
    base = root if root.is_dir() else root.parent
    graph = Graph()

    for file_path in files:
        node_id = file_path.relative_to(base).as_posix()
        text = file_path.read_text(encoding="utf-8")

        node = graph.ensure_node(node_id)
        node.labels = []
        node.properties = {}
        node.relationships = []

        for link in _extract_links_markdown_it(text):
            try:
                class_name, properties = parse_class_expression(link.label)
            except ValueError as exc:
                stripped = link.label.strip()
                if "->" in stripped or "<-" in stripped or stripped.startswith(":"):
                    graph.warnings.append(f"{node_id}: {exc}: {link.label!r}")
                continue

            if link.destination == "":
                if class_name not in node.labels:
                    node.labels.append(class_name)
                _merge_node_properties(graph, node, properties)
                continue

            target_id = resolve_destination(link.destination, source_id=node_id)
            graph.ensure_node(target_id)
            relationship_id = _relationship_fingerprint(
                source=node_id,
                relationship_type=class_name,
                target=target_id,
                properties=properties,
            )
            if any(existing.id == relationship_id for existing in node.relationships):
                continue
            node.relationships.append(
                Relationship(
                    id=relationship_id,
                    source=node_id,
                    target=target_id,
                    type=class_name,
                    properties=properties,
                )
            )

    return graph

def parse_class_expression(label: str) -> Tuple[str, Dict[str, Any]]:
    if "->" in label or "<-" in label:
        raise ValueError("direction markers are not supported in PGM 0.3.0")

    match = CLASS_EXPRESSION_RE.match(label.strip())
    if not match:
        raise ValueError("malformed PGM class expression")

    class_name = match.group("class")
    props_src = match.group("props")
    properties = parse_yaml_flow_mapping(props_src) if props_src else {}
    return class_name, properties


def parse_yaml_flow_mapping(source: str) -> Dict[str, Any]:
    if not source or not source.strip().startswith("{"):
        raise ValueError("property map must be a YAML flow mapping")

    if _yaml is not None:
        try:
            data = _yaml.safe_load(source)
        except _yaml.YAMLError as exc:
            raise ValueError("invalid YAML flow mapping") from exc
        if not isinstance(data, dict):
            raise ValueError("property map must be a mapping")
        properties = _normalize_yaml_value(dict(data))
    else:
        properties = _parse_flow_mapping_subset(source)

    _validate_property_map(properties)
    return properties


def _merge_node_properties(graph: Graph, node: Node, additions: Dict[str, Any]) -> None:
    for key, value in additions.items():
        if key not in node.properties:
            node.properties[key] = value
            continue
        if _values_equivalent(node.properties[key], value):
            continue
        graph.errors.append(
            f"{node.id}: conflicting node property {key!r}: "
            f"{node.properties[key]!r} != {value!r}"
        )


def _values_equivalent(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _values_equivalent(a, b) for a, b in zip(left, right)
        )
    return type(left) is type(right) and left == right


def _validate_property_map(properties: Dict[Any, Any]) -> None:
    for key, value in properties.items():
        if not isinstance(key, str):
            raise ValueError("property map keys must be strings")
        _validate_property_value(value, key)


def _validate_property_value(value: Any, key: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"property {key!r} must contain a finite number")
    if value is None or isinstance(value, (str, bool, int, float)):
        return
    if isinstance(value, list):
        for item in value:
            _validate_property_value(item, key)
        return
    raise ValueError(f"property {key!r} has an unsupported value type")


def resolve_destination(destination: str, source_id: str) -> str:
    raw = destination.strip()
    parsed = urlsplit(raw)

    if parsed.scheme or parsed.netloc:
        without_fragment = raw.split("#", 1)[0]
        return unquote(without_fragment)

    without_fragment = raw.split("#", 1)[0]
    decoded = unquote(without_fragment)
    if not decoded and raw.startswith("#"):
        return source_id
    source_dir = posixpath.dirname(source_id)
    joined = posixpath.normpath(posixpath.join(source_dir, decoded))
    return "" if joined == "." else joined


def _relationship_fingerprint(
    source: str,
    relationship_type: str,
    target: str,
    properties: Dict[str, Any],
) -> str:
    natural_key = [source, relationship_type, target, _canonical_property_value(properties)]
    canonical = json.dumps(
        natural_key,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _canonical_property_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _canonical_property_value(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonical_property_value(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def graph_to_cypher(graph: Graph, relationship_mode: str = "create") -> str:
    if graph.errors:
        raise ValueError("cannot serialize a graph with validation errors")
    if relationship_mode not in {"create", "merge"}:
        raise ValueError("relationship mode must be 'create' or 'merge'")

    aliases = {node_id: f"n{index}" for index, node_id in enumerate(graph.nodes.keys())}
    lines: List[str] = []
    relationship_keyword = relationship_mode.upper()

    for node_id, node in graph.nodes.items():
        alias = aliases[node_id]
        labels = "".join(f":{_cypher_name(label)}" for label in node.labels)
        lines.append(f'MERGE ({alias}{labels} {{id:{_cypher_value(node_id)}}})')
        if node.properties:
            lines.append("SET")
            items = list(node.properties.items())
            for index, (key, value) in enumerate(items):
                comma = "," if index < len(items) - 1 else ""
                lines.append(f"    {alias}.{_cypher_name(key)} = {_cypher_value(value)}{comma}")

    for rel in graph.relationships:
        source = aliases[rel.source]
        target = aliases[rel.target]
        rel_type = _cypher_name(rel.type)
        if not rel.properties:
            lines.append(f"{relationship_keyword} ({source})-[:{rel_type}]->({target})")
            continue

        lines.append(f"{relationship_keyword} ({source})-[:{rel_type} {{")
        items = sorted(rel.properties.items())
        for index, (key, value) in enumerate(items):
            comma = "," if index < len(items) - 1 else ""
            lines.append(f"    {_cypher_name(key)}: {_cypher_value(value)}{comma}")
        lines.append(f"}}]->({target})")

    return "\n".join(lines)


def _markdown_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.suffix.lower() == ".md":
            return [root]
        return []
    return sorted(root.rglob("*.md"))


def _normalize_yaml_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_yaml_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_yaml_value(item) for item in value]
    if isinstance(value, _datetime.date) and not isinstance(value, _datetime.datetime):
        return value.isoformat()
    return value


def _extract_links_markdown_it(markdown: str) -> List[Link]:
    parser = MarkdownIt("commonmark")
    tokens = parser.parse(markdown)
    links: List[Link] = []

    for token in tokens:
        if token.type != "inline" or not token.children:
            continue

        children = token.children
        index = 0
        while index < len(children):
            child = children[index]
            if child.type != "link_open":
                index += 1
                continue

            destination = ""
            attrs = child.attrs or {}
            if isinstance(attrs, dict):
                destination = attrs.get("href", "")
            else:
                for name, value in attrs:
                    if name == "href":
                        destination = value
                        break

            label_parts: List[str] = []
            index += 1
            while index < len(children) and children[index].type != "link_close":
                content = getattr(children[index], "content", "")
                if content:
                    label_parts.append(content)
                index += 1

            links.append(Link(label="".join(label_parts), destination=destination))
            index += 1

    return links


def _parse_flow_mapping_subset(source: str) -> Dict[str, Any]:
    text = source.strip()
    if not (text.startswith("{") and text.endswith("}")):
        raise ValueError("property map must use { }")
    inner = text[1:-1].strip()
    if not inner:
        return {}

    result: Dict[str, Any] = {}
    for item in _split_top_level(inner, ","):
        key, value = _split_mapping_item(item)
        result[_strip_quotes(key.strip())] = _parse_scalar_or_collection(value.strip())
    return result


def _parse_scalar_or_collection(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [] if not inner else [
            _parse_scalar_or_collection(part.strip())
            for part in _split_top_level(inner, ",")
        ]
    if value.startswith("{") and value.endswith("}"):
        return _parse_flow_mapping_subset(value)
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "~"}:
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return _strip_quotes(value)


def _split_mapping_item(item: str) -> Tuple[str, str]:
    quote: Optional[str] = None
    depth = 0
    for index, char in enumerate(item):
        if quote:
            if char == quote and item[index - 1 : index] != "\\":
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char in "[{(":
            depth += 1
        elif char in "]})":
            depth -= 1
        elif char == ":" and depth == 0:
            return item[:index], item[index + 1 :]
    raise ValueError(f"invalid mapping item: {item!r}")


def _split_top_level(text: str, delimiter: str) -> List[str]:
    parts: List[str] = []
    start = 0
    quote: Optional[str] = None
    depth = 0
    for index, char in enumerate(text):
        if quote:
            if char == quote and text[index - 1 : index] != "\\":
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char in "[{(":
            depth += 1
        elif char in "]})":
            depth -= 1
        elif char == delimiter and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return parts


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _cypher_name(name: str) -> str:
    if IDENTIFIER_RE.match(name):
        return name
    return "`" + name.replace("`", "``") + "`"


def _cypher_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_cypher_value(item) for item in value) + "]"
    if isinstance(value, _datetime.date) and not isinstance(value, _datetime.datetime):
        return f'date("{value.isoformat()}")'
    if isinstance(value, str) and DATE_RE.match(value):
        return f'date("{value}")'
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def main(argv: Optional[List[str]] = None) -> int:
    cli = argparse.ArgumentParser(prog="pgmark", description="Parse Property Graph Markdown.")
    subcommands = cli.add_subparsers(dest="command", required=True)

    parse_cmd = subcommands.add_parser("parse", help="parse a Markdown file or directory")
    parse_cmd.add_argument("path", help="Markdown file or directory")
    parse_cmd.add_argument("--cypher", action="store_true", help="emit openCypher")
    parse_cmd.add_argument(
        "--relationship-mode",
        choices=["create", "merge"],
        default="create",
        help="CREATE for an empty snapshot target or idempotent MERGE by natural key",
    )

    args = cli.parse_args(argv)

    if args.command == "parse":
        graph = parse_corpus(args.path)
        for warning in graph.warnings:
            print(f"warning: {warning}", file=sys.stderr)
        for error in graph.errors:
            print(f"error: {error}", file=sys.stderr)
        if graph.errors:
            return 1
        if args.cypher:
            print(graph_to_cypher(graph, relationship_mode=args.relationship_mode))
        else:
            print(f"{len(graph.nodes)} nodes, {len(graph.relationships)} relationships")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
