import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "parser"))

from canonical import canonical_json  # noqa: E402
from pgmark import (  # noqa: E402
    graph_from_json,
    graph_to_cypher,
    graph_to_data,
    graph_to_json,
    parse_corpus,
)


def concept(node_type="Note", body="", metadata=""):
    extra = f"{metadata.rstrip()}\n" if metadata else ""
    return f"---\ntype: {node_type}\n{extra}---\n\n{body}"


class BundleCase(unittest.TestCase):
    def parse_files(self, files):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            return parse_corpus(root)


class YamlProfileTests(BundleCase):
    def test_core_schema_resolution_and_explicit_timestamp(self):
        graph = self.parse_files(
            {
                "note.md": concept(
                    metadata=(
                        "legacy: yes\n"
                        "enabled: true\n"
                        "date_text: 2026-08-23\n"
                        "date_value: !!timestamp 2026-08-23"
                    )
                )
            }
        )

        properties = graph.nodes["note"].properties
        self.assertEqual(properties["legacy"], "yes")
        self.assertIs(properties["enabled"], True)
        self.assertEqual(properties["date_text"], "2026-08-23")
        self.assertEqual(properties["date_value"], datetime.date(2026, 8, 23))
        self.assertEqual(graph.errors, [])

    def test_duplicate_mapping_keys_are_core_error(self):
        graph = self.parse_files(
            {"note.md": "---\ntype: Note\ntype: Other\n---\n"}
        )

        self.assertTrue(graph.errors)
        self.assertEqual(graph.diagnostics[0].code, "PGM_YAML_INVALID")

    def test_unknown_tag_is_core_error_but_title_tag_is_warning(self):
        concept_error = self.parse_files(
            {"note.md": concept(metadata="value: !application/object x")}
        )
        self.assertEqual(
            concept_error.diagnostics[0].code, "PGM_YAML_TAG_UNSUPPORTED"
        )

        title_warning = self.parse_files(
            {
                "note.md": concept(
                    body='[target](target.md "{type: relates, value: !x y}")\n'
                )
            }
        )
        self.assertEqual(len(title_warning.relationships), 1)
        self.assertEqual(title_warning.relationships[0].properties, {})
        self.assertEqual(
            title_warning.diagnostics[0].code, "PGM_YAML_TAG_UNSUPPORTED"
        )
        self.assertEqual(title_warning.diagnostics[0].severity, "warning")

    def test_alias_dag_expands_and_cycles_are_rejected_by_context(self):
        dag = self.parse_files(
            {
                "note.md": concept(
                    body=(
                        '[target](target.md "{type: relates, first: &a [1, 2], '
                        'second: *a}")\n'
                    )
                )
            }
        )
        properties = dag.relationships[0].properties
        self.assertEqual(properties["first"], properties["second"])
        self.assertIsNot(properties["first"], properties["second"])

        concept_cycle = self.parse_files(
            {
                "note.md": (
                    "---\ntype: Note\ncycle: &cycle {self: *cycle}\n---\n"
                )
            }
        )
        self.assertEqual(concept_cycle.diagnostics[0].code, "PGM_YAML_CYCLE")
        self.assertEqual(concept_cycle.diagnostics[0].severity, "error")

        relationship_cycle = self.parse_files(
            {
                "note.md": concept(
                    body=(
                        '[target](target.md "{type: relates, cycle: &cycle '
                        '{self: *cycle}}")\n'
                    )
                )
            }
        )
        self.assertEqual(len(relationship_cycle.relationships), 1)
        self.assertEqual(relationship_cycle.relationships[0].properties, {})
        self.assertEqual(
            relationship_cycle.diagnostics[0].code, "PGM_YAML_CYCLE"
        )
        self.assertEqual(relationship_cycle.diagnostics[0].severity, "warning")

    def test_nested_collection_keys_and_python_collisions_round_trip(self):
        graph = self.parse_files(
            {
                "note.md": concept(
                    metadata=(
                        "exotic:\n"
                        "  ? {nested: key}\n"
                        "  : mapping key\n"
                        "  ? true\n"
                        "  : boolean key\n"
                        "  ? 1\n"
                        "  : number key\n"
                        "mixed_set: !!set {true, 1}"
                    )
                )
            }
        )

        self.assertEqual(graph.errors, [])
        encoded = graph_to_json(graph)
        self.assertEqual(graph_to_json(graph_from_json(encoded)), encoded)
        properties = canonical_json(graph.nodes["note"].properties)
        self.assertIn('["bool",true]', properties)
        self.assertIn('["number","1"]', properties)
        self.assertIn('["mapping",[[["string","nested"]', properties)


