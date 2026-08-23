import datetime
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "parser"))

import canonical  # noqa: E402
from canonical import canonical_value  # noqa: E402
from pgmark import main, parse_corpus, resolve_destination  # noqa: E402


def concept(body: str = "", metadata: str = "") -> str:
    extra = f"{metadata}\n" if metadata else ""
    return f"---\ntype: Note\n{extra}---\n\n{body}"


class ConstantHash:
    def __init__(self, _value: bytes = b"") -> None:
        pass

    def hexdigest(self) -> str:
        return "0" * 64

    def digest(self) -> bytes:
        return b"\0" * 32


class EdgeCaseTests(unittest.TestCase):
    def parse_files(self, files: dict[str, str | bytes]):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, bytes):
                    path.write_bytes(content)
                else:
                    path.write_text(content, encoding="utf-8")
            return parse_corpus(root)

    def test_only_ascii_yaml_separation_characters_enable_title_metadata(self):
        graph = self.parse_files(
            {
                "source.md": concept(
                    '[ascii](target.md "  {type: relates}  ")\n'
                    '[nbsp](target.md "&nbsp;{type: hidden}&nbsp;")\n'
                )
            }
        )

        self.assertEqual(graph.relationships[0].type, "relates")
        self.assertEqual(graph.relationships[1].title, "\u00a0{type: hidden}\u00a0")
        self.assertIsNone(graph.relationships[1].type)
        self.assertEqual(graph.relationships[1].properties, {})
        self.assertEqual(graph.warnings, [])

    def test_reserved_document_minimum_structure_matches_pinned_okf(self):
        empty_index = self.parse_files({"index.md": ""})
        plain_index = self.parse_files({"index.md": "plain text\n"})
        heading_index = self.parse_files({"index.md": "# Concepts\n"})
        empty_log = self.parse_files({"log.md": ""})
        nbsp_log = self.parse_files(
            {"log.md": "# Log\n\n## \u00a02026-01-01\u00a0\n- Update\n"}
        )

        self.assertEqual(empty_index.diagnostics[0].code, "OKF_INDEX_SECTION_REQUIRED")
        self.assertEqual(plain_index.diagnostics[0].code, "OKF_INDEX_SECTION_REQUIRED")
        self.assertEqual(heading_index.errors, [])
        self.assertEqual(empty_log.errors, [])
        self.assertEqual(nbsp_log.diagnostics[0].code, "OKF_LOG_DATE_HEADING_INVALID")

    def test_markdown_directory_is_not_opened_as_a_file(self):
        graph = self.parse_files(
            {"group.md/note.md": concept(), "ordinary.md": concept()}
        )

        self.assertEqual(set(graph.nodes), {"group.md/note", "ordinary"})
        self.assertEqual(graph.errors, [])

    def test_invalid_input_paths_and_utf8_are_diagnostics_not_tracebacks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing = root / "missing"
            non_markdown = root / "data.txt"
            non_markdown.write_text("data", encoding="utf-8")

            self.assertEqual(parse_corpus(missing).diagnostics[0].code, "PGM_INPUT_NOT_FOUND")
            self.assertEqual(
                parse_corpus(non_markdown).diagnostics[0].code,
                "PGM_INPUT_NOT_MARKDOWN",
            )
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(main(["validate", str(missing)]), 2)
                self.assertEqual(main(["validate", str(non_markdown)]), 2)
            self.assertIn("PGM_INPUT_NOT_FOUND", stderr.getvalue())
            self.assertIn("PGM_INPUT_NOT_MARKDOWN", stderr.getvalue())

        invalid_utf8 = self.parse_files({"bad.md": b"\xff\xfe"})
        self.assertEqual(invalid_utf8.diagnostics[0].code, "OKF_MARKDOWN_UTF8_INVALID")

    def test_cr_line_endings_and_one_initial_utf8_bom_are_accepted(self):
        graph = self.parse_files(
            {"note.md": "\ufeff---\rtype: Note\r---\r\r# Note\r"}
        )

        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.nodes["note"].type, "Note")

    def test_destination_controls_are_rejected_and_empty_segments_collapse(self):
        for destination in ("\0target.md", "tar\tget.md", " target.md", "target.md\x7f"):
            with self.subTest(destination=repr(destination)):
                with self.assertRaises(ValueError):
                    resolve_destination(destination, "source")

        self.assertEqual(resolve_destination("a//b.md", "source"), "a/b")
        self.assertEqual(resolve_destination("Ada%20Lovelace.md", "source"), "Ada Lovelace")

    def test_timestamp_range_and_precision_are_contextual(self):
        long_fraction = self.parse_files(
            {
                "bad.md": concept(
                    metadata="at: !!timestamp 2026-08-23T10:30:00.1234567Z"
                )
            }
        )
        overflow = self.parse_files(
            {
                "bad.md": concept(
                    metadata="at: !!timestamp 0001-01-01T00:00:00+14:00"
                )
            }
        )
        title = self.parse_files(
            {
                "source.md": concept(
                    '[target](target.md "{at: !!timestamp 0001-01-01T00:00:00+14:00}")\n'
                )
            }
        )

        self.assertEqual(long_fraction.diagnostics[0].code, "PGM_YAML_VALUE_UNSUPPORTED")
        self.assertEqual(overflow.diagnostics[0].code, "PGM_YAML_VALUE_UNSUPPORTED")
        self.assertEqual(title.errors, [])
        self.assertEqual(title.relationships[0].properties, {})
        self.assertEqual(title.diagnostics[0].severity, "warning")
        self.assertEqual(
            canonical_value(datetime.datetime(1, 1, 1)),
            ["timestamp", "0001-01-01T00:00:00"],
        )

    def test_yaml_sets_require_null_values_and_unique_pgm_identity(self):
        non_null = self.parse_files(
            {"bad.md": concept(metadata="values: !!set {a: value}")}
        )
        duplicate_set = self.parse_files(
            {"bad.md": concept(metadata="values: !!set {1, 1.0}")}
        )
        duplicate_map = self.parse_files(
            {"bad.md": concept(metadata="values: {1: integer, 1.0: float}")}
        )

        self.assertEqual(non_null.diagnostics[0].code, "PGM_YAML_INVALID")
        self.assertEqual(duplicate_set.diagnostics[0].code, "PGM_YAML_INVALID")
        self.assertEqual(duplicate_map.diagnostics[0].code, "PGM_YAML_INVALID")

    def test_detected_relationship_hash_collisions_are_core_errors(self):
        with patch.object(canonical.hashlib, "sha256", ConstantHash):
            graph = self.parse_files(
                {"source.md": concept("[a](a.md)\n[b](b.md)\n")}
            )

        self.assertEqual(len(graph.relationships), 2)
        self.assertEqual([item.occurrence for item in graph.relationships], [0, 0])
        self.assertEqual(
            {diagnostic.code for diagnostic in graph.diagnostics},
            {"PGM_RELATIONSHIP_KEY_COLLISION", "PGM_RELATIONSHIP_ID_COLLISION"},
        )


if __name__ == "__main__":
    unittest.main()
