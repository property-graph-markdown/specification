"""Local validation adapter for the pinned OKF and PGM YAML profiles.

The pinned OKF specification is the normative authority.  This module keeps
the reference implementation small and auditable; it does not import an OKF
agent runtime or vendor an upstream validator.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from jsonschema import Draft202012Validator  # type: ignore
from markdown_it import MarkdownIt  # type: ignore
from ruamel.yaml import YAML  # type: ignore
from ruamel.yaml.error import YAMLError  # type: ignore
from ruamel.yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode  # type: ignore

from canonical import (
    CanonicalizationError,
    DuplicateCanonicalKeyError,
    FrozenCanonicalSet,
    FrozenMapping,
    canonical_value,
    jcs_bytes,
)


OKF_VERSION = "0.2"
OKF_REPOSITORY = "GoogleCloudPlatform/knowledge-catalog"
OKF_COMMIT = "3fcbb9f828c2f23d109c855ee403c3a4c81f3a96"
OKF_SPEC_PATH = "okf/SPEC.md"
OKF_SPEC_SHA256 = "5a3311d270bebb16d558010e75064f5b75323f284992641732b1c8097511f948"
OKF_SPEC_URL = (
    "https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/"
    f"{OKF_COMMIT}/{OKF_SPEC_PATH}"
)

YAML_VERSION = "1.2.2"
YAML_SCHEMA = "Core Schema"
SUPPORTED_YAML_TAGS = frozenset(
    {
        "tag:yaml.org,2002:null",
        "tag:yaml.org,2002:bool",
        "tag:yaml.org,2002:int",
        "tag:yaml.org,2002:float",
        "tag:yaml.org,2002:str",
        "tag:yaml.org,2002:seq",
        "tag:yaml.org,2002:map",
        "tag:yaml.org,2002:binary",
        "tag:yaml.org,2002:timestamp",
        "tag:yaml.org,2002:set",
    }
)

FRONTMATTER_RE = re.compile(
    r"\A(?:\ufeff)?---[ \t]*(?:\r\n|\n|\r)"
    r"(?P<yaml>.*?)(?:\r\n|\n|\r)"
    r"---[ \t]*(?:(?:\r\n|\n|\r)|\Z)",
    re.DOTALL,
)
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIMESTAMP_FRACTION_RE = re.compile(
    r"(?:[Tt]|[ \t]+)\d{1,2}:\d{2}:\d{2}\.(?P<fraction>\d+)"
)
YAML_SEPARATION_CHARACTERS = " \t\r\n"

OKF_CONCEPT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["type"],
    "properties": {
        "type": {"type": "string", "minLength": 1},
    },
    "additionalProperties": True,
}

PGM_RELATIONSHIP_PROPERTIES_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "type": {"type": "string", "minLength": 1},
    },
    "additionalProperties": True,
}

ROOT_INDEX_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {"okf_version": {"const": OKF_VERSION}},
    "required": ["okf_version"],
    "additionalProperties": False,
}

_OKF_CONCEPT_VALIDATOR = Draft202012Validator(OKF_CONCEPT_SCHEMA)
_RELATIONSHIP_VALIDATOR = Draft202012Validator(
    PGM_RELATIONSHIP_PROPERTIES_SCHEMA
)
_ROOT_INDEX_VALIDATOR = Draft202012Validator(ROOT_INDEX_SCHEMA)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


class PGMValidationError(ValueError):
    """A stable machine code paired with a human-readable validation error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ParsedOKFConcept:
    metadata: Dict[str, Any]
    body: str


def _safe_yaml() -> YAML:
    """Return a safe YAML 1.2 Core-Schema parser.

    ruamel.yaml deliberately retains the legacy implicit timestamp resolver in
    its safe YAML 1.2 mode.  YAML 1.2.2 Core Schema does not resolve timestamps
    implicitly, so the reference adapter removes that resolver while retaining
    support for an explicitly written ``!!timestamp`` tag.
    """

    parser = YAML(typ="safe", pure=True)
    parser.version = (1, 2)
    parser.allow_duplicate_keys = False
    resolvers = parser.resolver.versioned_resolver
    for first_character, entries in list(resolvers.items()):
        resolvers[first_character] = [
            entry
            for entry in entries
            if entry[0] != "tag:yaml.org,2002:timestamp"
        ]
    return parser


