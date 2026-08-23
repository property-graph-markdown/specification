import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "parser"))

from canonical import canonical_document, canonical_json  # noqa: E402
from pgmark import (  # noqa: E402
    graph_to_cypher,
    graph_to_data,
    graph_to_json,
    parse_corpus,
)
from validation import OKF_COMMIT, OKF_SPEC_SHA256, OKF_SPEC_URL  # noqa: E402


def concept(node_type, body="", metadata=""):
    extra = f"{metadata.rstrip()}\n" if metadata else ""
    return f"---\ntype: {node_type}\n{extra}---\n\n{body}"


class ParserTests(unittest.TestCase):
    def parse_files(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            return parse_corpus(root)

    def test_okf_concept_id_and_complete_frontmatter_define_node(self):
        graph = self.parse_files(
            {"people/ada.md": concept("Person", metadata='name: "Ada"\nborn: 1815')}
        )

        node = graph.nodes["people/ada"]
        self.assertEqual(node.id, "people/ada")
        self.assertEqual(node.type, "Person")
        self.assertEqual(
            node.properties, {"type": "Person", "name": "Ada", "born": 1815}
        )
        self.assertEqual(node.relationships, [])
        self.assertEqual(graph.errors, [])

    def test_type_value_has_no_pgm_identifier_grammar(self):
        graph = self.parse_files(
            {"table.md": concept("BigQuery Table", metadata="tags: [sales, orders]")}
        )

        node = graph.nodes["table"]
        self.assertEqual(node.type, "BigQuery Table")
        self.assertEqual(node.properties["type"], "BigQuery Table")
        self.assertIn("SET n0.pgm_type = \"BigQuery Table\"", graph_to_cypher(graph))

    def test_nested_okf_metadata_is_preserved_as_node_properties(self):
        graph = self.parse_files(
            {
                "note.md": concept(
                    "Reference",
                    metadata=(
                        "generated: {by: reference_agent/test, at: 2026-08-21T10:00:00Z}\n"
                        "sources:\n"
                        "  - id: source-1\n"
                        "    resource: https://example.com"
                    ),
                )
            }
        )

        properties = graph.nodes["note"].properties
        self.assertEqual(properties["type"], "Reference")
        self.assertEqual(properties["generated"]["by"], "reference_agent/test")
        self.assertEqual(properties["sources"][0]["id"], "source-1")
        encoded = canonical_json(properties)
        decoded = json.loads(encoded)
        self.assertEqual(decoded, canonical_document(properties))
        self.assertIn('["string","reference_agent/test"]', encoded)
        self.assertIn('["string","source-1"]', encoded)
        self.assertIn("pgm_properties_json", graph_to_cypher(graph))

    def test_yaml_is_parsed_as_yaml_1_2(self):
        graph = self.parse_files(
            {"note.md": concept("Reference", metadata="legacy_boolean: yes")}
        )

        self.assertEqual(graph.nodes["note"].properties["legacy_boolean"], "yes")

    def test_okf_standard_reference_is_pinned_to_an_exact_commit(self):
        self.assertRegex(OKF_COMMIT, r"^[0-9a-f]{40}$")
        self.assertRegex(OKF_SPEC_SHA256, r"^[0-9a-f]{64}$")
        self.assertIn(OKF_COMMIT, OKF_SPEC_URL)
        self.assertNotIn("/main/", OKF_SPEC_URL)

    def test_canonical_json_is_deterministic_and_parseable(self):
        first = {"z": [1, None, {"b": True, "a": "text"}], "a": 2}
        second = {"a": 2, "z": [1, None, {"a": "text", "b": True}]}

        encoded = canonical_json(first)
        self.assertEqual(encoded, canonical_json(second))
        self.assertEqual(json.loads(encoded), canonical_document(second))

    def test_missing_frontmatter_is_validation_error(self):
        graph = self.parse_files({"note.md": "# Note\n"})

        self.assertIsNone(graph.nodes["note"].type)
        self.assertIn("missing leading OKF YAML frontmatter", graph.errors[0])
        with self.assertRaisesRegex(ValueError, "validation errors"):
            graph_to_cypher(graph)

    def test_non_empty_string_node_type_is_required_by_okf(self):
        graph = self.parse_files({"note.md": "---\ntitle: Note\n---\n\n# Note\n"})

        self.assertIn("requires a non-empty string 'type'", graph.errors[0])

        whitespace = self.parse_files(
            {"note.md": '---\ntype: " "\n---\n\n# Note\n'}
        )
        self.assertEqual(whitespace.errors, [])
        self.assertEqual(whitespace.nodes["note"].type, " ")

    def test_okf_reserved_files_are_not_nodes(self):
        graph = self.parse_files(
            {
                "index.md": "# Index\n",
                "nested/log.md": "# Log\n\n## 2026-08-23\n- Update\n",
                "note.md": concept("Note"),
            }
        )

        self.assertEqual(list(graph.nodes), ["note"])
        self.assertEqual(graph.errors, [])

    def test_okf_reserved_document_structure_is_validated(self):
        invalid_log = self.parse_files(
            {"log.md": "# Log\n\n## August 23\n- Update\n"}
        )
        self.assertIn("date heading must use YYYY-MM-DD", invalid_log.errors[0])

        invalid_index = self.parse_files(
            {"nested/index.md": "---\nokf_version: '0.2'\n---\n\n# Index\n"}
        )
        self.assertIn("only the bundle-root index.md", invalid_index.errors[0])

        valid_root_index = self.parse_files(
            {"index.md": "---\nokf_version: '0.2'\n---\n\n# Index\n"}
        )
        self.assertEqual(valid_root_index.errors, [])

    def test_link_without_title_is_untyped_relationship(self):
        graph = self.parse_files(
            {
                "alice.md": concept("Person", "[Acme](Acme.md)\n"),
                "Acme.md": concept("Organization"),
            }
        )

        relationship = graph.relationships[0]
        self.assertEqual(relationship.source, "alice")
        self.assertEqual(relationship.target, "Acme")
        self.assertEqual(relationship.link_text, "Acme")
        self.assertIsNone(relationship.title)
        self.assertIsNone(relationship.type)
        self.assertEqual(relationship.properties, {})
        self.assertEqual(graph.errors, [])

    def test_normal_markdown_title_preserves_baseline_relationship(self):
        graph = self.parse_files(
            {"alice.md": concept("Person", '[Acme](Acme.md "Acme Corporation")\n')}
        )

        relationship = graph.relationships[0]
        self.assertEqual(relationship.target, "Acme")
        self.assertEqual(relationship.title, "Acme Corporation")
        self.assertIsNone(relationship.type)
        self.assertEqual(relationship.properties, {})
        self.assertEqual(graph.warnings, [])

    def test_empty_yaml_flow_map_is_equivalent_to_bare_link(self):
        graph = self.parse_files(
            {"alice.md": concept("Person", '[Acme](Acme.md "{}")\n')}
        )

        relationship = graph.relationships[0]
        self.assertIsNone(relationship.type)
        self.assertEqual(relationship.properties, {})

    def test_typed_relationship_retains_type_property(self):
        graph = self.parse_files(
            {"alice.md": concept("Person", '[Acme](Acme.md "{type: works_for}")\n')}
        )

        relationship = graph.relationships[0]
        self.assertEqual(relationship.type, "works_for")
        self.assertEqual(relationship.properties, {"type": "works_for"})

    def test_relationship_type_is_a_yaml_string_not_a_pgm_identifier(self):
        graph = self.parse_files(
            {
                "alice.md": concept(
                    "Person", "[Acme](Acme.md \"{type: 'works for'}\")\n"
                )
            }
        )

        self.assertEqual(graph.relationships[0].type, "works for")
        self.assertEqual(graph.relationships[0].properties["type"], "works for")
        cypher = graph_to_cypher(graph)
        self.assertIn(":PGM_RELATIONSHIP", cypher)
        self.assertIn('pgm_type:"works for"', cypher)

        whitespace = self.parse_files(
            {
                "alice.md": concept(
                    "Person", "[Acme](Acme.md \"{type: ' '}\")\n"
                )
            }
        )
        self.assertEqual(whitespace.relationships[0].type, " ")
        self.assertEqual(whitespace.warnings, [])

    def test_untyped_relationship_with_properties(self):
        graph = self.parse_files(
            {"alice.md": concept("Person", '[Acme](Acme.md "{since: 2024}")\n')}
        )

        relationship = graph.relationships[0]
        self.assertIsNone(relationship.type)
        self.assertEqual(relationship.properties, {"since": 2024})

    def test_typed_relationship_with_complete_yaml_properties(self):
        graph = self.parse_files(
            {
                "alice.md": concept(
                    "Person",
                    '[Acme](Acme.md "{type: works_for, since: 2024, active: true}")\n',
                )
            }
        )

        relationship = graph.relationships[0]
        self.assertEqual(relationship.type, "works_for")
        self.assertEqual(
            relationship.properties,
            {"type": "works_for", "since": 2024, "active": True},
        )

    def test_yaml_scalar_sequence_and_mapping_values_are_preserved(self):
        graph = self.parse_files(
            {
                "note.md": concept(
                    "Thing",
                    '[target](target.md "{type: describes, text: hello, count: 2, '
                    "ratio: 0.5, active: true, missing: null, roles: [architect, "
                    'developer], context: {team: graph}}")\n',
                )
            }
        )

        self.assertEqual(
            graph.relationships[0].properties,
            {
                "type": "describes",
                "text": "hello",
                "count": 2,
                "ratio": 0.5,
                "active": True,
                "missing": None,
                "roles": ["architect", "developer"],
                "context": {"team": "graph"},
            },
        )

    def test_okf_named_relationship_properties_are_opaque_and_preserved(self):
        graph = self.parse_files(
            {
                "note.md": concept(
                    "Note",
                    '[target](target.md "{type: supports, status: stable, '
                    "stale_after: 2026-12-31, generated: {by: human:alice, "
                    "at: 2026-08-23T10:00:00Z}, verified: [{by: human:bob, "
                    "at: 2026-08-23T11:00:00Z}], sources: [{id: evidence-1, "
                    'resource: https://example.com/evidence}], tags: [reviewed]}")\n',
                )
            }
        )

        properties = graph.relationships[0].properties
        self.assertEqual(properties["type"], "supports")
        self.assertEqual(properties["status"], "stable")
        self.assertEqual(properties["stale_after"], "2026-12-31")
        self.assertEqual(properties["generated"]["by"], "human:alice")
        self.assertEqual(properties["verified"][0]["by"], "human:bob")
        self.assertEqual(properties["sources"][0]["id"], "evidence-1")
        self.assertEqual(properties["tags"], ["reviewed"])

    def test_quotes_and_markdown_escaping_in_title(self):
        graph = self.parse_files(
            {
                "note.md": concept(
                    "Thing",
                    '[target](target.md "{type: describes, note: \\"quoted value\\"}")\n',
                )
            }
        )

        relationship = graph.relationships[0]
        self.assertEqual(relationship.title, '{type: describes, note: "quoted value"}')
        self.assertEqual(relationship.properties["note"], "quoted value")

    def test_invalid_yaml_flow_map_is_nonfatal_baseline_relationship(self):
        graph = self.parse_files(
            {"note.md": concept("Note", '[target](target.md "{type:")\n')}
        )

        relationship = graph.relationships[0]
        self.assertIsNone(relationship.type)
        self.assertEqual(relationship.properties, {})
        self.assertEqual(graph.errors, [])
        self.assertEqual(len(graph.warnings), 1)
        self.assertIn("invalid PGM YAML Flow Mapping title", graph.warnings[0])

    def test_invalid_relationship_type_is_preserved_and_nonfatal(self):
        graph = self.parse_files(
            {"note.md": concept("Note", '[target](target.md "{type: 42}")\n')}
        )

        relationship = graph.relationships[0]
        self.assertIsNone(relationship.type)
        self.assertEqual(relationship.properties, {"type": 42})
        self.assertEqual(graph.errors, [])
        self.assertIn("Relationship remains untyped", graph.warnings[0])

        null_graph = self.parse_files(
            {"note.md": concept("Note", '[target](target.md "{type: null}")\n')}
        )
        self.assertIsNone(null_graph.relationships[0].type)
        self.assertEqual(null_graph.relationships[0].properties, {"type": None})
        self.assertIn("Relationship remains untyped", null_graph.warnings[0])

    def test_yaml_binary_and_set_values_are_valid_core_properties(self):
        graph = self.parse_files(
            {
                "note.md": concept(
                    "Note",
                    '[target](target.md "{type: carries, payload: !!binary SGVsbG8=, '
                    'flags: !!set {one: null, two: null}}")\n',
                )
            }
        )

        properties = graph.relationships[0].properties
        self.assertEqual(properties["payload"], b"Hello")
        self.assertEqual(properties["flags"], {"one", "two"})
        self.assertEqual(graph.errors, [])
        encoded = canonical_json(properties)
        decoded = json.loads(encoded)
        self.assertEqual(decoded, canonical_document(properties))
        self.assertIn('["binary","SGVsbG8="]', encoded)
        self.assertIn('["set",', encoded)
        self.assertIn("pgm_properties_json", graph_to_cypher(graph))

    def test_non_string_outer_property_key_keeps_baseline_relationship(self):
        graph = self.parse_files(
            {"note.md": concept("Note", '[target](target.md "{1: value}")\n')}
        )

        self.assertEqual(len(graph.relationships), 1)
        self.assertEqual(graph.relationships[0].properties, {})
        self.assertIn("Property map keys must be strings", graph.warnings[0])

    def test_relative_and_absolute_links_preserve_occurrences_and_share_key(self):
        graph = self.parse_files(
            {
                "people/alice.md": concept(
                    "Person",
                    "[Relative](../organizations/Acme.md)\n"
                    "[Absolute](/organizations/Acme.md)\n",
                )
            }
        )

        self.assertEqual(len(graph.relationships), 2)
        self.assertEqual(
            [relationship.target for relationship in graph.relationships],
            ["organizations/Acme", "organizations/Acme"],
        )
        self.assertEqual(len({relationship.key for relationship in graph.relationships}), 1)
        self.assertEqual(
            [relationship.occurrence for relationship in graph.relationships], [0, 1]
        )
        self.assertEqual(len({relationship.id for relationship in graph.relationships}), 2)

    def test_fragment_only_link_is_navigation_not_relationship(self):
        graph = self.parse_files(
            {"ada.md": concept("Person", "[Biography](#biography)\n")}
        )

        self.assertEqual(graph.relationships, [])

    def test_broken_concept_link_keeps_dangling_target_without_node(self):
        graph = self.parse_files(
            {"ada.md": concept("Person", "[Future](future/Concept.md)\n")}
        )

        self.assertEqual(graph.relationships[0].target, "future/Concept")
        self.assertNotIn("future/Concept", graph.nodes)
        serialized = graph_to_data(graph)
        self.assertFalse(serialized["relationships"][0]["resolved"])

    def test_external_and_empty_links_have_no_pgm_relationship(self):
        graph = self.parse_files(
            {
                "note.md": concept(
                    "Note",
                    "[web](https://example.com)\n"
                    "[mail](mailto:alice@example.com)\n"
                    "[empty]()\n",
                )
            }
        )

        self.assertEqual(graph.relationships, [])

    def test_reference_style_concept_link_is_relationship(self):
        graph = self.parse_files(
            {
                "note.md": concept(
                    "Note",
                    "[Acme][organization]\n\n"
                    '[organization]: Acme.md "{type: works_for}"\n',
                )
            }
        )

        self.assertEqual(graph.relationships[0].type, "works_for")
        self.assertEqual(graph.relationships[0].target, "Acme")

    def test_wikilink_is_not_commonmark_concept_link(self):
        graph = self.parse_files(
            {"note.md": concept("Note", "[[Acme | works_for]]\n")}
        )

        self.assertEqual(graph.relationships, [])

    def test_relationships_with_different_properties_remain_distinct(self):
        graph = self.parse_files(
            {
                "ada.md": concept(
                    "Person",
                    '[London](London.md "{type: visited, year: 1830}")\n'
                    '[London again](London.md "{type: visited, year: 1831}")\n',
                )
            }
        )

        self.assertEqual(len(graph.relationships), 2)
        self.assertEqual(len({relationship.id for relationship in graph.relationships}), 2)
        self.assertEqual(graph_to_cypher(graph).count(":PGM_RELATIONSHIP "), 2)

    def test_bare_and_empty_map_are_distinct_occurrences_with_shared_key(self):
        graph = self.parse_files(
            {
                "ada.md": concept(
                    "Person",
                    "[London](London.md)\n"
                    '[same target](London.md "{}")\n',
                )
            }
        )

        self.assertEqual(len(graph.relationships), 2)
        self.assertEqual(len({relationship.key for relationship in graph.relationships}), 1)
        self.assertEqual(len({relationship.id for relationship in graph.relationships}), 2)

    def test_relationship_fingerprint_is_stable_under_yaml_key_reordering(self):
        first = self.parse_files(
            {
                "ada.md": concept(
                    "Person",
                    '[London](London.md "{type: born_in, year: 1815, source: register}")\n',
                )
            }
        )
        second = self.parse_files(
            {
                "ada.md": concept(
                    "Person",
                    '[London](London.md "{source: register, year: 1815, type: born_in}")\n',
                )
            }
        )

        self.assertEqual(first.relationships[0].id, second.relationships[0].id)

    def test_cypher_adapter_maps_types_structurally_without_mutating_ast(self):
        graph = self.parse_files(
            {
                "ada.md": concept(
                    "Person",
                    '[London](London.md "{type: born_in, year: 1815}")\n',
                    metadata="name: Ada",
                )
            }
        )

        self.assertEqual(graph.nodes["ada"].properties["type"], "Person")
        self.assertEqual(graph.relationships[0].properties["type"], "born_in")
        cypher = graph_to_cypher(graph)
        self.assertIn(':PGMConcept {pgm_concept_id:"ada"}', cypher)
        self.assertIn('SET n1.pgm_type = "Person"', cypher)
        self.assertIn("pgm_relationship_id", cypher)
        self.assertIn("pgm_relationship_key", cypher)
        self.assertIn('pgm_type:"born_in"', cypher)
        self.assertIn('\\"pgm-yaml\\"', cypher)

    def test_cypher_json_preserves_nested_values_null_and_authored_id(self):
        graph = self.parse_files(
            {
                "note.md": concept(
                    "Note",
                    metadata=(
                        "id: authored-id\n"
                        "payload: {items: [1, text, null, {active: true}]}"
                    ),
                )
            }
        )

        encoded = canonical_json(graph.nodes["note"].properties)
        decoded = json.loads(encoded)
        self.assertEqual(decoded, canonical_document(graph.nodes["note"].properties))
        self.assertIn('["string","authored-id"]', encoded)
        self.assertIn('["string","active"]', encoded)

        cypher = graph_to_cypher(graph)
        self.assertIn('{pgm_concept_id:"note"}', cypher)
        self.assertIn('\\"string\\",\\"id\\"', cypher)
        self.assertIn('\\"string\\",\\"authored-id\\"', cypher)
        self.assertNotIn('{id:"note"}', cypher)

    def test_cypher_generic_relationship_type_supports_untyped_relationship(self):
        graph = self.parse_files(
            {"ada.md": concept("Person", "[London](London.md)\n")}
        )

        cypher = graph_to_cypher(graph)
        self.assertIn(":PGM_RELATIONSHIP", cypher)
        self.assertNotIn("pgm_type:", cypher)

    def test_create_and_merge_export_modes(self):
        graph = self.parse_files(
            {
                "ada.md": concept(
                    "Person", '[London](London.md "{type: born_in, year: 1815}")\n'
                )
            }
        )

        self.assertIn("CREATE (", graph_to_cypher(graph))
        self.assertIn(":PGM_RELATIONSHIP ", graph_to_cypher(graph))
        self.assertIn(
            "MERGE (",
            graph_to_cypher(graph, relationship_mode="merge"),
        )
        self.assertIn("pgm_relationship_id", graph_to_cypher(graph, "merge"))
        with self.assertRaisesRegex(ValueError, "relationship mode"):
            graph_to_cypher(graph, relationship_mode="replace")

    def test_frontmatter_links_are_not_scanned_as_markdown(self):
        graph = self.parse_files(
            {
                "a.md": concept(
                    "Note", metadata='description: "[not a link](b.md)"'
                )
            }
        )

        self.assertEqual(graph.relationships, [])

    def test_examples_match_expected_cypher(self):
        graph = parse_corpus(ROOT / "examples")
        expected = (ROOT / "examples" / "expected.cypher").read_text(
            encoding="utf-8"
        ).strip()
        expected_merge = (ROOT / "examples" / "expected-merge.cypher").read_text(
            encoding="utf-8"
        ).strip()

        self.assertEqual(graph.warnings, [])
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph_to_cypher(graph), expected)
        self.assertEqual(
            graph_to_cypher(graph, relationship_mode="merge"), expected_merge
        )


if __name__ == "__main__":
    unittest.main()
