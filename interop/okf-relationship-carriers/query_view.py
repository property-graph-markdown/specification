"""Fixture-only preview of proposed OKF #22 query behavior.

This is not a general #22 implementation: the registration is still open,
and source eligibility, conflicting log dispositions, and cross-bundle IDs
remain outside this exercise. A relationship property is never an affirmation.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "parser"))

from pgmark import Graph, parse_corpus  # noqa: E402


# The Remember producer's pinned manifest explicitly declares this form.
# It is NOT a general OKF/PGM rule for converting bare IDs to stable IDs.
REMEMBER_ID_FORM = "remember://lesson/<id>"
SUPERSESSION_ENTRY = re.compile(
    r"\* \*\*Supersession\*\*: `(?P<source>[^`]+)` supersedes "
    r"`(?P<target>[^`]+)`\. Affirmed by `(?P<actor>[^`]+)`\."
)
ACTOR = re.compile(
    r"(?:human|process):[A-Za-z0-9][A-Za-z0-9._-]*"
    r"|[A-Za-z0-9._-]+/[A-Za-z0-9._-]+"
)


def _remember_stable_id(bare_id: str) -> str:
    """Apply only Remember's documented `remember://lesson/<id>` form."""

    if not bare_id or any(char in bare_id for char in "/:` \t\n"):
        raise ValueError("Remember fixture expects a nonempty bare lesson ID")
    return REMEMBER_ID_FORM.replace("<id>", bare_id)


def _root_supersessions(bundle: Path) -> list[dict[str, str]]:
    """Read exact, dated, attributed supersession entries in the root log.

    This deliberately recognizes only the entry shape exercised by these
    fixtures, not every possible #22 resolution or conflict ordering.
    """

    log = bundle / "log.md"
    if not log.is_file():
        return []
    entries: list[dict[str, str]] = []
    entry_date: str | None = None
    for line in log.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            candidate = line[3:]
            try:
                entry_date = candidate if date.fromisoformat(candidate).isoformat() == candidate else None
            except ValueError:
                entry_date = None
            continue
        match = SUPERSESSION_ENTRY.fullmatch(line)
        if entry_date is None or match is None:
            continue
        actor = match.group("actor")
        if ACTOR.fullmatch(actor) is None:
            continue
        entries.append({"date": entry_date, **match.groupdict()})
    return entries


def _affirming_actors(
    entries: list[dict[str, str]], source_id: str, target_id: str
) -> list[str]:
    """Join only on the exact ordered stable-ID pair, never any log marker."""

    return sorted({
        entry["actor"]
        for entry in entries
        if entry["source"] == source_id and entry["target"] == target_id
    })


def _remember_view(bundle: Path) -> dict[str, Any]:
    graph = parse_corpus(bundle)
    if graph.errors or len(graph.nodes) != 1:
        raise ValueError("Remember extract must contain exactly one parseable concept")
    node = next(iter(graph.nodes.values()))
    source_bare_id = node.properties["id"]
    source_id = _remember_stable_id(source_bare_id)
    # The extract includes one concept, but this lookup still makes missing or
    # ambiguous stable IDs fail closed rather than treating a path as identity.
    id_counts = Counter(
        _remember_stable_id(concept.properties["id"])
        for concept in graph.nodes.values()
        if isinstance(concept.properties.get("id"), str)
    )
    resolutions = _root_supersessions(bundle)
    references: list[dict[str, Any]] = []
    for field, typ in (
        ("supersedes", "supersedes"),
        ("contradicts", "contradicts"),
        ("contested_by", "contradicts"),
    ):
        if field not in node.properties:
            continue
        value = node.properties[field]
        for target in value if isinstance(value, list) else [value]:
            target_id = _remember_stable_id(target)
            target_present = id_counts[target_id] == 1
            actors = (
                _affirming_actors(resolutions, source_id, target_id)
                if typ == "supersedes" else []
            )
            if typ == "supersedes":
                query_result = (
                    "affirmed-but-unresolved-target-no-exclusion"
                    if actors and not target_present else
                    "unaffirmed-and-unresolved-no-exclusion"
                    if not target_present else
                    "affirmed-pair-candidate-subject-to-source-eligibility"
                    if actors else "proposal-without-affirmation"
                )
            else:
                query_result = (
                    "unresolved-contradiction-no-reverse-view"
                    if not target_present else "open-contest"
                )
            references.append({
                "storedField": field,
                "interpretedType": typ,
                "sourceId": source_bare_id,
                "targetId": target,
                "sourceStableId": source_id,
                "targetStableId": target_id,
                "targetPresent": target_present,
                "affirmedBy": actors,
                # No case in either copied extract has a present target.
                "excludeTargetFromInForce": False,
                "queryResult": query_result,
            })
    return {
        "sourceHasPgmLinkOccurrences": bool(graph.relationships),
        "readableRootSupersessions": resolutions,
        "references": references,
    }


