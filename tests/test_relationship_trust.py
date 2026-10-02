"""Reference tests for the OKF-analog Relationship trust derivation."""

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "parser"))

from relationship_trust import (  # noqa: E402
    RelationshipTrustProfileError,
    relationship_trust_report,
    relationship_trust_tier,
)
from pgmark import graph_to_json, parse_corpus  # noqa: E402


class RelationshipTrustTests(unittest.TestCase):
    def test_fixture_report_does_not_change_core_or_direction(self):
        bundle = ROOT / "interop" / "okf-relationship-carriers" / "pgm-links"
        graph = parse_corpus(bundle)
        before = graph_to_json(graph)
        report = relationship_trust_report(graph)
        self.assertTrue(report["conforms"])
        self.assertEqual(report["diagnostics"], [])
        self.assertEqual(
            [item["trustTier"] for item in report["relationships"]],
            ["unverified", "unverified", "machine-confirmed", "human-reviewed"],
        )
        self.assertEqual(
            {(item["source"], item["target"]) for item in report["relationships"]},
            {("functions/checkout", "functions/handler")},
        )
        self.assertEqual(graph_to_json(graph), before)

    def test_missing_verification_is_unverified_independent_of_generation(self):
        self.assertEqual(relationship_trust_tier({}), "unverified")
        self.assertEqual(
            relationship_trust_tier(
                {"generated": {"by": "human:alice", "at": "2026-09-01T12:00:00Z"}}
            ),
            "unverified",
        )
        self.assertEqual(
            relationship_trust_tier({"generated": {"by": "process:export"}}),
            "unverified",
        )
        self.assertEqual(relationship_trust_tier({"generated": None}), "unverified")

    def test_one_machine_verifier_and_mixed_list(self):
        self.assertEqual(
            relationship_trust_tier(
                {"verified": {"by": "process:ci", "at": "2026-09-02T09:00:00Z"}}
            ),
            "machine-confirmed",
        )
        self.assertEqual(
            relationship_trust_tier(
                {
                    "verified": [
                        {"by": "roteiro/5.0.0", "at": "2026-09-02T08:00:00Z"},
                        {
                            "by": "human:alice",
                            "at": "2026-09-02T10:00:00+02:00",
                            "note": "manual review",
                        },
                    ]
                }
            ),
            "human-reviewed",
        )

    def test_direction_confidence_and_type_do_not_change_tier(self):
        properties = {
            "type": "calls",
            "direction": "inbound",
            "confidence": 0.99,
            "verified": {"by": "process:ci", "at": "2026-09-02T09:00:00Z"},
        }
        before = dict(properties)
        self.assertEqual(relationship_trust_tier(properties), "machine-confirmed")
        self.assertEqual(properties, before)

    def test_explicit_tagged_aware_timestamp_is_accepted(self):
        self.assertEqual(
            relationship_trust_tier(
                {
                    "verified": {
                        "by": "human:alice",
                        "at": datetime(2026, 9, 2, 9, tzinfo=timezone.utc),
                    }
                }
            ),
            "human-reviewed",
        )

    def test_present_malformed_events_are_profile_errors_not_unverified(self):
        invalid_cases = (
            {"verified": None},
            {"verified": []},
            {"verified": 1},
            {"verified": {"by": "human:alice"}},
            {"verified": {"by": "human:", "at": "2026-09-02T09:00:00Z"}},
            {"verified": {"by": "alice", "at": "2026-09-02T09:00:00Z"}},
            {"verified": {"by": "human:alice", "at": "2026-09-02"}},
            {"verified": {"by": "human:alice", "at": "2026-09-02T09:00:00"}},
            {"verified": {"by": "human:alice", "at": "2026-02-30T09:00:00Z"}},
            {"verified": {"by": "human:alice", "at": datetime(2026, 9, 2, 9)}},
        )
        for properties in invalid_cases:
            with self.subTest(properties=properties):
                with self.assertRaises(RelationshipTrustProfileError):
                    relationship_trust_tier(properties)

    def test_invalid_profile_does_not_invalidate_core_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "a.md").write_text(
                '---\ntype: Concept\n---\n\n[b](b.md "{verified: null}")\n',
                encoding="utf-8",
            )
            (root / "b.md").write_text(
                "---\ntype: Concept\n---\n\n# b\n", encoding="utf-8"
            )
            graph = parse_corpus(root)
            self.assertEqual(graph.errors, [])
            self.assertEqual(len(graph.relationships), 1)
            self.assertIsNone(graph.relationships[0].properties["verified"])
            report = relationship_trust_report(graph)
            self.assertFalse(report["conforms"])
            self.assertIsNone(report["relationships"][0]["trustTier"])
            self.assertEqual(len(report["diagnostics"]), 1)

            core = subprocess.run(
                [sys.executable, str(ROOT / "parser" / "pgmark.py"), "validate", str(root)],
                capture_output=True,
                check=False,
            )
            trust = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "parser" / "pgmark.py"),
                    "trust",
                    str(root),
                    "--json",
                ],
                capture_output=True,
                check=False,
            )
            self.assertEqual(core.returncode, 0, core.stderr)
            self.assertEqual(trust.returncode, 1, trust.stderr)
            cli_report = json.loads(trust.stdout)
            self.assertFalse(cli_report["conforms"])
            self.assertEqual(cli_report["pgmCoreVersion"], "0.4.0 Public Draft")
            self.assertEqual(cli_report["processorVersion"], "0.4.2a1")
            self.assertIn("okfCommit", cli_report)


if __name__ == "__main__":
    unittest.main()
