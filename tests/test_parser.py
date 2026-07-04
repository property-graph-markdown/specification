import tempfile
import unittest
from pathlib import Path
import sys


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

    def test_outgoing_relationship(self):
        graph = self.parse_files(
            {
                "alice.md": "[:LABEL](Ontology/Person.md)\n[:knows](bob.md)\n",
                "bob.md": "[:LABEL](Ontology/Person.md)\n# Bob\n",
            }
        )

        self.assertEqual(len(graph.relationships), 1)
        rel = graph.relationships[0]
        self.assertEqual(rel.source, "alice.md")
        self.assertEqual(rel.target, "bob.md")
        self.assertEqual(rel.type, "knows")
        self.assertEqual(graph.nodes["alice.md"].labels, ["Person"])

    def test_label_annotation_does_not_create_relationship(self):
        graph = self.parse_files(
            {
                "ada.md": "[:LABEL](Ontology/Person.md)\n[:LABEL](Ontology/Mathematician.md)\n",
            }
        )

        self.assertEqual(graph.nodes["ada.md"].labels, ["Person", "Mathematician"])
        self.assertEqual(graph.relationships, [])
        self.assertNotIn("Ontology/Person.md", graph.nodes)

    def test_yaml_labels_is_an_ordinary_property(self):
        graph = self.parse_files(
            {
                "note.md": "---\nlabels: [NotGraphLabels]\n---\n# Note\n",
            }
        )

        self.assertEqual(graph.nodes["note.md"].labels, [])
        self.assertEqual(graph.nodes["note.md"].properties["labels"], ["NotGraphLabels"])

    def test_direction_marker_warns_and_skips(self):
        graph = self.parse_files(
            {
                "invoice.md": "# Invoice\n",
                "peter.md": "[:approvedBy -> Invoice](invoice.md)\n",
            }
        )

        self.assertEqual(graph.relationships, [])
        self.assertEqual(len(graph.warnings), 1)
        self.assertIn("direction markers are not supported", graph.warnings[0])

    def test_relationship_properties(self):
        graph = self.parse_files(
            {
                "invoice.md": (
                    "[:LABEL](Ontology/Invoice.md)\n"
                    "[:approvedBy {date: 2026-06-26, confidence: 0.98}](peter.md)\n"
                ),
                "peter.md": "[:LABEL](Ontology/Person.md)\n# Peter\n",
            }
        )

        rel = graph.relationships[0]
        self.assertEqual(rel.type, "approvedBy")
        self.assertEqual(rel.properties["date"], "2026-06-26")
        self.assertEqual(rel.properties["confidence"], 0.98)

        cypher = graph_to_cypher(graph)
        self.assertIn('date: date("2026-06-26")', cypher)
        self.assertIn("confidence: 0.98", cypher)

    def test_ordinary_hyperlinks_are_ignored(self):
        graph = self.parse_files(
            {
                "note.md": "[:LABEL](Ontology/Note.md)\n[Read more](other.md)\n",
                "other.md": "# Other\n",
            }
        )

        self.assertEqual(graph.relationships, [])

    def test_malformed_semantic_relationship_warns_and_skips(self):
        graph = self.parse_files(
            {
                "a.md": "[:LABEL](Ontology/Thing.md)\n[:approvedBy {date](b.md)\n",
                "b.md": "# B\n",
            }
        )

        self.assertEqual(graph.relationships, [])
        self.assertEqual(len(graph.warnings), 1)
        self.assertIn("malformed semantic link label", graph.warnings[0])

    def test_label_annotation_rejects_properties(self):
        graph = self.parse_files(
            {
                "a.md": "[:LABEL {source: manual}](Ontology/Thing.md)\n",
            }
        )

        self.assertEqual(graph.nodes["a.md"].labels, [])
        self.assertEqual(graph.relationships, [])
        self.assertEqual(len(graph.warnings), 1)
        self.assertIn("LABEL annotations must not contain relationship properties", graph.warnings[0])


if __name__ == "__main__":
    unittest.main()
