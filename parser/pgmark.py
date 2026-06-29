#!/usr/bin/env python3
"""Reference parser for Property Graph Markdown 0.1.1.

The implementation favors readability over completeness. It parses a directory
of Markdown files, interprets YAML frontmatter as node metadata, extracts
semantic CommonMark links, and emits openCypher-compatible statements.
"""

from __future__ import annotations

import argparse
import datetime as _datetime
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
SEMANTIC_RE = re.compile(r"^(?P<type>[A-Z][A-Z0-9_]*)\s*(?P<props>\{.*\})?\s*$")


@dataclass
class Link:
    label: str
    destination: str


@dataclass
class Node:
    id: str
    labels: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relationship:
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    display_label: str = ""


@dataclass
class Graph:
    nodes: Dict[str, Node] = field(default_factory=dict)
    relationships: List[Relationship] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def ensure_node(self, node_id: str) -> Node:
        if node_id not in self.nodes:
            self.nodes[node_id] = Node(id=node_id)
        return self.nodes[node_id]


def parse_corpus(path: str | Path) -> Graph:
    """Parse a Markdown file or directory into a PGM graph."""

    root = Path(path)
    files = list(_markdown_files(root))
    base = root if root.is_dir() else root.parent
    graph = Graph()

    for file_path in files:
        node_id = _canonical_file_id(file_path, base)
        text = file_path.read_text(encoding="utf-8")
        frontmatter, body = split_frontmatter(text)
        labels, properties = parse_node_metadata(frontmatter)

        node = graph.ensure_node(node_id)
        node.labels = labels
        node.properties = properties

        for link in extract_links(body):
            try:
                rel_type, rel_props = parse_relationship_label(link.label)
            except ValueError as exc:
                if _looks_like_relationship_attempt(link.label):
                    graph.warnings.append(f"{node_id}: {exc}: {link.label!r}")
                continue

            target_id = resolve_destination(link.destination, source_id=node_id)
            graph.ensure_node(target_id)

            graph.relationships.append(
                Relationship(
                    source=node_id,
                    target=target_id,
                    type=rel_type,
                    properties=rel_props,
                    display_label="",
                )
            )

    return graph


def split_frontmatter(text: str) -> Tuple[str, str]:
    """Return (frontmatter, body) for a Markdown document."""

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return "", text

    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "".join(lines[1:index]), "".join(lines[index + 1 :])

    return "", text


def parse_node_metadata(frontmatter: str) -> Tuple[List[str], Dict[str, Any]]:
    if not frontmatter.strip():
        return [], {}

    data = parse_yaml_mapping(frontmatter)
    raw_labels = data.pop("labels", [])
    labels = _normalize_labels(raw_labels)
    return labels, data


def parse_relationship_label(label: str) -> Tuple[str, Dict[str, Any]]:
    if "->" in label or "<-" in label:
        raise ValueError("direction markers are not supported in PGM 0.1.1")

    match = SEMANTIC_RE.match(label.strip())
    if not match:
        raise ValueError("malformed relationship descriptor")

    rel_type = match.group("type")
    props_src = match.group("props")
    properties = parse_yaml_flow_mapping(props_src) if props_src else {}
    return rel_type, properties


def extract_links(markdown: str) -> List[Link]:
    """Extract CommonMark links as (visible label, destination)."""

    return _extract_links_markdown_it(markdown)


def _looks_like_relationship_attempt(label: str) -> bool:
    stripped = label.strip()
    return (
        "->" in stripped
        or "<-" in stripped
        or bool(re.match(r"^[A-Z][A-Z0-9_]*\s*\{", stripped))
    )


def parse_yaml_mapping(source: str) -> Dict[str, Any]:
    """Parse a YAML mapping, using PyYAML when available."""

    if _yaml is not None:
        data = _yaml.safe_load(source) or {}
        if not isinstance(data, dict):
            raise ValueError("YAML frontmatter must be a mapping")
        return _normalize_yaml_value(dict(data))

    return _parse_yaml_mapping_subset(source)


def parse_yaml_flow_mapping(source: str) -> Dict[str, Any]:
    """Parse a YAML 1.2 flow mapping used for relationship properties."""

    if not source or not source.strip().startswith("{"):
        raise ValueError("relationship property map must be a YAML flow mapping")

    if _yaml is not None:
        data = _yaml.safe_load(source)
        if not isinstance(data, dict):
            raise ValueError("relationship property map must be a mapping")
        return _normalize_yaml_value(dict(data))

    return _parse_flow_mapping_subset(source)


def resolve_destination(destination: str, source_id: str) -> str:
    """Resolve a Markdown link destination to a canonical node identifier."""

    raw = destination.strip()
    parsed = urlsplit(raw)

    if parsed.scheme or parsed.netloc:
        without_fragment = raw.split("#", 1)[0]
        return unquote(without_fragment)

    without_fragment = raw.split("#", 1)[0]
    decoded = unquote(without_fragment)
    source_dir = posixpath.dirname(source_id)
    joined = posixpath.normpath(posixpath.join(source_dir, decoded))
    return "" if joined == "." else joined