def _validate_yaml_node(node: Node, active: set[int]) -> None:
    object_id = id(node)
    if object_id in active:
        raise PGMValidationError(
            "PGM_YAML_CYCLE", "cyclic YAML aliases are not PGM Property values"
        )
    if node.tag not in SUPPORTED_YAML_TAGS:
        raise PGMValidationError(
            "PGM_YAML_TAG_UNSUPPORTED", f"unsupported YAML tag: {node.tag}"
        )

    active.add(object_id)
    try:
        value = getattr(node, "value", None)
        if isinstance(node, MappingNode):
            for key, item in value:
                _validate_yaml_node(key, active)
                _validate_yaml_node(item, active)
        elif isinstance(value, list):
            for item in value:
                _validate_yaml_node(item, active)
    finally:
        active.remove(object_id)


def parse_yaml_1_2(source: str, *, require_flow_mapping: bool = False) -> Any:
    """Parse one safe YAML 1.2.2 Core-Schema document.

    The representation graph is inspected before construction so unsupported
    tags and alias cycles receive deterministic PGM diagnostics.
    """

    parser = _safe_yaml()
    try:
        node = parser.compose(source)
    except YAMLError as exc:
        raise PGMValidationError("PGM_YAML_INVALID", "invalid YAML 1.2.2") from exc
    if node is None:
        return None
    _validate_yaml_node(node, set())
    if require_flow_mapping and (
        not isinstance(node, MappingNode) or node.flow_style is not True
    ):
        raise PGMValidationError(
            "PGM_RELATIONSHIP_PROPERTIES_NOT_FLOW_MAPPING",
            "Relationship Properties must be one YAML Flow Mapping",
        )

    try:
        loaded = _construct_yaml_node(node, parser.constructor, set(), False)
        # Verify the complete constructed value now, not only when an optional
        # exporter happens to run. This turns unsupported timestamp ranges or
        # canonical key collisions into contextual Core/title diagnostics.
        canonical_value(loaded)
        return loaded
    except PGMValidationError:
        raise
    except CanonicalizationError as exc:
        raise PGMValidationError("PGM_YAML_VALUE_UNSUPPORTED", str(exc)) from exc
    except (TypeError, ValueError, YAMLError) as exc:
        raise PGMValidationError("PGM_YAML_INVALID", "invalid YAML 1.2.2") from exc


