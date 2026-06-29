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
                "alice.md": "---\nlabels: [Person]\n---\n[KNOWS](bob.md)\n",
                "bob.md": "---\nlabels: [Person]\n---\n# Bob\n",
            }
        )

        self.assertEqual(len(graph.relationships), 1)
        rel = graph.relationships[0]
        self.assertEqual(rel.source, "alice.md")
        self.assertEqual(rel.target, "bob.md")
        self.assertEqual(rel.type, "KNOWS")

    def test_direction_marker_warns_and_skips(self):
        graph = self.parse_files(
            {
                "invoice.md": "---\nlabels: [Invoice]\n---\n# Invoice\n",
                "peter.md": "---\nlabels: [Person]\n---\n[APPROVED_BY -> Invoice](invoice.md)\n",
            }
        )

        self.assertEqual(graph.relationships, [])
        self.assertEqual(len(graph.warnings), 1)
        self.assertIn("direction markers are not supported", graph.warnings[0])

    def test_relationship_properties(self):
        graph = self.parse_files(
            {
                "invoice.md": (
                    "---\nlabels: [Invoice]\n---\n"
                    "[APPROVED_BY {date: 2026-06-26, confidence: 0.98}](peter.md)\n"
                ),
                "peter.md": "---\nlabels: [Person]\n---\n# Peter\n",
            }
        )

        rel = graph.relationships[0]
        self.assertEqual(rel.properties["date"], "2026-06-26")
        self.assertEqual(rel.properties["confidence"], 0.98)

        cypher = graph_to_cypher(graph)
        self.assertIn('date: date("2026-06-26")', cypher)
        self.assertIn("confidence: 0.98", cypher)

    def test_ordinary_hyperlinks_are_ignored(self):
        graph = self.parse_files(
            {
                "note.md": "---\nlabels: [Note]\n---\n[Read more](other.md)\n",
                "other.md": "# Other\n",
            }
        )

        self.assertEqual(graph.relationships, [])

    def test_malformed_semantic_relationship_warns_and_skips(self):
        graph = self.parse_files(
            {
                "a.md": "---\nlabels: [Thing]\n---\n[APPROVED_BY {date](b.md)\n",
                "b.md": "# B\n",
            }
        )

        self.assertEqual(graph.relationships, [])
        self.assertEqual(len(graph.warnings), 1)
        self.assertIn("malformed relationship descriptor", graph.warnings[0])


if __name__ == "__main__":
    unittest.main()
