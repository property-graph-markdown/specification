"""Informative PGM/OKF #16 carrier comparison, not an OKF conformance profile."""

import json
import posixpath
import sys
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "parser"))

from pgmark import graph_from_data, graph_to_data, parse_corpus  # noqa: E402
from relationship_trust import (  # noqa: E402
    RelationshipTrustProfileError,
    relationship_trust_tier,
)


FIXTURE = ROOT / "interop" / "okf-relationship-carriers"
sys.path.insert(0, str(FIXTURE))
from project_pgm import project  # noqa: E402
from query_view import view as query_view  # noqa: E402

CHECKOUT = "functions/checkout"
HANDLER = "functions/handler"


def has_explicit_offset(value):
    """Parse the fixture's UTC spelling on Python 3.10 as well as 3.11+."""

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized).utcoffset() is not None


def illustrative_view(source, target, properties):
    """Keep the physical Link assertion separate from declared direction."""

    direction = properties["direction"]
    if direction not in ("inbound", "outbound"):
        raise ValueError("this illustration supports inbound/outbound only")
    return {
        "physicalSource": source,
        "targetReference": target,
        "type": properties["type"],
        "declaredDirection": direction,
        "trustTier": relationship_trust_tier(properties),
    }


def proposed_frontmatter_target(carrier, entry):
    """Resolve only this fixture's simple file-relative `to` spelling."""

    path = posixpath.normpath(
        posixpath.join(posixpath.dirname(carrier), entry["to"])
    )
    if path.startswith("../") or path == ".." or not path.endswith(".md"):
        raise ValueError("this illustration expects an in-bundle .md path")
    return path[:-3]