def _construct_yaml_node(
    node: Node,
    constructor: Any,
    active: set[int],
    key_context: bool,
) -> Any:
    """Construct the supported YAML representation without Python key loss.

    The stock safe constructor necessarily uses ``dict`` and ``set``. Those
    containers cannot represent every YAML Mapping key or Set member and
    conflate PGM-distinct values such as ``true`` and ``1``. Construction from
    the already tag-checked representation graph lets the reference processor
    retain the full portable value while still reusing ruamel.yaml's scalar
    constructors.
    """

    object_id = id(node)
    if object_id in active:
        raise PGMValidationError(
            "PGM_YAML_CYCLE", "cyclic YAML aliases are not PGM Property values"
        )
    active.add(object_id)
    try:
        if isinstance(node, ScalarNode):
            scalar_constructors = {
                "tag:yaml.org,2002:null": constructor.construct_yaml_null,
                "tag:yaml.org,2002:bool": constructor.construct_yaml_bool,
                "tag:yaml.org,2002:int": constructor.construct_yaml_int,
                "tag:yaml.org,2002:float": constructor.construct_yaml_float,
                "tag:yaml.org,2002:str": constructor.construct_yaml_str,
                "tag:yaml.org,2002:binary": constructor.construct_yaml_binary,
                "tag:yaml.org,2002:timestamp": constructor.construct_yaml_timestamp,
            }
            scalar_constructor = scalar_constructors.get(node.tag)
            if scalar_constructor is None:
                raise PGMValidationError(
                    "PGM_YAML_INVALID",
                    f"YAML tag {node.tag} is not valid on a scalar node",
                )
            if node.tag == "tag:yaml.org,2002:timestamp":
                fraction = TIMESTAMP_FRACTION_RE.search(node.value)
                if fraction is not None and len(fraction.group("fraction")) > 6:
                    raise PGMValidationError(
                        "PGM_YAML_VALUE_UNSUPPORTED",
                        "timestamp has more than six fractional-second digits",
                    )
            return scalar_constructor(node)

        if isinstance(node, SequenceNode):
            if node.tag != "tag:yaml.org,2002:seq":
                raise PGMValidationError(
                    "PGM_YAML_INVALID",
                    f"YAML tag {node.tag} is not valid on a sequence node",
                )
            items = [
                _construct_yaml_node(item, constructor, active, key_context)
                for item in node.value
            ]
            return tuple(items) if key_context else items

        if isinstance(node, MappingNode):
            if node.tag == "tag:yaml.org,2002:set":
                items = []
                for key_node, value_node in node.value:
                    item = _construct_yaml_node(
                        key_node, constructor, active, True
                    )
                    marker = _construct_yaml_node(
                        value_node, constructor, active, False
                    )
                    if marker is not None:
                        raise PGMValidationError(
                            "PGM_YAML_INVALID",
                            "YAML Set entries must have null values",
                        )
                    items.append(item)
                try:
                    canonical_set = FrozenCanonicalSet(items)
                except DuplicateCanonicalKeyError as exc:
                    raise PGMValidationError(
                        "PGM_YAML_INVALID",
                        "duplicate YAML Set member under PGM value identity",
                    ) from exc
                native_set = frozenset(items) if key_context else set(items)
                if len(native_set) == len(canonical_set):
                    return native_set
                return canonical_set
            if node.tag != "tag:yaml.org,2002:map":
                raise PGMValidationError(
                    "PGM_YAML_INVALID",
                    f"YAML tag {node.tag} is not valid on a mapping node",
                )

            entries = []
            encoded_keys: set[bytes] = set()
            for key_node, value_node in node.value:
                key = _construct_yaml_node(
                    key_node, constructor, active, True
                )
                value = _construct_yaml_node(
                    value_node, constructor, active, False
                )
                encoded_key = jcs_bytes(canonical_value(key))
                if encoded_key in encoded_keys:
                    raise PGMValidationError(
                        "PGM_YAML_INVALID",
                        "duplicate YAML Mapping key under canonical PGM value identity",
                    )
                encoded_keys.add(encoded_key)
                entries.append((key, value))

            if key_context or any(not isinstance(key, str) for key, _ in entries):
                return FrozenMapping(entries)
            return {key: value for key, value in entries}

        raise PGMValidationError(
            "PGM_YAML_INVALID", f"unsupported YAML node kind: {type(node).__name__}"
        )
    finally:
        active.remove(object_id)


def _require_string_keys(mapping: Mapping[Any, Any], *, context: str) -> None:
    if any(not isinstance(key, str) for key in mapping):
        raise PGMValidationError(
            "PGM_PROPERTY_KEY_NOT_STRING", f"{context} keys must be strings"
        )


def parse_okf_concept(markdown: str) -> ParsedOKFConcept:
    """Apply the OKF Concept checks plus the PGM YAML profile."""

    match = FRONTMATTER_RE.match(markdown)
    if not match:
        raise PGMValidationError(
            "OKF_FRONTMATTER_MISSING", "missing leading OKF YAML frontmatter"
        )

    try:
        loaded = parse_yaml_1_2(match.group("yaml"))
    except PGMValidationError as exc:
        raise PGMValidationError(
            exc.code, f"invalid OKF YAML frontmatter ({exc})"
        ) from exc
    if not isinstance(loaded, Mapping):
        raise PGMValidationError(
            "OKF_FRONTMATTER_NOT_MAPPING",
            "OKF YAML frontmatter must be a mapping",
        )

    _require_string_keys(loaded, context="Concept frontmatter")
    metadata = dict(loaded)
    errors = sorted(_OKF_CONCEPT_VALIDATOR.iter_errors(metadata), key=str)
    if errors:
        raise PGMValidationError(
            "OKF_TYPE_REQUIRED",
            "OKF YAML frontmatter requires a non-empty string 'type'",
        )
    return ParsedOKFConcept(metadata=metadata, body=markdown[match.end() :])


