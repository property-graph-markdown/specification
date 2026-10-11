"""Informative, fixture-scoped PGM -> proposed OKF #16 list projection.

The PGM link occurrence remains authoritative. This does not implement an
accepted OKF carrier, stable concept IDs, or #22 query-time semantics.
"""

from __future__ import annotations

import argparse
import copy
import json
import posixpath
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "parser"))

from pgmark import Graph, parse_corpus  # noqa: E402


# Only fields in the currently proposed #16 list are copied. PGM properties
# outside that subset remain in the authoritative PGM graph, not in the list.
COMMON_FIELDS = ("direction", "generated", "verified")


def _relative_markdown_target(source: str, target: str) -> str:
    """Emit a candidate `to` path relative to its carrying Markdown file."""

    source_dir = posixpath.dirname(source) or "."
    return posixpath.relpath(f"{target}.md", start=source_dir)


def project(graph: Graph) -> dict[str, Any]:
    """Project typed link occurrences, retaining their source order and trace.

    Untyped links cannot satisfy the draft's required `type`. No invented type
    is supplied. A `direction` property is copied verbatim, never used to
    reverse the PGM Core edge. Paths are provisional #16 target references,
    not durable OKF concept IDs.
    """

    if graph.errors:
        raise ValueError("cannot project a graph with PGM Core errors")

    carriers: list[dict[str, Any]] = []
    mapping: list[dict[str, Any]] = []
    unprojected: list[dict[str, Any]] = []

    for source in sorted(graph.nodes):
        entries: list[dict[str, Any]] = []
        for edge in graph.nodes[source].relationships:
            if edge.type is None:
                unprojected.append(
                    {
                        "relationshipId": edge.id,
                        "source": edge.source,
                        "target": edge.target,
                        "reason": "untyped-link-cannot-satisfy-required-type",
                    }
                )
                continue

            entry: dict[str, Any] = {
                "to": _relative_markdown_target(edge.source, edge.target),
                "type": edge.type,
            }
            for field in COMMON_FIELDS:
                if field in edge.properties:
                    entry[field] = copy.deepcopy(edge.properties[field])

            # This narrow exercise uses JSON-compatible examples; fail visibly
            # rather than silently stringifying PGM's richer YAML value model.
            json.dumps(entry, allow_nan=False)
            index = len(entries)
            entries.append(entry)
            mapping.append(
                {
                    "relationshipId": edge.id,
                    "relationshipKey": edge.key,
                    "occurrence": edge.occurrence,
                    "source": edge.source,
                    "physicalTarget": edge.target,
                    "resolved": edge.target in graph.nodes,
                    "entryIndex": index,
                    "omittedProperties": sorted(
                        set(edge.properties) - {"type", *COMMON_FIELDS}
                    ),
                    "directionIsOnlyAnAuthoredProperty": "direction"
                    in edge.properties,
                }
            )
        if entries:
            carriers.append({"source": source, "relationships": entries})

    return {
        "format": "informative-pgm-to-okf16-projection",
        "version": 1,
        "targetReferenceKind": "relative-markdown-path-not-stable-concept-id",
        "carriers": carriers,
        "mapping": mapping,
        "unprojected": unprojected,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="PGM source bundle to project")
    args = parser.parse_args()
    graph = parse_corpus(args.bundle)
    if graph.errors:
        for error in graph.errors:
            print(error, file=sys.stderr)
        return 1
    print(json.dumps(project(graph), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