class OkfRelationshipCarrierExercise(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pgm = parse_corpus(FIXTURE / "pgm-links")
        cls.frontmatter = parse_corpus(FIXTURE / "frontmatter-proposal")
        cls.synthetic = parse_corpus(FIXTURE / "pgm-synthetic-lifecycle" / "bundle")
        cls.expected = json.loads(
            (FIXTURE / "expected-relationship-views.json").read_text(
                encoding="utf-8"
            )
        )

    def test_both_bundles_pass_the_pgm_pinned_okf_baseline(self):
        self.assertEqual(self.pgm.errors, [])
        self.assertEqual(self.frontmatter.errors, [])
        self.assertEqual(self.pgm.warnings, [])
        self.assertEqual(self.frontmatter.warnings, [])

    def test_avoid_the_known_current_okf_timestamp_difference(self):
        # The active OKF text at ad30107 changes these fields from date-only
        # values to offset-bearing datetimes; the pinned PGM text does not.
        for graph in (self.pgm, self.frontmatter):
            for node in graph.nodes.values():
                self.assertNotIn("stale_after", node.properties)
                self.assertNotIn("usage_window", node.properties)
                self.assertNotIn("sources", node.properties)
            source_verified = graph.nodes[CHECKOUT].properties["verified"]
            self.assertTrue(has_explicit_offset(source_verified["at"]))
        for edge in self.pgm.relationships:
            self.assertTrue(has_explicit_offset(edge.properties["generated"]["at"]))
            events = edge.properties.get("verified", [])
            for event in events if isinstance(events, list) else [events]:
                self.assertTrue(has_explicit_offset(event["at"]))
        for entry in self.frontmatter.nodes[CHECKOUT].properties["relationships"]:
            self.assertTrue(has_explicit_offset(entry["generated"]["at"]))
            events = entry.get("verified", [])
            for event in events if isinstance(events, list) else [events]:
                self.assertTrue(has_explicit_offset(event["at"]))

    def test_direction_property_does_not_reverse_pgm_core(self):
        relationships = self.pgm.relationships
        self.assertEqual(len(relationships), 4)
        self.assertEqual({edge.source for edge in relationships}, {CHECKOUT})
        self.assertEqual({edge.target for edge in relationships}, {HANDLER})
        self.assertEqual({edge.type for edge in relationships}, {"calls"})
        self.assertTrue(
            all(edge.properties["direction"] == "inbound" for edge in relationships)
        )
        self.assertTrue(
            all(edge.properties["confidence"] == 0.85 for edge in relationships)
        )

    def test_duplicate_links_remain_distinct_and_trust_changes_portable_key(self):
        first, second, process, human = self.pgm.relationships
        self.assertEqual(first.key, second.key)
        self.assertEqual((first.occurrence, second.occurrence), (0, 1))
        self.assertNotEqual(first.id, second.id)
        self.assertNotEqual(first.key, process.key)
        self.assertNotEqual(process.key, human.key)
        self.assertEqual(
            [relationship_trust_tier(edge.properties) for edge in self.pgm.relationships],
            [
                "unverified",
                "unverified",
                "machine-confirmed",
                "human-reviewed",
            ],
        )
        # The source Concept is human-reviewed, but its first two edges are not.
        self.assertIn("verified", self.pgm.nodes[CHECKOUT].properties)
        self.assertNotIn("verified", first.properties)

    def test_frontmatter_list_is_not_pgm_relationship_semantics(self):
        relationships = self.frontmatter.relationships
        self.assertEqual(len(relationships), 4)
        self.assertTrue(all(edge.type is None for edge in relationships))
        self.assertTrue(all(edge.properties == {} for edge in relationships))
        self.assertEqual({edge.source for edge in relationships}, {CHECKOUT})
        self.assertEqual({edge.target for edge in relationships}, {HANDLER})
        self.assertEqual(
            len(self.frontmatter.nodes[CHECKOUT].properties["relationships"]), 4
        )

    def test_informative_views_agree_without_reversing_physical_links(self):
        pgm_view = [
            illustrative_view(edge.source, edge.target, edge.properties)
            for edge in self.pgm.relationships
        ]
        frontmatter_view = [
            illustrative_view(
                CHECKOUT, proposed_frontmatter_target(CHECKOUT, entry), entry
            )
            for entry in self.frontmatter.nodes[CHECKOUT].properties["relationships"]
        ]
        self.assertEqual(pgm_view, self.expected)
        self.assertEqual(frontmatter_view, self.expected)
        self.assertTrue(
            all(
                "confidence" not in entry
                for entry in self.frontmatter.nodes[CHECKOUT].properties["relationships"]
            )
        )

    def test_invalid_trust_event_fails_only_the_optional_profile(self):
        edge = self.pgm.relationships[0]
        self.assertEqual(edge.properties["type"], "calls")
        with self.assertRaises(RelationshipTrustProfileError):
            relationship_trust_tier(
                {"verified": {"by": "human:alice", "at": "2026-09-02"}}
            )

    def test_expected_pgm_reference_json_is_exact_and_round_trips(self):
        expected = json.loads(
            (FIXTURE / "expected-pgm-graph.json").read_text(encoding="utf-8")
        )
        actual = graph_to_data(self.pgm)
        self.assertEqual(actual, expected)
        self.assertEqual(graph_to_data(graph_from_data(expected)), expected)
        self.assertEqual(expected["pgmVersion"], "0.4.0 Public Draft")

    def test_projection_matches_proposed_frontmatter_common_fields(self):
        expected = json.loads(
            (FIXTURE / "expected-projection.json").read_text(encoding="utf-8")
        )
        actual = project(self.pgm)
        self.assertEqual(actual, expected)
        self.assertEqual(project(self.pgm), actual)
        self.assertEqual(
            actual["carriers"],
            [{
                "source": CHECKOUT,
                "relationships": self.frontmatter.nodes[CHECKOUT].properties[
                    "relationships"
                ],
            }],
        )
        first, duplicate, process, human = actual["mapping"]
        self.assertEqual(first["relationshipKey"], duplicate["relationshipKey"])
        self.assertNotEqual(first["relationshipId"], duplicate["relationshipId"])
        self.assertEqual([row["entryIndex"] for row in actual["mapping"]], [0, 1, 2, 3])
        self.assertEqual([row["occurrence"] for row in actual["mapping"]], [0, 1, 0, 0])
        self.assertTrue(all(row["omittedProperties"] == ["confidence"] for row in actual["mapping"]))
        self.assertTrue(all(row["directionIsOnlyAnAuthoredProperty"] for row in actual["mapping"]))
        self.assertNotEqual(process["relationshipKey"], human["relationshipKey"])

    def test_synthetic_lifecycle_projection_shows_non_projectable_cases(self):
        self.assertEqual(self.synthetic.errors, [])
        expected = json.loads(
            (FIXTURE / "expected-synthetic-projection.json").read_text(
                encoding="utf-8"
            )
        )
        actual = project(self.synthetic)
        self.assertEqual(actual, expected)
        entries = actual["carriers"][0]["relationships"]
        self.assertEqual([entry["type"] for entry in entries], ["supersedes", "contradicts", "contradicts"])
        self.assertEqual([row["resolved"] for row in actual["mapping"]], [True, True, False])
        self.assertEqual(len(actual["unprojected"]), 1)
        self.assertEqual(actual["unprojected"][0]["reason"], "untyped-link-cannot-satisfy-required-type")

    def test_remember_input_is_frontmatter_native_with_no_pgm_link_assertion(self):
        remember = parse_corpus(FIXTURE / "frontmatter-native-remember" / "bundle")
        self.assertEqual(remember.errors, [])
        self.assertEqual(remember.relationships, [])
        self.assertEqual(project(remember)["carriers"], [])
        node = next(iter(remember.nodes.values()))
        self.assertEqual(node.properties["supersedes"], "okf-conformance-predecessor-000")
        self.assertEqual(node.properties["contested_by"], ["okf-conformance-disputer-002"])
        self.assertEqual(node.properties["verified"], [])

    def test_query_preview_keeps_open_proposal_and_fail_safe_boundaries(self):
        expected = json.loads(
            (FIXTURE / "expected-query-view.json").read_text(encoding="utf-8")
        )
        actual = query_view()
        self.assertEqual(actual, expected)
        remember = actual["rememberFrontmatterNative"]
        self.assertFalse(remember["sourceHasPgmLinkOccurrences"])
        self.assertFalse(remember["rootLogHasResolutionMarkers"])
        self.assertTrue(all(not row["targetPresent"] for row in remember["references"]))
        self.assertEqual(remember["references"][1]["storedField"], "contested_by")
        self.assertEqual(remember["references"][1]["interpretedType"], "contradicts")
        synthetic = actual["syntheticPgmLinkNative"]
        self.assertFalse(synthetic["rootLogHasResolutionMarkers"])
        self.assertTrue(all(not row["excludeTargetFromInForce"] for row in synthetic["references"]))
        self.assertEqual(
            synthetic["references"][1]["derivedReverse"],
            {
                "on": "urn:pgm-fixture:claim-001",
                "type": "contradicted_by",
                "from": "urn:pgm-fixture:decision-002",
            },
        )
        self.assertIsNone(synthetic["references"][2]["derivedReverse"])


if __name__ == "__main__":
    unittest.main()
