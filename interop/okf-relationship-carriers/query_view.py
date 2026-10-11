"""Fixture-only preview of proposed OKF #22 query behavior.

This is deliberately not a general #22 implementation: #22 remains an open
proposal, and source eligibility / full log conflict handling are out of
scope. The examples here have no readable affirmation, so none excludes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "parser"))

from pgmark import parse_corpus  # noqa: E402


def _root_log_has_resolution(bundle: Path) -> bool:
    log = bundle / "log.md"
    if not log.is_file():
        return False
    text = log.read_text(encoding="utf-8")
    return "**Supersession**:" in text or "**Dismissal**:" in text


def view() -> dict[str, Any]:
    """Return explicit candidate query outcomes for the two fixture modes."""

    remember_root = FIXTURE / "frontmatter-native-remember" / "bundle"
    remember = parse_corpus(remember_root)
    synthetic_root = FIXTURE / "pgm-synthetic-lifecycle" / "bundle"
    synthetic = parse_corpus(synthetic_root)
    if remember.errors or synthetic.errors:
        raise ValueError("fixtures must parse without PGM Core errors")

    remember_node = next(iter(remember.nodes.values()))
    known_remember_ids = {
        node.properties["id"]
        for node in remember.nodes.values()
        if isinstance(node.properties.get("id"), str)
    }
    native_edges: list[dict[str, Any]] = []
    for field, typ in (("supersedes", "supersedes"), ("contested_by", "contradicts")):
        value = remember_node.properties[field]
        targets = value if isinstance(value, list) else [value]
        for target in targets:
            native_edges.append(
                {
                    "storedField": field,
                    "interpretedType": typ,
                    "sourceId": remember_node.properties["id"],
                    "targetId": target,
                    "targetPresent": target in known_remember_ids,
                    "queryResult": "unresolved-reference-no-exclusion-or-reverse-view",
                }
            )

    stable_id_by_path = {
        node.id: node.properties["id"]
        for node in synthetic.nodes.values()
        if isinstance(node.properties.get("id"), str)
    }
    pgm_edges: list[dict[str, Any]] = []
    for edge in synthetic.relationships:
        if edge.type not in ("supersedes", "contradicts"):
            continue
        source_id = stable_id_by_path.get(edge.source)
        target_id = stable_id_by_path.get(edge.target)
        if source_id is None:
            raise ValueError("synthetic asserting concept needs an explicit stable id")
        if edge.type == "supersedes":
            result = {
                "state": "proposal-without-affirmation" if target_id else "unresolved-reference",
                "excludeTargetFromInForce": False,
                "derivedReverse": None,
            }
        else:
            result = {
                "state": "open-contest" if target_id else "unresolved-reference",
                "excludeTargetFromInForce": False,
                "surfaceBoth": bool(target_id),
                "derivedReverse": (
                    {"on": target_id, "type": "contradicted_by", "from": source_id}
                    if target_id
                    else None
                ),
            }
        pgm_edges.append(
            {
                "relationshipId": edge.id,
                "storedType": edge.type,
                "physicalSource": edge.source,
                "physicalTarget": edge.target,
                "sourceStableId": source_id,
                "targetStableId": target_id,
                **result,
            }
        )

    return {
        "format": "informative-okf22-query-preview",
        "registrationStatus": "open-proposal-not-normative-okf-or-pgm-core",
        "rememberFrontmatterNative": {
            "sourceHasPgmLinkOccurrences": bool(remember.relationships),
            "rootLogHasResolutionMarkers": _root_log_has_resolution(remember_root),
            "references": native_edges,
        },
        "syntheticPgmLinkNative": {
            "rootLogHasResolutionMarkers": _root_log_has_resolution(synthetic_root),
            "references": pgm_edges,
        },
    }


if __name__ == "__main__":
    print(json.dumps(view(), ensure_ascii=False, indent=2, sort_keys=True))