class DestinationProfileTests(BundleCase):
    def test_path_fragment_targets_concept_but_fragment_only_does_not(self):
        graph = self.parse_files(
            {
                "source.md": concept(
                    body=(
                        "[target](target.md#details)\n"
                        "[local heading](#details)\n"
                    )
                )
            }
        )

        self.assertEqual(len(graph.relationships), 1)
        self.assertEqual(graph.relationships[0].target, "target")

    def test_query_reserved_uppercase_and_external_paths_are_not_concepts(self):
        graph = self.parse_files(
            {
                "source.md": concept(
                    body=(
                        "[query](target.md?view=full)\n"
                        "[index](index.md)\n"
                        "[log](log.md)\n"
                        "[uppercase](Target.MD)\n"
                        "[external](https://example.com/target.md)\n"
                    )
                )
            }
        )

        self.assertEqual(graph.relationships, [])
        self.assertEqual(
            {diagnostic.code for diagnostic in graph.diagnostics},
            {"PGM_CONCEPT_DESTINATION_INVALID"},
        )

    def test_percent_decoding_is_segment_safe_and_bundle_bounded(self):
        graph = self.parse_files(
            {
                "nested/source.md": concept(
                    body=(
                        "[space](../people/Ada%20Lovelace.md)\n"
                        "[escape](%2e%2e/%2e%2e/outside.md)\n"
                        "[slash](target%2Fchild.md)\n"
                        "[backslash](target%5Cchild.md)\n"
                        "[malformed](target%2.md)\n"
                    )
                )
            }
        )

        self.assertEqual(len(graph.relationships), 2)
        self.assertEqual(
            [relationship.target for relationship in graph.relationships],
            ["people/Ada Lovelace", "nested/target%2"],
        )
        # CommonMark normalizes the malformed source escape to ``%25`` before
        # PGM sees the parsed destination, so it is then decoded exactly once
        # to a literal percent sign. The other three unsafe paths are rejected.
        self.assertEqual(len(graph.warnings), 3)


class SerializationTests(BundleCase):
    def test_reference_json_is_deterministic_lossless_and_marks_unresolved(self):
        graph = self.parse_files(
            {
                "source.md": concept(
                    body=(
                        "[bare](target.md)\n"
                        '[typed](target.md "{type: relates, value: 2}")\n'
                    ),
                    metadata="large: 1208925819614629174706176",
                )
            }
        )

        first = graph_to_json(graph)
        second = graph_to_json(graph)
        self.assertEqual(first, second)
        data = json.loads(first)
        self.assertEqual(data["format"], "pgm-graph")
        self.assertEqual(len(data["nodes"]), 1)
        self.assertEqual(len(data["relationships"]), 2)
        self.assertTrue(all(not item["resolved"] for item in data["relationships"]))
        self.assertEqual(data, graph_to_data(graph))
        self.assertIn("1208925819614629174706176", first)

    def test_cypher_uses_generic_types_ids_and_distinguishable_placeholders(self):
        graph = self.parse_files(
            {"source.md": concept(body="[target](missing.md)\n")}
        )
        cypher = graph_to_cypher(graph)

        self.assertIn(":PGMConcept", cypher)
        self.assertIn("ON CREATE SET n0.pgm_resolved = false", cypher)
        self.assertIn(":PGM_RELATIONSHIP", cypher)
        self.assertIn("pgm_relationship_id", cypher)
        self.assertIn("pgm_relationship_key", cypher)
        self.assertNotIn("pgm_type:", cypher)

    def test_numeric_equivalence_is_shared_by_relationship_key(self):
        integer_graph = self.parse_files(
            {
                "source.md": concept(
                    body='[target](target.md "{type: value, number: 1}")\n'
                )
            }
        )
        float_graph = self.parse_files(
            {
                "source.md": concept(
                    body='[target](target.md "{number: 1.0, type: value}")\n'
                )
            }
        )

        self.assertEqual(
            integer_graph.relationships[0].key,
            float_graph.relationships[0].key,
        )
        self.assertEqual(canonical_json(1), canonical_json(1.0))


if __name__ == "__main__":
    unittest.main()
