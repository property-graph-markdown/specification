#!/usr/bin/env python3
"""Reference processor for Property Graph Markdown 0.4.0 Public Draft."""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import unquote_to_bytes, urlsplit

from markdown_it import MarkdownIt  # type: ignore

from canonical import (
    CanonicalizationError,
    canonical_document,
    canonical_json,
    decode_canonical_document,
    relationship_id,
    relationship_key,
)
from validation import (
    OKF_COMMIT,
    OKF_SPEC_SHA256,
    PGMValidationError,
    ValidationIssue,
    parse_okf_concept,
    parse_pgm_relationship_properties,
    validate_reserved_document,
)


PGM_VERSION = "0.4.0"
PGM_STATUS = "Public Draft"
PGM_VERSION_LABEL = f"{PGM_VERSION} {PGM_STATUS}"
PROCESSOR_NAME = "pgmark"
PROCESSOR_VERSION = "0.4.0a1"
EXCHANGE_PROFILE = "PGM JSON Exchange Profile v1"
EXCHANGE_SCHEMA = "urn:pgm:schema:graph:1"
MARKDOWN_PROFILE = "CommonMark 0.31.2"
YAML_PROFILE = "YAML 1.2.2 Core Schema"
CONFORMANCE_CLASSES = (
    "PGM Core Processor",
    "Portable Relationship Identification Processor",
    "PGM JSON Exchange Processor",
)
YAML_EXPLICIT_TAGS = (
    "tag:yaml.org,2002:binary",
    "tag:yaml.org,2002:set",
    "tag:yaml.org,2002:timestamp",
)
YAML_ALIAS_POLICY = "acyclic-expand-by-value; cycles-rejected"
DIAGNOSTIC_CATEGORIES = {
    "coreErrors": "error",
    "warnings": "warning",
    "adapterErrors": "adapter-error",
}

CONCEPT_ID_PROPERTY = "pgm_concept_id"
RESOLVED_PROPERTY = "pgm_resolved"
TYPE_PROPERTY = "pgm_type"
PROPERTIES_JSON_PROPERTY = "pgm_properties_json"
RELATIONSHIP_ID_PROPERTY = "pgm_relationship_id"
RELATIONSHIP_KEY_PROPERTY = "pgm_relationship_key"
OCCURRENCE_PROPERTY = "pgm_occurrence"
NATIVE_NODE_LABEL = "PGMConcept"
NATIVE_RELATIONSHIP_TYPE = "PGM_RELATIONSHIP"

MALFORMED_PERCENT_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")
RELATIONSHIP_KEY_RE = re.compile(r"^pgmkey:v1:sha256:[0-9a-f]{64}$")
RELATIONSHIP_ID_RE = re.compile(r"^pgmrel:v1:sha256:[0-9a-f]{64}$")
YAML_SEPARATION_CHARACTERS = " \t\r\n"


