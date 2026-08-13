import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "parser"))

from pgmark import graph_to_cypher, parse_corpus  # noqa: E402


class ParserTests(unittest.TestCase):
    def parse_files(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            return parse_corpus(root)

    def test_node_label(self):
        graph = self.parse_files({"ada.md": "[:Person]()\n"})

        node = graph.nodes["ada.md"]
        self.assertEqual(node.labels, ["Person"])
        self.assertEqual(node.properties, {})
        self.assertEqual(node.relationships, [])

    def test_node_label_and_properties(self):
        graph = self.parse_files(
            {"ada.md": '[:Person {name: "Ada", born: 1815}]()\n'}
        )

        node = graph.nodes["ada.md"]
        self.assertEqual(node.labels, ["Person"])
        self.assertEqual(node.properties, {"name": "Ada", "born": 1815})
        self.assertEqual(graph.errors, [])

    def test_multiple_node_annotations_merge_semantics(self):
        graph = self.parse_files(
            {
                "ada.md": (
                    '[:Person {name: "Ada"}]()\n'
                    "[:Mathematician {born: 1815}]()\n"
                )
            }
        )

        node = graph.nodes["ada.md"]
        self.assertEqual(node.labels, ["Person", "Mathematician"])
        self.assertEqual(node.properties, {"name": "Ada", "born": 1815})

    def test_duplicate_label_is_deduplicated(self):
        graph = self.parse_files({"ada.md": "[:Person]()\n[:Person]()\n"})

        self.assertEqual(graph.nodes["ada.md"].labels, ["Person"])

    def test_equivalent_repeated_property_is_allowed(self):
        graph = self.parse_files(
            {
                "ada.md": (
                    "[:Person {born: 1815}]()\n"
                    "[:Mathematician {born: 1815}]()\n"
                )
            }
        )

        self.assertEqual(graph.nodes["ada.md"].properties["born"], 1815)
        self.assertEqual(graph.errors, [])

    def test_conflicting_repeated_property_is_validation_error(self):
        graph = self.parse_files(
            {
                "ada.md": (
                    "[:Person {born: 1815}]()\n"
                    "[:Mathematician {born: 1816}]()\n"
                )
            }
        )

        self.assertEqual(len(graph.errors), 1)
        self.assertIn("conflicting node property 'born'", graph.errors[0])
        with self.assertRaisesRegex(ValueError, "validation errors"):
            graph_to_cypher(graph)

    def test_relationship(self):
        graph = self.parse_files(
            {
                "ada.md": "[:BORN_IN](London.md)\n",
                "London.md": "# London\n",
            }
        )

        self.assertEqual(len(graph.relationships), 1)
        relationship = graph.relationships[0]
        self.assertRegex(relationship.id, r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(relationship.source, "ada.md")
        self.assertEqual(relationship.type, "BORN_IN")
        self.assertEqual(relationship.target, "London.md")
        self.assertEqual(relationship.properties, {})
        self.assertEqual(graph.nodes["ada.md"].relationships, [relationship])

    def test_relationship_with_properties(self):
        graph = self.parse_files(
            {
                "ada.md": "[:BORN_IN {year: 1815}](London.md)\n",
                "London.md": "# London\n",
            }
        )

        self.assertEqual(graph.relationships[0].properties, {"year": 1815})
        self.assertIn(")-[:BORN_IN {", graph_to_cypher(graph))

    def test_relative_relationship_target_uses_source_directory(self):
        graph = self.parse_files(
            {"people/ada.md": "[:BORN_IN](../places/London.md)\n"}
        )

        self.assertEqual(graph.relationships[0].target, "places/London.md")

    def test_fragment_only_relationship_targets_current_document(self):
        graph = self.parse_files({"ada.md": "[:REFERENCES](#biography)\n"})

        self.assertEqual(graph.relationships[0].target, "ada.md")

    def test_relationships_with_different_properties_remain_distinct(self):
        graph = self.parse_files(
            {
                "ada.md": (
                    "[:VISITED {year: 1830}](London.md)\n"
                    "[:VISITED {year: 1831}](London.md)\n"
                )
            }
        )

        self.assertEqual(len(graph.relationships), 2)
        self.assertEqual(len({relationship.id for relationship in graph.relationships}), 2)
        self.assertEqual(graph_to_cypher(graph).count("CREATE (n0)-[:VISITED"), 2)

    def test_exact_duplicate_relationships_are_coalesced(self):
        graph = self.parse_files(
            {
                "ada.md": (
                    "[:VISITED {year: 1830}](London.md)\n"
                    "[:VISITED {year: 1830}](London.md)\n"
                )
            }
        )

        self.assertEqual(len(graph.relationships), 1)

    def test_numerically_equivalent_relationship_properties_are_coalesced(self):
        graph = self.parse_files(
            {
                "ada.md": (
                    "[:RATED {score: 1}](work.md)\n"
                    "[:RATED {score: 1.0}](work.md)\n"
                )
            }
        )

        self.assertEqual(len(graph.relationships), 1)

    def test_relationship_fingerprint_is_stable_under_reordering(self):
        first = self.parse_files(
            {
                "ada.md": (
                    "[:Person]()\n"
                    "[:BORN_IN {year: 1815, source: register}](London.md)\n"
                )
            }
        )
        second = self.parse_files(
            {
                "ada.md": (
                    "[Biography](bio.md)\n"
                    "[:BORN_IN {source: register, year: 1815}](London.md)\n"
                    "[:Person]()\n"
                )
            }
        )

        self.assertEqual(first.relationships[0].id, second.relationships[0].id)

    def test_create_and_natural_key_merge_modes(self):
        graph = self.parse_files(
            {"ada.md": "[:BORN_IN {year: 1815}](London.md)\n"}
        )

        create_cypher = graph_to_cypher(graph)
        merge_cypher = graph_to_cypher(graph, relationship_mode="merge")
        self.assertIn("CREATE (n0)-[:BORN_IN", create_cypher)
        self.assertIn("MERGE (n0)-[:BORN_IN", merge_cypher)
        self.assertNotIn("CREATE (n0)-[:BORN_IN", merge_cypher)

        with self.assertRaisesRegex(ValueError, "relationship mode"):
            graph_to_cypher(graph, relationship_mode="replace")

    def test_empty_angle_bracket_destination_is_node_annotation(self):
        graph = self.parse_files({"ada.md": "[:Person](<>)\n"})

        self.assertEqual(graph.nodes["ada.md"].labels, ["Person"])
        self.assertEqual(graph.relationships, [])

    def test_ordinary_empty_link_has_no_graph_semantics(self):
        graph = self.parse_files({"note.md": "[coming soon]()\n"})

        self.assertEqual(graph.nodes["note.md"].labels, [])
        self.assertEqual(graph.nodes["note.md"].properties, {})
        self.assertEqual(graph.relationships, [])
        self.assertEqual(graph.warnings, [])

    def test_ordinary_non_empty_link_has_no_graph_semantics(self):
        graph = self.parse_files({"note.md": "[London](London.md)\n"})

        self.assertEqual(graph.relationships, [])
        self.assertNotIn("London.md", graph.nodes)

    def test_wikilink_has_no_graph_semantics(self):
        graph = self.parse_files(
            {"note.md": "[[London | :BORN_IN {year: 1815}]]\n"}
        )

        self.assertEqual(graph.relationships, [])
        self.assertEqual(graph.warnings, [])

    def test_class_name_is_required(self):
        graph = self.parse_files({"note.md": "[:]();\n"})

        self.assertEqual(graph.nodes["note.md"].labels, [])
        self.assertEqual(len(graph.warnings), 1)
        self.assertIn("malformed PGM class expression", graph.warnings[0])

    def test_property_map_must_be_a_mapping(self):
        graph = self.parse_files({"note.md": "[:Person [1, 2, 3]]()\n"})

        self.assertEqual(graph.nodes["note.md"].labels, [])
        self.assertEqual(len(graph.warnings), 1)
        self.assertIn("malformed PGM class expression", graph.warnings[0])

    def test_malformed_semantic_annotation_warns_and_skips(self):
        graph = self.parse_files(
            {"a.md": "[:approvedBy {date](b.md)\n", "b.md": "# B\n"}
        )

        self.assertEqual(graph.relationships, [])
        self.assertEqual(len(graph.warnings), 1)
        self.assertIn("malformed PGM class expression", graph.warnings[0])

    def test_direction_marker_warns_and_skips(self):
        graph = self.parse_files(
            {"peter.md": "[:approvedBy -> Invoice](invoice.md)\n"}
        )

        self.assertEqual(graph.relationships, [])
        self.assertEqual(len(graph.warnings), 1)
        self.assertIn("direction markers are not supported", graph.warnings[0])

    def test_supported_property_values_and_cypher_serialization(self):
        graph = self.parse_files(
            {
                "note.md": (
                    '[:Thing {text: "hello", count: 2, ratio: 0.5, active: true, '
                    "missing: null, tags: [one, two]}]()\n"
                )
            }
        )

        self.assertEqual(
            graph.nodes["note.md"].properties,
            {
                "text": "hello",
                "count": 2,
                "ratio": 0.5,
                "active": True,
                "missing": None,
                "tags": ["one", "two"],
            },
        )
        self.assertIn('n0.tags = ["one", "two"]', graph_to_cypher(graph))

    def test_label_is_not_reserved(self):
        graph = self.parse_files({"a.md": "[:LABEL](target.md)\n"})

        self.assertEqual(graph.nodes["a.md"].labels, [])
        self.assertEqual(graph.relationships[0].type, "LABEL")

    def test_examples_match_expected_cypher(self):
        graph = parse_corpus(ROOT / "examples")
        expected = (ROOT / "examples" / "expected.cypher").read_text(encoding="utf-8").strip()
        expected_merge = (ROOT / "examples" / "expected-merge.cypher").read_text(
            encoding="utf-8"
        ).strip()

        self.assertEqual(graph.warnings, [])
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph_to_cypher(graph), expected)
        self.assertEqual(
            graph_to_cypher(graph, relationship_mode="merge"),
            expected_merge,
        )


if __name__ == "__main__":
    unittest.main()