def _unique_stable_id_by_path(graph: Graph) -> dict[str, str]:
    """Resolve an in-bundle path only when its document ID is nonambiguous."""

    ids = {
        node.id: value
        for node in graph.nodes.values()
        if isinstance(value := node.properties.get("id"), str) and value
    }
    counts = Counter(ids.values())
    return {path: stable_id for path, stable_id in ids.items() if counts[stable_id] == 1}


def _pgm_view(graph: Graph, bundle: Path) -> dict[str, Any]:
    stable_id_by_path = _unique_stable_id_by_path(graph)
    resolutions = _root_supersessions(bundle)
    rows: list[dict[str, Any]] = []
    pairs: dict[tuple[str, str, str], dict[str, Any]] = {}
    for edge in graph.relationships:
        if edge.type not in ("supersedes", "contradicts"):
            continue
        source_id = stable_id_by_path.get(edge.source)
        target_id = stable_id_by_path.get(edge.target)
        actors = (
            _affirming_actors(resolutions, source_id, target_id)
            if edge.type == "supersedes" and source_id and target_id else []
        )
        if source_id is None or target_id is None:
            result: dict[str, Any] = {
                "state": "unresolved-reference",
                "excludeTargetFromInForce": False,
                "derivedReverse": None,
            }
            if edge.type == "contradicts":
                result["surfaceBoth"] = False
        elif edge.type == "supersedes":
            result = {
                "state": (
                    "affirmed-pair-candidate-subject-to-source-eligibility"
                    if actors else "proposal-without-affirmation"
                ),
                "affirmedBy": actors,
                "excludeTargetFromInForce": False,
                "derivedReverse": None,
            }
        else:
            result = {
                "state": "open-contest",
                "excludeTargetFromInForce": False,
                "surfaceBoth": True,
                "derivedReverse": {
                    "on": target_id,
                    "type": "contradicted_by",
                    "from": source_id,
                },
            }
        rows.append({
            "relationshipId": edge.id,
            "storedType": edge.type,
            "physicalSource": edge.source,
            "physicalTarget": edge.target,
            "sourceStableId": source_id,
            "targetStableId": target_id,
            **result,
        })
        if source_id is not None and target_id is not None:
            key = (edge.type, source_id, target_id)
            if key not in pairs:
                pairs[key] = {
                    "storedType": edge.type,
                    "sourceStableId": source_id,
                    "targetStableId": target_id,
                    "relationshipIds": [],
                    "state": result["state"],
                    "excludeTargetFromInForce": result["excludeTargetFromInForce"],
                }
            pairs[key]["relationshipIds"].append(edge.id)
    return {
        "readableRootSupersessions": resolutions,
        "references": rows,
        "pairDecisions": list(pairs.values()),
    }


def view() -> dict[str, Any]:
    """Return explicit candidate query outcomes for the fixture's authoring modes."""

    synthetic_root = FIXTURE / "pgm-synthetic-lifecycle" / "bundle"
    synthetic = parse_corpus(synthetic_root)
    if synthetic.errors:
        raise ValueError("synthetic fixture must parse without PGM Core errors")
    return {
        "format": "informative-okf22-query-preview",
        "registrationStatus": "open-proposal-not-normative-okf-or-pgm-core",
        "rememberFrontmatterNative": _remember_view(
            FIXTURE / "frontmatter-native-remember" / "bundle"
        ),
        "rememberFrontmatterNativeCurrent": _remember_view(
            FIXTURE / "frontmatter-native-remember-current" / "bundle"
        ),
        "syntheticPgmLinkNative": _pgm_view(synthetic, synthetic_root),
    }


if __name__ == "__main__":
    print(json.dumps(view(), ensure_ascii=False, indent=2, sort_keys=True))