class DestinationError(ValueError):
    """A path-looking Link destination that cannot be a Concept destination."""


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class Relationship:
    id: str
    key: str
    occurrence: int
    source: str
    target: str
    link_text: str
    title: Optional[str] = None
    type: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    document: Optional[str] = None

    def display(self) -> str:
        prefix = f"{self.document}: " if self.document else ""
        return prefix + self.message

    def as_json(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.document is not None:
            result["document"] = self.document
        return result


@dataclass
class Graph:
    nodes: Dict[str, Node] = field(default_factory=dict)
    diagnostics: List[Diagnostic] = field(default_factory=list)

    @property
    def relationships(self) -> List[Relationship]:
        return [
            relationship
            for node_id in sorted(self.nodes)
            for relationship in self.nodes[node_id].relationships
        ]

    @property
    def warnings(self) -> List[str]:
        return [
            diagnostic.display()
            for diagnostic in self.diagnostics
            if diagnostic.severity == "warning"
        ]

    @property
    def errors(self) -> List[str]:
        return [
            diagnostic.display()
            for diagnostic in self.diagnostics
            if diagnostic.severity == "error"
        ]

    def add_error(self, code: str, message: str, document: Optional[str] = None) -> None:
        self.diagnostics.append(Diagnostic("error", code, message, document))

    def add_warning(
        self, code: str, message: str, document: Optional[str] = None
    ) -> None:
        self.diagnostics.append(Diagnostic("warning", code, message, document))


def parse_corpus(path: str | Path) -> Graph:
    """Parse one file or Knowledge Bundle into a PGM Core Result candidate."""

    root = Path(path)
    graph = Graph()
    try:
        if root.is_symlink():
            graph.add_error(
                "PGM_INPUT_SYMLINK_UNSUPPORTED",
                "the reference processor does not follow a symbolic-link input root",
            )
            return graph
        if not root.exists():
            graph.add_error(
                "PGM_INPUT_NOT_FOUND", f"input path does not exist: {root}"
            )
            return graph
        if root.is_file():
            if not root.name.endswith(".md"):
                graph.add_error(
                    "PGM_INPUT_NOT_MARKDOWN",
                    "a single-file input must have the exact lowercase .md suffix",
                )
                return graph
            files = [root]
            base = root.parent
        elif root.is_dir():
            base = root
            files = []
            for candidate in sorted(root.rglob("*.md")):
                document_id = candidate.relative_to(base).as_posix()
                if candidate.is_symlink():
                    graph.add_error(
                        "PGM_INPUT_SYMLINK_UNSUPPORTED",
                        "the reference processor does not follow symbolic-link Markdown files",
                        document_id,
                    )
                elif candidate.is_file():
                    files.append(candidate)
        else:
            graph.add_error(
                "PGM_INPUT_KIND_UNSUPPORTED",
                "input must be a regular Markdown file or Knowledge Bundle directory",
            )
            return graph
    except OSError as exc:
        graph.add_error(
            "PGM_INPUT_SCAN_FAILED",
            f"could not inspect input path: {exc.strerror or type(exc).__name__}",
        )
        return graph

    key_preimages: Dict[str, Tuple[str, str, str]] = {}
    id_semantics: Dict[str, Tuple[Tuple[str, str, str], int]] = {}

    for file_path in files:
        document_id = file_path.relative_to(base).as_posix()
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            graph.add_error(
                "OKF_MARKDOWN_UTF8_INVALID",
                "OKF Markdown documents must be valid UTF-8",
                document_id,
            )
            continue
        except OSError as exc:
            graph.add_error(
                "PGM_INPUT_READ_FAILED",
                f"could not read Markdown document: "
                f"{exc.strerror or type(exc).__name__}",
                document_id,
            )
            continue
        if _is_okf_reserved_file(file_path):
            for issue in validate_reserved_document(document_id, text):
                graph.add_error(issue.code, issue.message, document_id)
            continue

        try:
            node_id = concept_id_from_document_id(document_id)
        except ValueError as exc:
            graph.add_error("OKF_CONCEPT_PATH_INVALID", str(exc), document_id)
            continue

        node = Node(id=node_id)
        graph.nodes[node_id] = node

        try:
            node_type, node_properties, markdown_body = parse_okf_document(text)
        except PGMValidationError as exc:
            graph.add_error(exc.code, str(exc), node_id)
            continue
        except ValueError as exc:
            graph.add_error("PGM_CONCEPT_INVALID", str(exc), node_id)
            continue

        node.type = node_type
        node.properties = node_properties
        key_occurrences: Dict[Tuple[str, str, str], int] = defaultdict(int)

        for link in _extract_links_markdown_it(markdown_body):
            try:
                target_id = resolve_destination(link.destination, source_id=node_id)
            except DestinationError as exc:
                if _looks_like_local_markdown_destination(link.destination):
                    graph.add_warning(
                        "PGM_CONCEPT_DESTINATION_INVALID",
                        str(exc),
                        node_id,
                    )
                continue

            relationship_type, properties, issue = parse_relationship_title(link.title)
            if issue is not None:
                graph.add_warning(
                    issue.code,
                    f"{issue.message}: {link.title!r}",
                    node_id,
                )

            try:
                property_preimage = canonical_json(properties)
                semantic_key = relationship_key(node_id, target_id, properties)
            except CanonicalizationError as exc:
                graph.add_error(
                    "PGM_RELATIONSHIP_CANONICALIZATION_FAILED", str(exc), node_id
                )
                continue
            key_preimage = (node_id, target_id, property_preimage)
            previous_key_preimage = key_preimages.setdefault(
                semantic_key, key_preimage
            )
            if previous_key_preimage != key_preimage:
                graph.add_error(
                    "PGM_RELATIONSHIP_KEY_COLLISION",
                    "different Relationship key preimages produced the same digest",
                    node_id,
                )

            occurrence = key_occurrences[key_preimage]
            key_occurrences[key_preimage] += 1
            occurrence_id = relationship_id(semantic_key, occurrence)
            id_semantic = (key_preimage, occurrence)
            previous_id_semantic = id_semantics.setdefault(
                occurrence_id, id_semantic
            )
            if previous_id_semantic != id_semantic:
                graph.add_error(
                    "PGM_RELATIONSHIP_ID_COLLISION",
                    "different Relationship occurrence semantics produced the same ID",
                    node_id,
                )
            node.relationships.append(
                Relationship(
                    id=occurrence_id,
                    key=semantic_key,
                    occurrence=occurrence,
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
    """Return derived Node Type, complete Properties, and Markdown body."""

    parsed = parse_okf_concept(markdown)
    return parsed.metadata["type"], parsed.metadata, parsed.body


def parse_relationship_title(
    title: Optional[str],
) -> Tuple[Optional[str], Dict[str, Any], Optional[ValidationIssue]]:
    """Return derived Type, complete Properties, and an optional warning."""

    if title is None or not title.lstrip(YAML_SEPARATION_CHARACTERS).startswith("{"):
        return None, {}, None

    try:
        properties, diagnostic = parse_pgm_relationship_properties(title)
    except PGMValidationError as exc:
        return (
            None,
            {},
            ValidationIssue(
                exc.code,
                f"invalid PGM YAML Flow Mapping title ({exc})",
            ),
        )

    relationship_type = properties.get("type")
    if diagnostic is not None:
        return None, properties, diagnostic
    return relationship_type, properties, None


def parse_yaml_flow_mapping(source: str) -> Dict[str, Any]:
    properties, _ = parse_pgm_relationship_properties(source)
    return properties


def concept_id_from_document_id(document_id: str) -> str:
    """Convert an exact lowercase-.md OKF document path to a Concept ID."""

    if not document_id.endswith(".md"):
        raise ValueError(f"not a lowercase .md Concept document: {document_id}")
    concept_id = document_id[:-3]
    segments = concept_id.split("/")
    if (
        concept_id.startswith("/")
        or "\\" in concept_id
        or any(_is_c0_or_delete(character) for character in concept_id)
        or any(segment in {"", ".", ".."} for segment in segments)
    ):
        raise ValueError(f"not a portable bundle-relative Concept path: {document_id}")
    return concept_id


def is_concept_destination(destination: str, source_id: str = "source") -> bool:
    """Return whether a destination resolves to an in-bundle Concept ID."""

    try:
        resolve_destination(destination, source_id)
    except DestinationError:
        return False
    return True


def resolve_destination(destination: str, source_id: str) -> str:
    """Resolve a parsed Markdown destination under the normative PGM rules."""

    raw = destination
    if not raw:
        raise DestinationError("empty Link destination is not a Concept destination")
    if any(ord(character) <= 0x20 or ord(character) == 0x7F for character in raw):
        raise DestinationError(
            "Concept destination contains an unescaped space or control character"
        )
    if "?" in raw.split("#", 1)[0]:
        raise DestinationError("query-bearing Link is not a Concept destination")
    try:
        parsed = urlsplit(raw)
    except ValueError as exc:
        raise DestinationError("malformed URI-reference") from exc
    if parsed.scheme or parsed.netloc:
        raise DestinationError("external URI is not a Concept destination")
    if not parsed.path:
        raise DestinationError("fragment-only Link is not a Concept destination")

    raw_segments = parsed.path.split("/")
    decoded_segments = [_decode_path_segment(segment) for segment in raw_segments]
    absolute = parsed.path.startswith("/")
    stack = [] if absolute else [
        segment for segment in posixpath.dirname(source_id).split("/") if segment
    ]

    for segment in decoded_segments:
        if segment in {"", "."}:
            continue
        if segment == "..":
            if not stack:
                raise DestinationError(
                    "Concept destination escapes the Knowledge Bundle root"
                )
            stack.pop()
            continue
        stack.append(segment)

    if not stack:
        raise DestinationError("Concept destination has no document path")
    final_segment = stack[-1]
    if not final_segment.endswith(".md"):
        raise DestinationError("Concept destination must end with exact lowercase .md")
    if final_segment in {"index.md", "log.md"}:
        raise DestinationError("reserved OKF document is not a Concept destination")

    document_id = "/".join(stack)
    return concept_id_from_document_id(document_id)


def _decode_path_segment(segment: str) -> str:
    if MALFORMED_PERCENT_RE.search(segment):
        raise DestinationError("malformed percent escape in Concept destination")
    try:
        decoded = unquote_to_bytes(segment).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise DestinationError(
            "Concept destination contains invalid percent-encoded UTF-8"
        ) from exc
    if any(_is_c0_or_delete(character) for character in decoded):
        raise DestinationError("Concept destination contains a control character")
    if "/" in decoded or "\\" in decoded:
        raise DestinationError(
            "a percent-decoded path segment contains a path separator"
        )
    return decoded


def _looks_like_local_markdown_destination(destination: str) -> bool:
    raw = destination
    if not raw:
        return False
    if any(ord(character) <= 0x20 or ord(character) == 0x7F for character in raw):
        return True
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return True
    if parsed.scheme or parsed.netloc:
        return False
    return ".md" in parsed.path.lower() or parsed.path.startswith((".", "/"))


def _is_c0_or_delete(character: str) -> bool:
    codepoint = ord(character)
    return codepoint <= 0x1F or codepoint == 0x7F


def graph_to_data(graph: Graph) -> Dict[str, Any]:
    """Return the deterministic reference JSON graph serialization data."""

    _require_exportable(graph)
    nodes = []
    for node_id in sorted(graph.nodes):
        node = graph.nodes[node_id]
        nodes.append(
            {
                "id": node.id,
                "type": node.type,
                "properties": canonical_document(node.properties),
            }
        )

    relationships = []
    for relationship in _sorted_relationships(graph):
        relationships.append(
            {
                "id": relationship.id,
                "relationshipKey": relationship.key,
                "occurrence": relationship.occurrence,
                "source": relationship.source,
                "target": relationship.target,
                "resolved": relationship.target in graph.nodes,
                "type": relationship.type,
                "properties": canonical_document(relationship.properties),
                "linkText": relationship.link_text,
                "title": relationship.title,
            }
        )

    return {
        "format": "pgm-graph",
        "formatVersion": "1",
        "pgmVersion": PGM_VERSION_LABEL,
        "conformance": {
            "classes": list(CONFORMANCE_CLASSES),
            "processorName": PROCESSOR_NAME,
            "processorVersion": PROCESSOR_VERSION,
            "exchangeProfile": EXCHANGE_PROFILE,
            "schema": EXCHANGE_SCHEMA,
            "okfCommit": OKF_COMMIT,
            "okfSpecSha256": OKF_SPEC_SHA256,
            "markdownProfile": MARKDOWN_PROFILE,
            "yamlProfile": YAML_PROFILE,
            "yamlExplicitTags": list(YAML_EXPLICIT_TAGS),
            "yamlAliasPolicy": YAML_ALIAS_POLICY,
            "diagnosticCategories": dict(DIAGNOSTIC_CATEGORIES),
        },
        "nodes": nodes,
        "relationships": relationships,
        "diagnostics": [diagnostic.as_json() for diagnostic in graph.diagnostics],
    }


def graph_to_json(graph: Graph, *, pretty: bool = True) -> str:
    data = graph_to_data(graph)
    if pretty:
        return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return json.dumps(
        data, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def graph_from_data(data: Any) -> Graph:
    """Validate and import one PGM JSON Exchange Profile v1 object."""

    root = _require_object(
        data,
        {
            "format",
            "formatVersion",
            "pgmVersion",
            "conformance",
            "nodes",
            "relationships",
            "diagnostics",
        },
        "PGM graph document",
    )
    _require_equal(root["format"], "pgm-graph", "format")
    _require_equal(root["formatVersion"], "1", "formatVersion")
    _require_equal(root["pgmVersion"], PGM_VERSION_LABEL, "pgmVersion")

    conformance = _require_object(
        root["conformance"],
        {
            "classes",
            "processorName",
            "processorVersion",
            "exchangeProfile",
            "schema",
            "okfCommit",
            "okfSpecSha256",
            "markdownProfile",
            "yamlProfile",
            "yamlExplicitTags",
            "yamlAliasPolicy",
            "diagnosticCategories",
        },
        "conformance statement",
    )
    expected_conformance = {
        "exchangeProfile": EXCHANGE_PROFILE,
        "schema": EXCHANGE_SCHEMA,
        "okfCommit": OKF_COMMIT,
        "okfSpecSha256": OKF_SPEC_SHA256,
        "yamlProfile": YAML_PROFILE,
        "yamlAliasPolicy": YAML_ALIAS_POLICY,
        "diagnosticCategories": DIAGNOSTIC_CATEGORIES,
    }
    for name, expected in expected_conformance.items():
        _require_equal(conformance[name], expected, f"conformance.{name}")
    _require_required_unique_strings(
        conformance["classes"], CONFORMANCE_CLASSES, "conformance.classes"
    )
    _require_required_unique_strings(
        conformance["yamlExplicitTags"],
        YAML_EXPLICIT_TAGS,
        "conformance.yamlExplicitTags",
    )
    _require_nonempty_string(
        conformance["markdownProfile"], "conformance.markdownProfile"
    )
    _require_nonempty_string(
        conformance["processorName"], "conformance.processorName"
    )
    _require_nonempty_string(
        conformance["processorVersion"], "conformance.processorVersion"
    )

    raw_nodes = _require_array(root["nodes"], "nodes")
    raw_relationships = _require_array(root["relationships"], "relationships")
    raw_diagnostics = _require_array(root["diagnostics"], "diagnostics")
    graph = Graph()

    for index, raw_node in enumerate(raw_nodes):
        context = f"nodes[{index}]"
        item = _require_object(raw_node, {"id", "type", "properties"}, context)
        node_id = _require_concept_id(item["id"], f"{context}.id")
        if node_id in graph.nodes:
            raise ValueError(f"duplicate Node ID: {node_id!r}")
        node_type = _require_optional_type(item["type"], f"{context}.type")
        if node_type is None:
            raise ValueError(f"{context}.type must not be null")
        properties = _decode_property_map(item["properties"], f"{context}.properties")
        if properties.get("type") != node_type:
            raise ValueError(
                f"{context}.type does not equal the retained 'type' Property"
            )
        graph.nodes[node_id] = Node(
            id=node_id,
            type=node_type,
            properties=properties,
        )

    relationship_ids: Dict[
        str, Tuple[Tuple[str, str, str], int]
    ] = {}
    key_preimages: Dict[str, Tuple[str, str, str]] = {}
    ordinals: Dict[Tuple[str, str], set[int]] = defaultdict(set)
    for index, raw_relationship in enumerate(raw_relationships):
        context = f"relationships[{index}]"
        item = _require_object(
            raw_relationship,
            {
                "id",
                "relationshipKey",
                "occurrence",
                "source",
                "target",
                "resolved",
                "type",
                "properties",
                "linkText",
                "title",
            },
            context,
        )
        source = _require_concept_id(item["source"], f"{context}.source")
        target = _require_concept_id(item["target"], f"{context}.target")
        if source not in graph.nodes:
            raise ValueError(f"{context}.source does not identify an imported Node")
        if not isinstance(item["resolved"], bool):
            raise ValueError(f"{context}.resolved must be a boolean")
        actually_resolved = target in graph.nodes
        if item["resolved"] is not actually_resolved:
            raise ValueError(
                f"{context}.resolved disagrees with target Node membership"
            )

        properties = _decode_property_map(item["properties"], f"{context}.properties")
        derived_type = properties.get("type")
        if not isinstance(derived_type, str) or not derived_type:
            derived_type = None
        imported_type = _require_optional_type(item["type"], f"{context}.type")
        if imported_type != derived_type:
            raise ValueError(
                f"{context}.type does not equal the Type derived from Properties"
            )

        semantic_key = _require_nonempty_string(
            item["relationshipKey"], f"{context}.relationshipKey"
        )
        if not RELATIONSHIP_KEY_RE.fullmatch(semantic_key):
            raise ValueError(f"{context}.relationshipKey has an invalid v1 shape")
        expected_key = relationship_key(source, target, properties)
        if semantic_key != expected_key:
            raise ValueError(f"{context}.relationshipKey fails semantic verification")
        key_preimage = (source, target, canonical_json(properties))
        previous_key_preimage = key_preimages.setdefault(
            semantic_key, key_preimage
        )
        if previous_key_preimage != key_preimage:
            raise ValueError(
                f"{context}.relationshipKey collides with a different preimage"
            )

        occurrence = item["occurrence"]
        if (
            isinstance(occurrence, bool)
            or not isinstance(occurrence, int)
            or occurrence < 0
        ):
            raise ValueError(f"{context}.occurrence must be a non-negative integer")
        occurrence_group = (source, semantic_key)
        if occurrence in ordinals[occurrence_group]:
            raise ValueError(f"duplicate occurrence ordinal in {context}")
        ordinals[occurrence_group].add(occurrence)

        occurrence_id = _require_nonempty_string(item["id"], f"{context}.id")
        if not RELATIONSHIP_ID_RE.fullmatch(occurrence_id):
            raise ValueError(f"{context}.id has an invalid v1 shape")
        if occurrence_id != relationship_id(semantic_key, occurrence):
            raise ValueError(f"{context}.id fails occurrence verification")
        id_semantic = (key_preimage, occurrence)
        previous_id_semantic = relationship_ids.get(occurrence_id)
        if previous_id_semantic is not None:
            if previous_id_semantic != id_semantic:
                raise ValueError(
                    f"{context}.id collides with different occurrence semantics"
                )
            raise ValueError(f"duplicate Relationship ID: {occurrence_id!r}")
        relationship_ids[occurrence_id] = id_semantic

        link_text = _require_string(item["linkText"], f"{context}.linkText")
        title = item["title"]
        if title is not None:
            title = _require_string(title, f"{context}.title")
        graph.nodes[source].relationships.append(
            Relationship(
                id=occurrence_id,
                key=semantic_key,
                occurrence=occurrence,
                source=source,
                target=target,
                link_text=link_text,
                title=title,
                type=imported_type,
                properties=properties,
            )
        )

    for (source, semantic_key), observed in ordinals.items():
        expected = set(range(len(observed)))
        if observed != expected:
            raise ValueError(
                "Relationship occurrence ordinals must be contiguous from zero "
                f"for source {source!r} and key {semantic_key!r}"
            )

    for index, raw_diagnostic in enumerate(raw_diagnostics):
        context = f"diagnostics[{index}]"
        if not isinstance(raw_diagnostic, dict):
            raise ValueError(f"{context} must be an object")
        required = {"severity", "code", "message"}
        allowed = required | {"document"}
        if set(raw_diagnostic) - allowed or not required.issubset(raw_diagnostic):
            raise ValueError(f"{context} has missing or unknown members")
        _require_equal(raw_diagnostic["severity"], "warning", f"{context}.severity")
        code = _require_nonempty_string(raw_diagnostic["code"], f"{context}.code")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", code):
            raise ValueError(f"{context}.code is not a stable diagnostic code")
        message = _require_nonempty_string(
            raw_diagnostic["message"], f"{context}.message"
        )
        document = raw_diagnostic.get("document")
        if document is not None:
            document = _require_nonempty_string(document, f"{context}.document")
        graph.diagnostics.append(Diagnostic("warning", code, message, document))

    return graph


def graph_from_json(source: str) -> Graph:
    """Parse and import one UTF-8 PGM JSON Exchange Profile v1 document."""

    if not isinstance(source, str):
        raise ValueError("JSON source must be text")
    try:
        data = json.loads(
            source,
            object_pairs_hook=_reject_duplicate_json_members,
            parse_constant=_reject_nonfinite_json_number,
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid PGM graph JSON: {exc.msg}") from exc
    return graph_from_data(data)


def graph_to_cypher(graph: Graph, relationship_mode: str = "create") -> str:
    """Return an informative, lossless generic-property Cypher projection."""

    _require_exportable(graph)
    if relationship_mode not in {"create", "merge"}:
        raise ValueError("relationship mode must be 'create' or 'merge'")

    all_ids = sorted(
        set(graph.nodes) | {relationship.target for relationship in graph.relationships}
    )
    aliases = {node_id: f"n{index}" for index, node_id in enumerate(all_ids)}
    lines: List[str] = []

    for node_id in all_ids:
        alias = aliases[node_id]
        lines.append(
            f"MERGE ({alias}:{NATIVE_NODE_LABEL} "
            f"{{{CONCEPT_ID_PROPERTY}:{_cypher_string(node_id)}}})"
        )
        node = graph.nodes.get(node_id)
        if node is None:
            lines.append(
                f"ON CREATE SET {alias}.{RESOLVED_PROPERTY} = false"
            )
            continue
        lines.append(f"SET {alias}.{RESOLVED_PROPERTY} = true")
        lines.append(
            f"SET {alias}.{TYPE_PROPERTY} = {_cypher_string(node.type or '')}"
        )
        lines.append(
            f"SET {alias}.{PROPERTIES_JSON_PROPERTY} = "
            f"{_cypher_string(canonical_json(node.properties))}"
        )

    keyword = relationship_mode.upper()
    for index, relationship in enumerate(_sorted_relationships(graph)):
        source = aliases[relationship.source]
        target = aliases[relationship.target]
        rel_alias = f"r{index}"
        if relationship_mode == "create":
            properties = [
                f"{RELATIONSHIP_ID_PROPERTY}:{_cypher_string(relationship.id)}",
                f"{RELATIONSHIP_KEY_PROPERTY}:{_cypher_string(relationship.key)}",
                f"{OCCURRENCE_PROPERTY}:{relationship.occurrence}",
                f"{PROPERTIES_JSON_PROPERTY}:"
                f"{_cypher_string(canonical_json(relationship.properties))}",
            ]
            if relationship.type is not None:
                properties.append(
                    f"{TYPE_PROPERTY}:{_cypher_string(relationship.type)}"
                )
            lines.append(
                f"{keyword} ({source})-[{rel_alias}:{NATIVE_RELATIONSHIP_TYPE} "
                "{" + ",".join(properties) + f"}}]->({target})"
            )
            continue

        lines.append(
            f"{keyword} ({source})-[{rel_alias}:{NATIVE_RELATIONSHIP_TYPE} "
            f"{{{RELATIONSHIP_ID_PROPERTY}:{_cypher_string(relationship.id)}}}]"
            f"->({target})"
        )
        lines.append(
            f"SET {rel_alias}.{RELATIONSHIP_KEY_PROPERTY} = "
            f"{_cypher_string(relationship.key)}"
        )
        lines.append(
            f"SET {rel_alias}.{OCCURRENCE_PROPERTY} = {relationship.occurrence}"
        )
        lines.append(
            f"SET {rel_alias}.{PROPERTIES_JSON_PROPERTY} = "
            f"{_cypher_string(canonical_json(relationship.properties))}"
        )
        if relationship.type is not None:
            lines.append(
                f"SET {rel_alias}.{TYPE_PROPERTY} = "
                f"{_cypher_string(relationship.type)}"
            )

    return "\n".join(lines)


def _require_object(value: Any, members: set[str], context: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object")
    actual = set(value)
    if actual != members:
        missing = sorted(members - actual)
        unknown = sorted(actual - members)
        details = []
        if missing:
            details.append(f"missing {missing}")
        if unknown:
            details.append(f"unknown {unknown}")
        raise ValueError(f"{context} has " + " and ".join(details))
    return value


def _require_array(value: Any, context: str) -> List[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be an array")
    return value


def _require_required_unique_strings(
    value: Any, required: Sequence[str], context: str
) -> List[str]:
    raw_items = _require_array(value, context)
    items = [
        _require_nonempty_string(item, f"{context}[{index}]")
        for index, item in enumerate(raw_items)
    ]
    if len(items) != len(set(items)):
        raise ValueError(f"{context} must contain unique strings")
    missing = [item for item in required if item not in items]
    if missing:
        raise ValueError(f"{context} is missing required values {missing!r}")
    return items


def _require_equal(value: Any, expected: Any, context: str) -> None:
    if value != expected or type(value) is not type(expected):
        raise ValueError(f"{context} must equal {expected!r}")


def _require_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{context} must be a string")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{context} contains invalid Unicode") from exc
    return value


def _require_nonempty_string(value: Any, context: str) -> str:
    result = _require_string(value, context)
    if not result:
        raise ValueError(f"{context} must not be empty")
    return result


def _require_optional_type(value: Any, context: str) -> Optional[str]:
    if value is None:
        return None
    return _require_nonempty_string(value, context)


def _require_concept_id(value: Any, context: str) -> str:
    concept_id = _require_nonempty_string(value, context)
    segments = concept_id.split("/")
    if (
        concept_id.startswith("/")
        or "\\" in concept_id
        or any(_is_c0_or_delete(character) for character in concept_id)
        or any(segment in {"", ".", ".."} for segment in segments)
        or segments[-1] in {"index", "log"}
    ):
        raise ValueError(f"{context} is not a bundle-relative PGM Concept ID")
    return concept_id


def _decode_property_map(value: Any, context: str) -> Dict[str, Any]:
    try:
        decoded = decode_canonical_document(value)
    except CanonicalizationError as exc:
        raise ValueError(f"{context} is not canonical PGM value encoding v1") from exc
    if not isinstance(decoded, dict) or any(
        not isinstance(key, str) for key in decoded
    ):
        raise ValueError(f"{context} must decode to a string-keyed Property map")
    return decoded


def _reject_duplicate_json_members(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object member: {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_json_number(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not permitted: {value}")


def _require_exportable(graph: Graph) -> None:
    if not isinstance(graph, Graph):
        raise ValueError("export value must be a PGM Graph")
    if not isinstance(graph.nodes, dict):
        raise ValueError("graph.nodes must be a Node map")
    if not isinstance(graph.diagnostics, list):
        raise ValueError("graph.diagnostics must be a list")

    has_errors = False
    for index, diagnostic in enumerate(graph.diagnostics):
        context = f"diagnostics[{index}]"
        if not isinstance(diagnostic, Diagnostic):
            raise ValueError(f"{context} must be a Diagnostic")
        severity = _require_nonempty_string(
            diagnostic.severity, f"{context}.severity"
        )
        if severity == "error":
            has_errors = True
        elif severity != "warning":
            raise ValueError(f"{context}.severity must be 'warning' or 'error'")
        code = _require_nonempty_string(diagnostic.code, f"{context}.code")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", code):
            raise ValueError(f"{context}.code is not a stable diagnostic code")
        _require_nonempty_string(diagnostic.message, f"{context}.message")
        if diagnostic.document is not None:
            _require_nonempty_string(diagnostic.document, f"{context}.document")
    if has_errors:
        raise ValueError("cannot serialize a graph with validation errors")

    node_ids = set()
    for graph_key, node in graph.nodes.items():
        node_id = _require_concept_id(graph_key, "graph Node-map key")
        if not isinstance(node, Node):
            raise ValueError(f"graph.nodes[{node_id!r}] must be a Node")
        retained_id = _require_concept_id(
            node.id, f"graph.nodes[{node_id!r}].id"
        )
        if retained_id != node_id:
            raise ValueError(
                f"graph.nodes[{node_id!r}].id does not equal its Node-map key"
            )
        node_type = _require_optional_type(
            node.type, f"graph.nodes[{node_id!r}].type"
        )
        if node_type is None:
            raise ValueError(f"graph.nodes[{node_id!r}].type must not be null")
        properties = _require_export_property_map(
            node.properties, f"graph.nodes[{node_id!r}].properties"
        )
        if properties.get("type") != node_type:
            raise ValueError(
                f"graph.nodes[{node_id!r}].type does not equal the retained "
                "'type' Property"
            )
        if not isinstance(node.relationships, list):
            raise ValueError(
                f"graph.nodes[{node_id!r}].relationships must be a list"
            )
        node_ids.add(node_id)

    relationship_ids: Dict[
        str, Tuple[Tuple[str, str, str], int]
    ] = {}
    key_preimages: Dict[str, Tuple[str, str, str]] = {}
    ordinals: Dict[Tuple[str, str], set[int]] = defaultdict(set)
    for owner_id, node in graph.nodes.items():
        for index, relationship in enumerate(node.relationships):
            context = f"graph.nodes[{owner_id!r}].relationships[{index}]"
            if not isinstance(relationship, Relationship):
                raise ValueError(f"{context} must be a Relationship")

            source = _require_concept_id(
                relationship.source, f"{context}.source"
            )
            target = _require_concept_id(
                relationship.target, f"{context}.target"
            )
            if source != owner_id:
                raise ValueError(
                    f"{context}.source does not equal its containing Node ID"
                )
            if source not in node_ids:
                raise ValueError(f"{context}.source does not identify a Node")

            properties = _require_export_property_map(
                relationship.properties, f"{context}.properties"
            )
            property_type = properties.get("type")
            derived_type = (
                property_type
                if isinstance(property_type, str) and property_type
                else None
            )
            retained_type = _require_optional_type(
                relationship.type, f"{context}.type"
            )
            if retained_type != derived_type:
                raise ValueError(
                    f"{context}.type does not equal the Type derived from Properties"
                )

            semantic_key = _require_nonempty_string(
                relationship.key, f"{context}.relationshipKey"
            )
            if not RELATIONSHIP_KEY_RE.fullmatch(semantic_key):
                raise ValueError(f"{context}.relationshipKey has an invalid v1 shape")
            try:
                expected_key = relationship_key(source, target, properties)
            except CanonicalizationError as exc:
                raise ValueError(
                    f"{context}.properties cannot be canonically encoded"
                ) from exc
            if semantic_key != expected_key:
                raise ValueError(
                    f"{context}.relationshipKey fails semantic verification"
                )
            key_preimage = (source, target, canonical_json(properties))
            previous_key_preimage = key_preimages.setdefault(
                semantic_key, key_preimage
            )
            if previous_key_preimage != key_preimage:
                raise ValueError(
                    f"{context}.relationshipKey collides with a different preimage"
                )

            occurrence = relationship.occurrence
            if (
                isinstance(occurrence, bool)
                or not isinstance(occurrence, int)
                or occurrence < 0
            ):
                raise ValueError(
                    f"{context}.occurrence must be a non-negative integer"
                )
            occurrence_group = (source, semantic_key)
            if occurrence in ordinals[occurrence_group]:
                raise ValueError(f"duplicate occurrence ordinal in {context}")
            ordinals[occurrence_group].add(occurrence)

            occurrence_id = _require_nonempty_string(
                relationship.id, f"{context}.id"
            )
            if not RELATIONSHIP_ID_RE.fullmatch(occurrence_id):
                raise ValueError(f"{context}.id has an invalid v1 shape")
            if occurrence_id != relationship_id(semantic_key, occurrence):
                raise ValueError(f"{context}.id fails occurrence verification")
            id_semantic = (key_preimage, occurrence)
            previous_id_semantic = relationship_ids.get(occurrence_id)
            if previous_id_semantic is not None:
                if previous_id_semantic != id_semantic:
                    raise ValueError(
                        f"{context}.id collides with different occurrence semantics"
                    )
                raise ValueError(f"duplicate Relationship ID: {occurrence_id!r}")
            relationship_ids[occurrence_id] = id_semantic

            _require_string(relationship.link_text, f"{context}.linkText")
            if relationship.title is not None:
                _require_string(relationship.title, f"{context}.title")

    for (source, semantic_key), observed in ordinals.items():
        if observed != set(range(len(observed))):
            raise ValueError(
                "Relationship occurrence ordinals must be contiguous from zero "
                f"for source {source!r} and key {semantic_key!r}"
            )


def _require_export_property_map(value: Any, context: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a string-keyed Property map")
    for key in value:
        _require_string(key, f"{context} key")
    try:
        canonical_document(value)
    except CanonicalizationError as exc:
        raise ValueError(f"{context} cannot be canonically encoded") from exc
    return value


def _sorted_relationships(graph: Graph) -> List[Relationship]:
    return sorted(
        graph.relationships,
        key=lambda relationship: (
            relationship.source,
            relationship.target,
            relationship.key,
            relationship.occurrence,
            relationship.id,
        ),
    )


def _is_okf_reserved_file(path: Path) -> bool:
    return path.name in {"index.md", "log.md"}


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


def _cypher_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _print_diagnostics(graph: Graph) -> None:
    for diagnostic in graph.diagnostics:
        print(
            f"{diagnostic.severity} [{diagnostic.code}]: {diagnostic.display()}",
            file=sys.stderr,
        )


def main(argv: Optional[List[str]] = None) -> int:
    cli = argparse.ArgumentParser(
        prog="pgmark",
        description="Process Property Graph Markdown 0.4.0 Public Draft bundles.",
    )
    cli.add_argument(
        "--version",
        action="version",
        version=f"{PROCESSOR_NAME} {PROCESSOR_VERSION} (PGM {PGM_VERSION_LABEL})",
    )
    subcommands = cli.add_subparsers(dest="command", required=True)

    validate_cmd = subcommands.add_parser(
        "validate", help="validate an OKF/PGM Core Bundle"
    )
    validate_cmd.add_argument("path", help="Markdown file or Knowledge Bundle root")
    validate_cmd.add_argument(
        "--json", action="store_true", help="emit the machine-readable graph report"
    )

    parse_cmd = subcommands.add_parser(
        "parse", help="parse and optionally serialize a PGM Core Result"
    )
    parse_cmd.add_argument("path", help="Markdown file or Knowledge Bundle root")
    parse_cmd.add_argument(
        "--format",
        choices=["summary", "json", "cypher"],
        default="summary",
        help="output format (default: summary)",
    )
    parse_cmd.add_argument(
        "--cypher",
        action="store_true",
        help="deprecated alias for --format cypher",
    )
    parse_cmd.add_argument(
        "--relationship-mode",
        choices=["create", "merge"],
        default="create",
        help="Cypher CREATE snapshot or idempotent MERGE by occurrence ID",
    )
    import_cmd = subcommands.add_parser(
        "import-json", help="validate and import PGM JSON Exchange Profile v1"
    )
    import_cmd.add_argument("path", help="JSON file, or - for standard input")
    import_cmd.add_argument(
        "--format",
        choices=["summary", "json", "cypher"],
        default="summary",
        help="output after import (default: summary)",
    )
    import_cmd.add_argument(
        "--relationship-mode",
        choices=["create", "merge"],
        default="create",
        help="Cypher CREATE snapshot or idempotent MERGE by occurrence ID",
    )

    args = cli.parse_args(argv)
    if args.command == "import-json":
        try:
            source = (
                sys.stdin.read()
                if args.path == "-"
                else Path(args.path).read_text(encoding="utf-8")
            )
        except UnicodeError as exc:
            print(f"import error [PGM_JSON_IMPORT_ERROR]: {exc}", file=sys.stderr)
            return 1
        except OSError as exc:
            print(f"input error [PGM_INPUT_READ_FAILED]: {exc}", file=sys.stderr)
            return 2
        try:
            graph = graph_from_json(source)
        except (UnicodeError, ValueError) as exc:
            print(f"import error [PGM_JSON_IMPORT_ERROR]: {exc}", file=sys.stderr)
            return 1
        _print_diagnostics(graph)
        if args.format == "summary":
            print(
                f"{len(graph.nodes)} nodes, {len(graph.relationships)} relationships, "
                f"{len(graph.warnings)} warnings"
            )
        elif args.format == "json":
            print(graph_to_json(graph), end="")
        else:
            print(
                graph_to_cypher(graph, relationship_mode=args.relationship_mode)
            )
        return 0

    graph = parse_corpus(args.path)
    _print_diagnostics(graph)
    input_failed = any(
        diagnostic.severity == "error"
        and diagnostic.code.startswith("PGM_INPUT_")
        for diagnostic in graph.diagnostics
    )

    if args.command == "validate":
        if args.json and not graph.errors:
            print(graph_to_json(graph), end="")
        elif not graph.errors:
            print(
                f"PGM Core Bundle conforms to {PGM_VERSION_LABEL}: "
                f"{len(graph.nodes)} nodes, {len(graph.relationships)} relationships, "
                f"{len(graph.warnings)} warnings"
            )
        if input_failed:
            return 2
        return 1 if graph.errors else 0

    if graph.errors:
        return 2 if input_failed else 1

    output_format = "cypher" if args.cypher else args.format
    if args.cypher and args.format != "summary":
        cli.error("--cypher cannot be combined with --format")
    try:
        if output_format == "summary":
            print(
                f"{len(graph.nodes)} nodes, {len(graph.relationships)} relationships, "
                f"{len(graph.warnings)} warnings"
            )
        elif output_format == "json":
            print(graph_to_json(graph), end="")
        elif output_format == "cypher":
            print(
                graph_to_cypher(graph, relationship_mode=args.relationship_mode)
            )
    except ValueError as exc:
        print(f"adapter error [PGM_ADAPTER_ERROR]: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
