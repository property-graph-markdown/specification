#!/usr/bin/env python3
"""Reference validator for prototype-based PGM Schema 0.4.0 Public Draft."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Set, Tuple


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "parser"))

from pgmark import Graph, PGM_VERSION_LABEL, parse_corpus  # noqa: E402
from validation import OKF_COMMIT, OKF_SPEC_SHA256  # noqa: E402


Signature = Tuple[str, Optional[str], str]
PGM_SCHEMA_VERSION = "0.4.0"
PGM_SCHEMA_STATUS = "Public Draft"
PGM_SCHEMA_VERSION_LABEL = f"{PGM_SCHEMA_VERSION} {PGM_SCHEMA_STATUS}"


@dataclass(frozen=True)
class SchemaDiagnostic:
    code: str
    message: str

    def render(self) -> str:
        return f"error [{self.code}]: {self.message}"


@dataclass(frozen=True)
class PrototypeSchema:
    types: FrozenSet[str]
    attributes: Dict[str, FrozenSet[str]]
    relationships: Dict[Signature, FrozenSet[str]]


def concept_documents(root: Path) -> Set[str]:
    return {
        path.relative_to(root).as_posix()[:-3]
        for path in root.rglob("*.md")
        if path.is_file()
        and not path.is_symlink()
        and path.name not in {"index.md", "log.md"}
    }


def relationship_type_name(value: Optional[str]) -> str:
    return value if value is not None else "<untyped>"


def graph_errors(graph: Graph, scope: str) -> List[SchemaDiagnostic]:
    """Return core conformance errors without promoting PGM warnings."""

    return [
        SchemaDiagnostic(diagnostic.code, f"{scope}: {diagnostic.display()}")
        for diagnostic in graph.diagnostics
        if diagnostic.severity == "error"
    ]


def load_schema(
    root: Path,
) -> Tuple[Optional[PrototypeSchema], List[SchemaDiagnostic]]:
    errors: List[SchemaDiagnostic] = []
    if not root.is_dir():
        return None, [
            SchemaDiagnostic(
                "PGMS_SCHEMA_ROOT_INVALID",
                f"schema bundle does not exist or is not a directory: {root}",
            )
        ]

    documents = concept_documents(root)
    if not documents:
        return None, [
            SchemaDiagnostic(
                "PGMS_SCHEMA_EMPTY",
                "schema bundle requires at least one Prototype concept",
            )
        ]

    graph = parse_corpus(root)
    errors.extend(graph_errors(graph, "schema"))

    types = set(documents)
    attributes: Dict[str, FrozenSet[str]] = {}
    relationships: Dict[Signature, FrozenSet[str]] = {}

    for document_id in sorted(documents):
        node = graph.nodes.get(document_id)
        type_name = document_id
        actual_type = node.type if node else None
        if actual_type != "Prototype":
            errors.append(
                SchemaDiagnostic(
                    "PGMS_PROTOTYPE_REQUIRED",
                    f"schema:{document_id}: expected frontmatter type Prototype, "
                    f"found {actual_type or '<missing>'}",
                )
            )
        attributes[type_name] = (
            frozenset(set(node.properties) - {"type"}) if node else frozenset()
        )

    for document_id in sorted(documents):
        node = graph.nodes.get(document_id)
        if node is None:
            continue
        source_type = document_id
        for relationship in node.relationships:
            if relationship.target not in documents:
                errors.append(
                    SchemaDiagnostic(
                        "PGMS_PROTOTYPE_TARGET_UNRESOLVED",
                        f"schema:{document_id}: prototype "
                        f"{relationship_type_name(relationship.type)} target "
                        f"{relationship.target} is not a Prototype concept in the schema bundle",
                    )
                )
                continue
            target_type = relationship.target
            signature = (source_type, relationship.type, target_type)
            if signature in relationships:
                errors.append(
                    SchemaDiagnostic(
                        "PGMS_DUPLICATE_SIGNATURE",
                        "schema: duplicate prototype signature "
                        f"{source_type} -[{relationship_type_name(relationship.type)}]-> "
                        f"{target_type}",
                    )
                )
                continue
            relationships[signature] = frozenset(
                set(relationship.properties) - {"type"}
            )

    if errors:
        return None, errors
    return PrototypeSchema(
        types=frozenset(types),
        attributes=attributes,
        relationships=relationships,
    ), []


def validate_instance(root: Path, schema: PrototypeSchema) -> List[SchemaDiagnostic]:
    if not root.is_dir():
        return [
            SchemaDiagnostic(
                "PGMS_INSTANCE_ROOT_INVALID",
                f"instance bundle does not exist or is not a directory: {root}",
            )
        ]

    errors: List[SchemaDiagnostic] = []
    documents = concept_documents(root)
    graph = parse_corpus(root)
    errors.extend(graph_errors(graph, "instance"))

    instance_types: Dict[str, Optional[str]] = {}
    for document_id in sorted(documents):
        node = graph.nodes.get(document_id)
        type_name = node.type if node else None
        instance_types[document_id] = type_name
        if type_name not in schema.types:
            errors.append(
                SchemaDiagnostic(
                    "PGMS_INSTANCE_TYPE_UNKNOWN",
                    f"instance:{document_id}: unknown Type {type_name or '<missing>'}",
                )
            )
            continue
        unexpected = sorted(
            set(node.properties) - {"type"} - set(schema.attributes[type_name])
        )
        for key in unexpected:
            errors.append(
                SchemaDiagnostic(
                    "PGMS_INSTANCE_ATTRIBUTE_UNDECLARED",
                    f"instance:{document_id}: attribute {key} is not declared by "
                    f"Type {type_name}",
                )
            )

    for document_id in sorted(documents):
        node = graph.nodes.get(document_id)
        if node is None:
            continue
        source_type = instance_types.get(document_id)
        for relationship in node.relationships:
            if relationship.target not in documents:
                errors.append(
                    SchemaDiagnostic(
                        "PGMS_INSTANCE_TARGET_OUT_OF_SCOPE",
                        f"instance:{document_id}: relationship "
                        f"{relationship_type_name(relationship.type)} target "
                        f"{relationship.target} is outside the validation scope",
                    )
                )
                continue
            target_type = instance_types.get(relationship.target)
            if source_type not in schema.types or target_type not in schema.types:
                continue
            signature = (source_type, relationship.type, target_type)
            permitted = schema.relationships.get(signature)
            if permitted is None:
                errors.append(
                    SchemaDiagnostic(
                        "PGMS_INSTANCE_SIGNATURE_UNDECLARED",
                        f"instance:{document_id}: relationship signature "
                        f"{source_type} -[{relationship_type_name(relationship.type)}]-> "
                        f"{target_type} "
                        "has no prototype",
                    )
                )
                continue
            for key in sorted(
                set(relationship.properties) - {"type"} - set(permitted)
            ):
                errors.append(
                    SchemaDiagnostic(
                        "PGMS_INSTANCE_PROPERTY_UNDECLARED",
                        f"instance:{document_id}: relationship property {key} is not "
                        f"declared by prototype {source_type} "
                        f"-[{relationship_type_name(relationship.type)}]-> {target_type}",
                    )
                )

    return errors


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a prototype-based PGM Schema 0.4.0 Public Draft bundle "
            "and optional instance bundle."
        )
    )
    parser.add_argument(
        "--version",
        action="version",
        version=(
            f"PGM Schema {PGM_SCHEMA_VERSION_LABEL}; PGM {PGM_VERSION_LABEL}; "
            f"OKF {OKF_COMMIT} ({OKF_SPEC_SHA256})"
        ),
    )
    parser.add_argument("schema", nargs="?", help="schema Knowledge Bundle root")
    parser.add_argument("instance", nargs="?", help="instance Knowledge Bundle root")
    args = parser.parse_args(argv)

    if args.schema is None:
        schema_root = HERE / "example-schema"
        instance_root: Optional[Path] = HERE / "example-graph"
    else:
        schema_root = Path(args.schema).resolve()
        instance_root = Path(args.instance).resolve() if args.instance else None

    schema, errors = load_schema(schema_root)
    if schema is not None and instance_root is not None:
        errors.extend(validate_instance(instance_root, schema))

    if errors:
        print(f"PGM Schema validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(error.render(), file=sys.stderr)
        return 1

    assert schema is not None
    print(f"PGM Schema {PGM_SCHEMA_VERSION_LABEL} prototype bundle is valid.")
    print(f"Types: {len(schema.types)}")
    print(
        "Prototype attributes: "
        f"{sum(len(keys) for keys in schema.attributes.values())}"
    )
    print(f"Prototype relationships: {len(schema.relationships)}")
    if instance_root is not None:
        print("Instance bundle conforms to the schema prototypes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