def graph_to_cypher(graph: Graph) -> str:
    aliases = {node_id: f"n{index}" for index, node_id in enumerate(graph.nodes.keys())}
    lines: List[str] = []

    for node_id, node in graph.nodes.items():
        alias = aliases[node_id]
        labels = "".join(f":{_cypher_name(label)}" for label in node.labels)
        lines.append(f'MERGE ({alias}{labels} {{id:{_cypher_value(node_id)}}})')
        if node.properties:
            lines.append("SET")
            items = list(node.properties.items())
            for index, (key, value) in enumerate(items):
                comma = "," if index < len(items) - 1 else ""
                lines.append(f"    {alias}.{_cypher_property(key)} = {_cypher_value(value)}{comma}")

    for rel in graph.relationships:
        source = aliases[rel.source]
        target = aliases[rel.target]
        rel_type = _cypher_name(rel.type)
        if not rel.properties:
            lines.append(f"MERGE ({source})-[:{rel_type}]->({target})")
            continue

        lines.append(f"MERGE ({source})-[:{rel_type} {{")
        items = list(rel.properties.items())
        for index, (key, value) in enumerate(items):
            comma = "," if index < len(items) - 1 else ""
            lines.append(f"    {_cypher_property(key)}: {_cypher_value(value)}{comma}")
        lines.append(f"}}]->({target})")

    return "\n".join(lines)


def _markdown_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.suffix.lower() == ".md":
            return [root]
        return []
    return sorted(root.rglob("*.md"))


def _canonical_file_id(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def _normalize_labels(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        labels = [value]
    elif isinstance(value, list):
        labels = [str(item) for item in value]
    else:
        raise ValueError("labels must be a string or sequence of strings")

    for label in labels:
        if not IDENTIFIER_RE.match(label):
            raise ValueError(f"invalid node label: {label!r}")
    return labels


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


def _parse_yaml_mapping_subset(source: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"unsupported YAML line: {raw_line!r}")
        key, value = line.split(":", 1)
        data[key.strip()] = _parse_scalar_or_collection(value.strip())
    return data


def _parse_flow_mapping_subset(source: str) -> Dict[str, Any]:
    text = source.strip()
    if not (text.startswith("{") and text.endswith("}")):
        raise ValueError("relationship property map must use { }")

    inner = text[1:-1].strip()
    if not inner:
        return {}

    result: Dict[str, Any] = {}
    for item in _split_top_level(inner, ","):
        key, value = _split_mapping_item(item)
        result[_strip_quotes(key.strip())] = _parse_scalar_or_collection(value.strip())
    return result


def _parse_scalar_or_collection(value: str) -> Any:
    if value == "":
        return ""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar_or_collection(part.strip()) for part in _split_top_level(inner, ",")]
    if value.startswith("{") and value.endswith("}"):
        return _parse_flow_mapping_subset(value)

    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "~"}:
        return None
    if re.match(r"^-?\d+$", value):
        return int(value)
    if re.match(r"^-?\d+\.\d+$", value):
        return float(value)
    return _strip_quotes(value)


def _split_mapping_item(item: str) -> Tuple[str, str]:
    quote: Optional[str] = None
    depth = 0
    for index, char in enumerate(item):
        if quote:
            if char == quote and item[index - 1 : index] != "\\":
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char in "[{(":
            depth += 1
            continue
        if char in "]})":
            depth -= 1
            continue
        if char == ":" and depth == 0:
            return item[:index], item[index + 1 :]
    raise ValueError(f"invalid mapping item: {item!r}")


def _split_top_level(text: str, delimiter: str) -> List[str]:
    parts: List[str] = []
    buffer: List[str] = []
    quote: Optional[str] = None
    depth = 0

    for index, char in enumerate(text):
        if quote:
            buffer.append(char)
            if char == quote and text[index - 1 : index] != "\\":
                quote = None
            continue

        if char in {"'", '"'}:
            quote = char
            buffer.append(char)
            continue
        if char in "[{(":
            depth += 1
            buffer.append(char)
            continue
        if char in "]})":
            depth -= 1
            buffer.append(char)
            continue
        if char == delimiter and depth == 0:
            parts.append("".join(buffer).strip())
            buffer = []
            continue

        buffer.append(char)

    if buffer:
        parts.append("".join(buffer).strip())
    return parts


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _cypher_name(name: str) -> str:
    if IDENTIFIER_RE.match(name):
        return name
    return "`" + name.replace("`", "``") + "`"


def _cypher_property(name: str) -> str:
    return name if IDENTIFIER_RE.match(name) else _cypher_name(name)


def _cypher_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
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

    args = cli.parse_args(argv)

    if args.command == "parse":
        graph = parse_corpus(args.path)
        for warning in graph.warnings:
            print(f"warning: {warning}", file=sys.stderr)
        if args.cypher:
            print(graph_to_cypher(graph))
        else:
            print(f"{len(graph.nodes)} nodes, {len(graph.relationships)} relationships")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
