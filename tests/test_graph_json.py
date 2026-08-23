import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "parser"))

from canonical import (  # noqa: E402
    FrozenCanonicalSet,
    FrozenMapping,
    canonical_document,
    decode_canonical_document,
    relationship_id,
    relationship_key,
)
from pgmark import (  # noqa: E402
    Graph,
    Node,
    Relationship,
    graph_from_data,
    graph_from_json,
    graph_to_data,
    graph_to_json,
    main,
    parse_corpus,
)


SCHEMA_PATH = ROOT / "interop" / "pgm-graph.schema.json"


def concept(node_type="Note", body="", metadata=""):
    extra = f"{metadata.rstrip()}\n" if metadata else ""
    return f"---\ntype: {node_type}\n{extra}---\n\n{body}"


class GraphJsonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.schema_validator = Draft202012Validator(cls.schema)

    def parse_files(self, files):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            return parse_corpus(root)

    def representative_graph(self):
        graph = self.parse_files(
            {
                "source.md": concept(
                    body=(
                        "[untyped](target.md)\n"
                        "[duplicate](target.md)\n"
                        '[typed](target.md "{type: relates, weight: 1}")\n'
                        "[unresolved](missing.md)\n"
                        '[invalid type](other.md "{type: 42, note: retained}")\n'
                    ),
                    metadata=(
                        "active: true\n"
                        "payload: !!binary SGVsbG8=\n"
                        "observed: !!timestamp 2026-08-23T10:30:00Z"
                    ),
                ),
                "target.md": concept("Target"),
            }
        )
        self.assertEqual(graph.errors, [])
        self.assertEqual(len(graph.warnings), 1)
        return graph

    def test_schema_accepts_reference_export(self):
        data = graph_to_data(self.representative_graph())
        self.schema_validator.validate(data)
        self.assertEqual(data["pgmVersion"], "0.4.0 Public Draft")
        self.assertEqual(data["conformance"]["processorName"], "pgmark")
        self.assertEqual(data["conformance"]["processorVersion"], "0.4.0a1")
        self.assertEqual(
            data["conformance"]["exchangeProfile"],
            "PGM JSON Exchange Profile v1",
        )
        self.assertEqual(
            data["conformance"]["schema"], "urn:pgm:schema:graph:1"
        )
        self.assertEqual(
            data["conformance"]["classes"],
            [
                "PGM Core Processor",
                "Portable Relationship Identification Processor",
                "PGM JSON Exchange Processor",
            ],
        )
        self.assertEqual(
            data["conformance"]["yamlExplicitTags"],
            [
                "tag:yaml.org,2002:binary",
                "tag:yaml.org,2002:set",
                "tag:yaml.org,2002:timestamp",
            ],
        )
        self.assertEqual(
            data["conformance"]["yamlAliasPolicy"],
            "acyclic-expand-by-value; cycles-rejected",
        )
        self.assertEqual(
            data["conformance"]["diagnosticCategories"],
            {
                "coreErrors": "error",
                "warnings": "warning",
                "adapterErrors": "adapter-error",
            },
        )

    def test_import_accepts_identified_conforming_foreign_processor(self):
        data = graph_to_data(self.representative_graph())
        data["conformance"]["processorName"] = "other-pgm"
        data["conformance"]["processorVersion"] = "2.1.0"
        data["conformance"]["markdownProfile"] = "EquivalentMarkdown 1.0"
        data["conformance"]["classes"] = [
            "Extension Processor",
            "PGM JSON Exchange Processor",
            "PGM Core Processor",
            "Portable Relationship Identification Processor",
        ]
        data["conformance"]["yamlExplicitTags"] = [
            "tag:example.test,2026:extension",
            "tag:yaml.org,2002:timestamp",
            "tag:yaml.org,2002:binary",
            "tag:yaml.org,2002:set",
        ]

        self.schema_validator.validate(data)
        imported = graph_from_data(data)

        self.assertEqual(
            graph_to_data(imported)["conformance"]["processorName"], "pgmark"
        )

    def test_import_requires_named_markdown_profile(self):
        data = graph_to_data(self.representative_graph())
        data["conformance"]["markdownProfile"] = ""

        with self.assertRaises(ValidationError):
            self.schema_validator.validate(data)
        with self.assertRaises(ValueError):
            graph_from_data(data)

    def test_import_requires_exact_exchange_profile_and_schema_revision(self):
        for field, value in (
            ("exchangeProfile", "PGM JSON Exchange Profile v2"),
            ("schema", "urn:pgm:schema:graph:2"),
        ):
            with self.subTest(field=field):
                data = graph_to_data(self.representative_graph())
                data["conformance"][field] = value
                with self.assertRaises(ValidationError):
                    self.schema_validator.validate(data)
                with self.assertRaises(ValueError):
                    graph_from_data(data)

        for field, value in (
            ("classes", ["PGM Core Processor"]),
            ("yamlExplicitTags", ["tag:yaml.org,2002:timestamp"]),
            ("yamlAliasPolicy", "implementation-defined"),
            ("diagnosticCategories", {"warnings": "warning"}),
        ):
            with self.subTest(field=field):
                data = graph_to_data(self.representative_graph())
                data["conformance"][field] = value
                with self.assertRaises(ValidationError):
                    self.schema_validator.validate(data)
                with self.assertRaises(ValueError):
                    graph_from_data(data)

    def test_export_import_export_is_exact_and_preserves_occurrences(self):
        graph = self.representative_graph()
        exported_data = graph_to_data(graph)
        exported_json = graph_to_json(graph)

        imported = graph_from_json(exported_json)

        self.assertEqual(graph_to_data(imported), exported_data)
        self.assertEqual(graph_to_json(imported), exported_json)
        self.assertEqual(len(imported.relationships), 5)
        self.assertEqual(len({item.id for item in imported.relationships}), 5)
        self.assertNotIn("missing", imported.nodes)
        self.assertNotIn("other", imported.nodes)
        self.assertEqual(imported.warnings, graph.warnings)

        duplicate_edges = [
            item
            for item in imported.relationships
            if item.source == "source"
            and item.target == "target"
            and item.type is None
        ]
        self.assertEqual([item.occurrence for item in duplicate_edges], [0, 1])
        self.assertEqual(len({item.key for item in duplicate_edges}), 1)

    def test_mapping_valued_and_python_colliding_keys_round_trip(self):
        mapping_key = FrozenMapping([("nested", "key")])
        exotic_mapping = FrozenMapping(
            [
                (mapping_key, "mapping key"),
                (True, "boolean key"),
                (1, "number key"),
            ]
        )
        graph = Graph(
            nodes={
                "concept": Node(
                    id="concept",
                    type="Note",
                    properties={
                        "type": "Note",
                        "exotic": exotic_mapping,
                        "set": FrozenCanonicalSet([True, 1, mapping_key]),
                    },
                )
            }
        )

        data = graph_to_data(graph)
        imported = graph_from_data(data)

        self.assertEqual(graph_to_data(imported), data)
        document = canonical_document(exotic_mapping)
        self.assertEqual(
            canonical_document(decode_canonical_document(document)), document
        )
        imported_set = imported.nodes["concept"].properties["set"]
        self.assertIsInstance(imported_set, FrozenCanonicalSet)
        self.assertEqual(len(imported_set), 3)

    def test_import_rejects_semantic_tampering(self):
        baseline = graph_to_data(self.representative_graph())
        resolved_index = next(
            index
            for index, item in enumerate(baseline["relationships"])
            if item["resolved"]
        )
        typed_index = next(
            index
            for index, item in enumerate(baseline["relationships"])
            if item["type"] == "relates"
        )

        cases = []

        wrong_resolved = copy.deepcopy(baseline)
        wrong_resolved["relationships"][resolved_index]["resolved"] = False
        cases.append(wrong_resolved)

        wrong_type = copy.deepcopy(baseline)
        wrong_type["relationships"][typed_index]["type"] = "other"
        cases.append(wrong_type)

        wrong_key = copy.deepcopy(baseline)
        wrong_key["relationships"][0]["relationshipKey"] = (
            "pgmkey:v1:sha256:" + "0" * 64
        )
        cases.append(wrong_key)

        wrong_id = copy.deepcopy(baseline)
        wrong_id["relationships"][0]["id"] = "pgmrel:v1:sha256:" + "0" * 64
        cases.append(wrong_id)

        duplicate_node = copy.deepcopy(baseline)
        duplicate_node["nodes"].append(copy.deepcopy(duplicate_node["nodes"][0]))
        cases.append(duplicate_node)

        duplicate_relationship_id = copy.deepcopy(baseline)
        duplicate_relationship_id["relationships"][1]["id"] = (
            duplicate_relationship_id["relationships"][0]["id"]
        )
        cases.append(duplicate_relationship_id)

        missing_source = copy.deepcopy(baseline)
        missing_source["relationships"][0]["source"] = "not-a-node"
        cases.append(missing_source)

        for case in cases:
            with self.subTest(case=cases.index(case)):
                with self.assertRaises(ValueError):
                    graph_from_data(case)

    def test_occurrence_ordinals_must_be_unique_and_contiguous(self):
        data = graph_to_data(self.representative_graph())
        duplicates = [
            item
            for item in data["relationships"]
            if item["source"] == "source"
            and item["target"] == "target"
            and item["type"] is None
        ]
        self.assertEqual(len(duplicates), 2)
        second_id = duplicates[1]["id"]
        tampered = copy.deepcopy(data)
        second = next(
            item for item in tampered["relationships"] if item["id"] == second_id
        )
        second["occurrence"] = 2
        second["id"] = relationship_id(second["relationshipKey"], 2)

        with self.assertRaisesRegex(ValueError, "contiguous from zero"):
            graph_from_data(tampered)

    def test_schema_rejects_noncanonical_identifier_shape(self):
        data = graph_to_data(self.representative_graph())
        data["relationships"][0]["id"] = "sha256:not-a-pgm-id"

        with self.assertRaises(ValidationError):
            self.schema_validator.validate(data)

    def test_concept_ids_are_bundle_relative_posix_paths_everywhere(self):
        baseline = graph_to_data(self.representative_graph())
        invalid_ids = (
            "",
            "/absolute",
            "a//b",
            "a/./b",
            "a/../b",
            "a\\b",
            "a\x00b",
            "a\tb",
            "a\x7fb",
            "index",
            "nested/log",
        )

        for invalid in invalid_ids:
            for location in ("node", "source", "target"):
                with self.subTest(invalid=invalid, location=location):
                    data = copy.deepcopy(baseline)
                    if location == "node":
                        data["nodes"][0]["id"] = invalid
                    else:
                        data["relationships"][0][location] = invalid
                    with self.assertRaises(ValidationError):
                        self.schema_validator.validate(data)
                    with self.assertRaises(ValueError):
                        graph_from_data(data)

    def test_export_rejects_invalid_manual_node_identity_and_type(self):
        invalid_ids = (
            "",
            "/absolute",
            "a//b",
            "a/./b",
            "a/../b",
            "a\\b",
            "a\x00b",
            "a\tb",
            "a\x7fb",
            "index",
            "nested/log",
        )
        for invalid in invalid_ids:
            with self.subTest(invalid_id=invalid):
                graph = Graph(
                    nodes={
                        invalid: Node(
                            id=invalid,
                            type="Note",
                            properties={"type": "Note"},
                        )
                    }
                )
                with self.assertRaises(ValueError):
                    graph_to_data(graph)

        for invalid_type in (None, ""):
            with self.subTest(invalid_type=invalid_type):
                graph = Graph(
                    nodes={
                        "concept": Node(
                            id="concept",
                            type=invalid_type,
                            properties={"type": invalid_type},
                        )
                    }
                )
                with self.assertRaises(ValueError):
                    graph_to_data(graph)

        mismatched = Graph(
            nodes={
                "concept": Node(
                    id="concept",
                    type="Note",
                    properties={"type": "Other"},
                )
            }
        )
        with self.assertRaisesRegex(ValueError, "retained 'type' Property"):
            graph_to_data(mismatched)

    def test_export_rejects_invalid_manual_relationship_target(self):
        properties = {}
        invalid_target = "a/../b"
        key = relationship_key("source", invalid_target, properties)
        relationship = Relationship(
            id=relationship_id(key, 0),
            key=key,
            occurrence=0,
            source="source",
            target=invalid_target,
            link_text="invalid",
            properties=properties,
        )
        graph = Graph(
            nodes={
                "source": Node(
                    id="source",
                    type="Note",
                    properties={"type": "Note"},
                    relationships=[relationship],
                )
            }
        )

        with self.assertRaisesRegex(ValueError, "Concept ID"):
            graph_to_data(graph)

    def test_export_rejects_core_errors_but_preserves_warnings(self):
        invalid = self.parse_files({"invalid.md": "# Missing frontmatter\n"})
        self.assertTrue(invalid.errors)
        with self.assertRaisesRegex(ValueError, "validation errors"):
            graph_to_data(invalid)

        warnings = self.representative_graph()
        self.assertEqual(len(graph_to_data(warnings)["diagnostics"]), 1)

    def test_json_parser_rejects_duplicate_members_and_nonfinite_numbers(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON object member"):
            graph_from_json('{"format":"pgm-graph","format":"other"}')
        with self.assertRaisesRegex(ValueError, "non-finite JSON number"):
            graph_from_json('{"value":NaN}')

    def test_cli_can_import_and_reexport_json(self):
        graph = self.representative_graph()
        expected = graph_to_json(graph)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "graph.json"
            path.write_text(expected, encoding="utf-8")
            output = io.StringIO()
            diagnostics = io.StringIO()
            with redirect_stdout(output), redirect_stderr(diagnostics):
                result = main(["import-json", str(path), "--format", "json"])

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), expected)
        self.assertIn("PGM_RELATIONSHIP_TYPE_INVALID", diagnostics.getvalue())


if __name__ == "__main__":
    unittest.main()
