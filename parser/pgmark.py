#!/usr/bin/env python3
"""Readable reference parser for Property Graph Markdown 0.4.0."""

from __future__ import annotations

import argparse
import base64
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

try:  # Required for OKF frontmatter and Relationship Properties.
    import yaml as _yaml  # type: ignore
except Exception:  # pragma: no cover - exercised only when PyYAML is absent.
    _yaml = None

from markdown_it import MarkdownIt  # type: ignore


IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(?P<yaml>.*?)(?:\r?\n)---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)


@dataclass
class Link:
    text: str
    destination: str
    title: Optional[str] = None


@dataclass
class Node:
    id: str
    type: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    relationships: List["Relationship"] = field(default_factory=list)


@dataclass
class Relationship:
    id: str
    source: str
    target: str
    link_text: str
    title: Optional[str] = None
    type: Optional[str] = None
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
        if _is_okf_reserved_file(file_path):
            continue

        document_id = file_path.relative_to(base).as_posix()
        node_id = concept_id_from_document_id(document_id)
        text = file_path.read_text(encoding="utf-8")

        node = graph.ensure_node(node_id)
        node.type = None
        node.properties = {}
        node.relationships = []

        try:
            node_type, node_properties, markdown_body = parse_okf_document(text)
        except ValueError as exc:
            graph.errors.append(f"{node_id}: {exc}")
            continue

        node.type = node_type
        node.properties = node_properties

        for link in _extract_links_markdown_it(markdown_body):
            if not is_concept_destination(link.destination):
                continue

            relationship_type, properties, diagnostic = parse_relationship_title(
                link.title
            )
            if diagnostic:
                graph.warnings.append(f"{node_id}: {diagnostic}: {link.title!r}")

            target_id = resolve_destination(link.destination, source_id=node_id)
            graph.ensure_node(target_id)
            relationship_id = _relationship_fingerprint(
                source=node_id,
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
                    link_text=link.text,
                    title=link.title,
                    type=relationship_type,
                    properties=properties,
                )
            )

    return graph


def parse_okf_document(markdown: str) -> Tuple[str, Dict[str, Any], str]:
    """Return derived Node type, complete Properties, and Markdown body."""

    match = FRONTMATTER_RE.match(markdown)
    if not match:
        raise ValueError("missing leading OKF YAML frontmatter")
    if _yaml is None:
        raise ValueError("parsing OKF YAML frontmatter requires PyYAML")

    try:
        loaded = _yaml.safe_load(match.group("yaml"))
    except _yaml.YAMLError as exc:
        raise ValueError("invalid OKF YAML frontmatter") from exc
    if not isinstance(loaded, dict):
        raise ValueError("OKF YAML frontmatter must be a mapping")

    metadata = _normalize_yaml_value(dict(loaded))
    _validate_property_map(metadata)
    node_type = metadata.get("type")
    if not isinstance(node_type, str) or not node_type.strip():
        raise ValueError("OKF YAML frontmatter requires a non-empty string 'type'")

    return node_type, metadata, markdown[match.end() :]


def parse_relationship_title(
    title: Optional[str],
) -> Tuple[Optional[str], Dict[str, Any], Optional[str]]:
    """Return derived type, complete Properties, and an optional diagnostic."""

    if title is None or not title.lstrip().startswith("{"):
        return None, {}, None

    try:
        properties = parse_yaml_flow_mapping(title)
    except ValueError as exc:
        return None, {}, f"invalid PGM YAML Flow Mapping title ({exc})"

    relationship_type = properties.get("type")
    if "type" in properties and (
        not isinstance(relationship_type, str) or not relationship_type.strip()
    ):
        return (
            None,
            properties,
            "Relationship Property 'type' is not a non-empty string; "
            "Relationship remains untyped",
        )
    return relationship_type, properties, None


def parse_yaml_flow_mapping(source: str) -> Dict[str, Any]:
    if not source or not source.strip().startswith("{"):
        raise ValueError("property map must be a YAML flow mapping")
    if _yaml is None:
        raise ValueError("parsing Relationship Properties requires PyYAML")

    try:
        data = _yaml.safe_load(source)
    except _yaml.YAMLError as exc:
        raise ValueError("invalid YAML flow mapping") from exc
    if not isinstance(data, dict):
        raise ValueError("property map must be a mapping")
    properties = _normalize_yaml_value(dict(data))

    _validate_property_map(properties)
    return properties


def _validate_property_map(properties: Dict[Any, Any]) -> None:
    for key in properties:
        if not isinstance(key, str):
            raise ValueError("property map keys must be strings")


def concept_id_from_document_id(document_id: str) -> str:
    """Convert an OKF concept document path to its Concept ID."""

    if not document_id.lower().endswith(".md"):
        raise ValueError(f"not a Markdown concept document: {document_id}")
    return document_id[:-3]


def is_concept_destination(destination: str) -> bool:
    """Return whether a CommonMark destination denotes an OKF Concept path."""

    raw = destination.strip()
    if not raw:
        return False
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc:
        return False
    if not parsed.path:
        return bool(parsed.fragment)
    return unquote(parsed.path).lower().endswith(".md")


