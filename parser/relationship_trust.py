"""Optional OKF-analog trust interpretation for PGM Relationship occurrences.

This module does not change PGM Core Properties, direction, or JSON exchange.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Mapping


PROFILE_NAME = "PGM OKF Relationship Trust Profile v1 Public Draft"

_ACTOR = re.compile(r"(?:human:[^\s:]+|process:[^\s:]+|[^\s/:]+/[^\s/]+)\Z")
_OFFSET_DATETIME = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}"
    r"(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})\Z"
)


class RelationshipTrustProfileError(ValueError):
    """The authored Relationship remains valid PGM Core, but not this profile."""


def _actor(value: Any, location: str) -> str:
    if not isinstance(value, str) or _ACTOR.fullmatch(value) is None:
        raise RelationshipTrustProfileError(
            f"{location}.by must use an OKF actor: producer/version, "
            "process:<id>, or human:<id>"
        )
    return value


def _timestamp(value: Any, location: str) -> None:
    if isinstance(value, datetime):
        if value.utcoffset() is not None:
            return
    elif isinstance(value, str) and _OFFSET_DATETIME.fullmatch(value):
        try:
            # Python 3.10 does not accept a trailing Z in fromisoformat().
            normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
            if datetime.fromisoformat(normalized).utcoffset() is not None:
                return
        except ValueError:
            pass
    raise RelationshipTrustProfileError(
        f"{location}.at must be an ISO 8601 datetime with an explicit offset"
    )


def _event(value: Any, location: str) -> str:
    if not isinstance(value, Mapping):
        raise RelationshipTrustProfileError(f"{location} must be a Mapping")
    actor = _actor(value.get("by"), location)
    _timestamp(value.get("at"), location)
    return actor


def relationship_trust_tier(properties: Mapping[str, Any]) -> str:
    """Derive one advisory tier from one occurrence's authored Properties.

    Raises RelationshipTrustProfileError for invalid present verification events;
    callers must not reinterpret such an error as an unverified tier.
    """

    if "verified" not in properties:
        return "unverified"

    raw = properties["verified"]
    if isinstance(raw, Mapping):
        events = [raw]
    elif isinstance(raw, list) and raw:
        events = raw
    else:
        raise RelationshipTrustProfileError(
            "verified must be one event Mapping or a non-empty Sequence of events"
        )

    actors = [_event(event, f"verified[{index}]") for index, event in enumerate(events)]
    if any(actor.startswith("human:") for actor in actors):
        return "human-reviewed"
    return "machine-confirmed"


def relationship_trust_report(graph: Any) -> dict[str, Any]:
    """Evaluate a Core Result without changing its Relationships or Properties."""

    relationships: list[dict[str, Any]] = []
    diagnostics: list[dict[str, str]] = []
    ordered = sorted(
        graph.relationships,
        key=lambda edge: (edge.source, edge.target, edge.key, edge.occurrence, edge.id),
    )
    for edge in ordered:
        item = {
            "relationshipId": edge.id,
            "source": edge.source,
            "target": edge.target,
            "trustTier": None,
        }
        try:
            item["trustTier"] = relationship_trust_tier(edge.properties)
        except RelationshipTrustProfileError as exc:
            diagnostics.append(
                {
                    "code": "PGM_RELATIONSHIP_TRUST_INVALID",
                    "relationshipId": edge.id,
                    "message": str(exc),
                }
            )
        relationships.append(item)
    return {
        "profile": PROFILE_NAME,
        "conforms": not diagnostics,
        "relationships": relationships,
        "diagnostics": diagnostics,
    }