def parse_pgm_relationship_properties(
    source: str,
) -> Tuple[Dict[str, Any], Optional[ValidationIssue]]:
    """Parse a complete PGM YAML Flow Mapping title."""

    stripped = source.strip(YAML_SEPARATION_CHARACTERS)
    if not stripped.startswith("{") or not stripped.endswith("}"):
        raise PGMValidationError(
            "PGM_RELATIONSHIP_PROPERTIES_NOT_FLOW_MAPPING",
            "property map must begin with '{' and end with '}'",
        )
    try:
        loaded = parse_yaml_1_2(stripped, require_flow_mapping=True)
    except PGMValidationError:
        raise
    if not isinstance(loaded, Mapping):
        raise PGMValidationError(
            "PGM_RELATIONSHIP_PROPERTIES_NOT_MAPPING",
            "property map must be a mapping",
        )

    _require_string_keys(loaded, context="Relationship Property map")
    properties = dict(loaded)
    errors = sorted(_RELATIONSHIP_VALIDATOR.iter_errors(properties), key=str)
    diagnostic = None
    if errors:
        diagnostic = ValidationIssue(
            "PGM_RELATIONSHIP_TYPE_INVALID",
            "Relationship Property 'type' is not a non-empty string; "
            "Relationship remains untyped",
        )
    return properties, diagnostic


def validate_reserved_document(
    relative_path: str, markdown: str
) -> List[ValidationIssue]:
    """Apply the normative OKF rules for a present index.md or log.md."""

    path = PurePosixPath(relative_path)
    if path.name not in {"index.md", "log.md"}:
        return []

    match = FRONTMATTER_RE.match(markdown)
    if path.name == "index.md":
        if match is not None:
            if len(path.parts) != 1:
                return [
                    ValidationIssue(
                        "OKF_INDEX_FRONTMATTER_NOT_ROOT",
                        "only the bundle-root index.md may contain frontmatter",
                    )
                ]
            try:
                loaded = parse_yaml_1_2(match.group("yaml"))
            except PGMValidationError:
                return [
                    ValidationIssue(
                        "OKF_INDEX_FRONTMATTER_INVALID",
                        "bundle-root index.md has invalid YAML frontmatter",
                    )
                ]
            errors = list(_ROOT_INDEX_VALIDATOR.iter_errors(loaded))
            if errors:
                return [
                    ValidationIssue(
                        "OKF_INDEX_FRONTMATTER_INVALID",
                        "bundle-root index.md frontmatter must contain only "
                        "okf_version: '0.2'",
                    )
                ]

        body = markdown[match.end() :] if match is not None else markdown
        tokens = MarkdownIt("commonmark").parse(body)
        if not any(token.type == "heading_open" for token in tokens):
            return [
                ValidationIssue(
                    "OKF_INDEX_SECTION_REQUIRED",
                    "index.md requires one or more sections under headings",
                )
            ]
        return []

    if match is not None:
        return [
            ValidationIssue(
                "OKF_LOG_FRONTMATTER_FORBIDDEN",
                "log.md must not contain YAML frontmatter",
            )
        ]

    tokens = MarkdownIt("commonmark").parse(markdown)
    headings = _level_two_headings(tokens, markdown)
    if markdown.strip(YAML_SEPARATION_CHARACTERS) and not headings:
        return [
            ValidationIssue(
                "OKF_LOG_DATE_HEADING_REQUIRED",
                "log.md requires ISO 8601 level-two date headings",
            )
        ]
    parsed_dates: List[date] = []
    for heading in headings:
        if not ISO_DATE_RE.fullmatch(heading):
            return [
                ValidationIssue(
                    "OKF_LOG_DATE_HEADING_INVALID",
                    f"log.md date heading must use YYYY-MM-DD: {heading!r}",
                )
            ]
        try:
            parsed_dates.append(date.fromisoformat(heading))
        except ValueError:
            return [
                ValidationIssue(
                    "OKF_LOG_DATE_INVALID",
                    f"log.md contains an invalid calendar date: {heading!r}",
                )
            ]
    if parsed_dates != sorted(parsed_dates, reverse=True):
        return [
            ValidationIssue(
                "OKF_LOG_ORDER_INVALID",
                "log.md date headings must be newest first",
            )
        ]
    return []


def _level_two_headings(tokens: List[Any], markdown: str) -> List[str]:
    source_lines = re.split(r"\r\n|\n|\r", markdown)
    headings: List[str] = []
    for index, token in enumerate(tokens[:-1]):
        if token.type == "heading_open" and token.tag == "h2":
            inline = tokens[index + 1]
            if inline.type == "inline":
                source_line = ""
                if token.map and token.map[0] < len(source_lines):
                    source_line = source_lines[token.map[0]]
                if any(
                    character.isspace() and character not in " \t"
                    for character in source_line
                ):
                    headings.append("\0invalid-non-ascii-whitespace")
                else:
                    headings.append(inline.content)
    return headings