def resolve_destination(destination: str, source_id: str) -> str:
    raw = destination.strip()
    parsed = urlsplit(raw)

    if parsed.scheme or parsed.netloc:
        raise ValueError("external URI is not an OKF Concept destination")

    decoded = unquote(parsed.path)
    if not decoded and parsed.fragment:
        return source_id

    if decoded.startswith("/"):
        document_id = posixpath.normpath(decoded.lstrip("/"))
    else:
        source_dir = posixpath.dirname(source_id)
        document_id = posixpath.normpath(posixpath.join(source_dir, decoded))
    if document_id in {"", "."}:
        return source_id
    return concept_id_from_document_id(document_id)


def _relationship_fingerprint(
    source: str,
    target: str,
    properties: Dict[str, Any],
) -> str:
    natural_key = [
        source,
        target,
        _canonical_property_value(properties),
    ]
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
        if all(isinstance(key, str) for key in value):
            return {
                key: _canonical_property_value(value[key]) for key in sorted(value)
            }
        entries = [
            [_canonical_property_value(key), _canonical_property_value(item)]
            for key, item in value.items()
        ]
        entries.sort(
            key=lambda entry: json.dumps(
                entry[0], ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
        )
        return {"$yamlType": "mapping", "entries": entries}
    if isinstance(value, list):
        return [_canonical_property_value(item) for item in value]
    if isinstance(value, tuple):
        return [_canonical_property_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        items = [_canonical_property_value(item) for item in value]
        items.sort(
            key=lambda item: json.dumps(
                item, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
        )
        return {"$yamlType": "set", "items": items}
    if isinstance(value, bytes):
        return {
            "$yamlType": "binary",
            "value": base64.b64encode(value).decode("ascii"),
        }
    if isinstance(value, _datetime.datetime):
        return {"$yamlType": "timestamp", "value": value.isoformat()}
    if isinstance(value, _datetime.date):
        return {"$yamlType": "date", "value": value.isoformat()}
    if isinstance(value, float) and not math.isfinite(value):
        return {"$yamlType": "float", "value": repr(value)}
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def graph_to_cypher(graph: Graph, relationship_mode: str = "create") -> str:
    if graph.errors:
        raise ValueError("cannot serialize a graph with validation errors")
    if relationship_mode not in {"create", "merge"}:
        raise ValueError("relationship mode must be 'create' or 'merge'")
    if any(relationship.type is None for relationship in graph.relationships):
        raise ValueError(
            "Cypher export requires a type for every Relationship; "
            "untyped Relationships remain valid PGM"
        )

    aliases = {node_id: f"n{index}" for index, node_id in enumerate(graph.nodes.keys())}
    lines: List[str] = []
    relationship_keyword = relationship_mode.upper()

    for node_id, node in graph.nodes.items():
        alias = aliases[node_id]
        labels = f":{_cypher_name(node.type)}" if node.type else ""
        lines.append(f'MERGE ({alias}{labels} {{id:{_cypher_value(node_id)}}})')
        data_properties = {
            key: value for key, value in node.properties.items() if key != "type"
        }
        if data_properties:
            lines.append("SET")
            items = list(data_properties.items())
            for index, (key, value) in enumerate(items):
                comma = "," if index < len(items) - 1 else ""
                lines.append(f"    {alias}.{_cypher_name(key)} = {_cypher_value(value)}{comma}")

    for rel in graph.relationships:
        source = aliases[rel.source]
        target = aliases[rel.target]
        assert rel.type is not None
        rel_type = _cypher_name(rel.type)
        data_properties = {
            key: value for key, value in rel.properties.items() if key != "type"
        }
        if not data_properties:
            lines.append(f"{relationship_keyword} ({source})-[:{rel_type}]->({target})")
            continue

        lines.append(f"{relationship_keyword} ({source})-[:{rel_type} {{")
        items = sorted(data_properties.items())
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


def _is_okf_reserved_file(path: Path) -> bool:
    return path.name in {"index.md", "log.md"}


def _normalize_yaml_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_yaml_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_yaml_value(item) for item in value]
    if isinstance(value, set):
        return {_normalize_yaml_value(item) for item in value}
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
            title: Optional[str] = None
            attrs = child.attrs or {}
            if isinstance(attrs, dict):
                destination = attrs.get("href", "")
                title = attrs.get("title")
            else:
                for name, value in attrs:
                    if name == "href":
                        destination = value
                    elif name == "title":
                        title = value

            label_parts: List[str] = []
            index += 1
            while index < len(children) and children[index].type != "link_close":
                content = getattr(children[index], "content", "")
                if content:
                    label_parts.append(content)
                index += 1

            links.append(
                Link(
                    text="".join(label_parts),
                    destination=destination,
                    title=title,
                )
            )
            index += 1

    return links


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
        if not math.isfinite(value):
            raise ValueError("Cypher export cannot represent non-finite YAML floats")
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_cypher_value(item) for item in value) + "]"
    if isinstance(value, (set, frozenset, bytes)):
        raise ValueError(
            f"Cypher export cannot represent YAML value of type {type(value).__name__}"
        )
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError(
                "Cypher export cannot represent YAML mappings with non-string keys"
            )
        return "{" + ", ".join(
            f"{_cypher_name(str(key))}: {_cypher_value(item)}"
            for key, item in value.items()
        ) + "}"
    if isinstance(value, _datetime.datetime):
        return f'datetime("{value.isoformat()}")'
    if isinstance(value, _datetime.date):
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
            try:
                cypher = graph_to_cypher(
                    graph, relationship_mode=args.relationship_mode
                )
            except ValueError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
            print(cypher)
        else:
            print(f"{len(graph.nodes)} nodes, {len(graph.relationships)} relationships")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
