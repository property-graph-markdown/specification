"""Executable runner for the language-neutral PGM Core TCK manifest."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
sys.path.insert(0, str(ROOT / "parser"))

from pgmark import Graph, parse_corpus  # noqa: E402


def _load_manifest() -> dict[str, Any]:
    parser = YAML(typ="safe", pure=True)
    parser.version = (1, 2)
    with (TESTS / "core.yaml").open(encoding="utf-8") as source:
        manifest = parser.load(source)
    if not isinstance(manifest, dict):
        raise TypeError("Core TCK manifest must be a mapping")
    return manifest


def _load_schema() -> dict[str, Any]:
    with (TESTS / "tck.schema.json").open(encoding="utf-8") as source:
        schema = json.load(source)
    if not isinstance(schema, dict):
        raise TypeError("Core TCK schema must be an object")
    return schema


def _project_core_result(graph: Graph) -> dict[str, Any]:
    """Project implementation objects to the normative PGM Core shape."""

    nodes = [
        {
            "id": node.id,
            "type": node.type,
            "properties": node.properties,
        }
        for _, node in sorted(graph.nodes.items())
    ]
    relationships = [
        {
            "source": relationship.source,
            "target": relationship.target,
            "resolved": relationship.target in graph.nodes,
            "type": relationship.type,
            "properties": relationship.properties,
        }
        for relationship in graph.relationships
    ]
    return {
        "nodes": nodes,
        "relationships": relationships,
    }


def _write_bundle(root: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe TCK file path: {name!r}")
        destination = root.joinpath(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")


class CoreTCKTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = _load_manifest()
        cls.schema = _load_schema()

    def test_manifest_schema_is_valid(self) -> None:
        Draft202012Validator.check_schema(self.schema)

    def test_manifest_conforms_to_schema(self) -> None:
        errors = sorted(
            Draft202012Validator(self.schema).iter_errors(self.manifest),
            key=lambda error: list(error.absolute_path),
        )
        rendered = "\n".join(
            f"{list(error.absolute_path)}: {error.message}" for error in errors
        )
        self.assertEqual(errors, [], rendered)

        identifiers = [case["id"] for case in self.manifest["cases"]]
        self.assertEqual(len(identifiers), len(set(identifiers)), "case IDs must be unique")

    def test_all_core_cases(self) -> None:
        for case in self.manifest["cases"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                _write_bundle(root, case["files"])
                graph = parse_corpus(root)
                expected = case["expect"]

                if not expected["conforms"]:
                    self.assertTrue(
                        graph.errors,
                        "a non-conforming Core Bundle must produce at least one error",
                    )
                    continue

                self.assertFalse(
                    graph.errors,
                    "a conforming Core Bundle must not produce an error: "
                    + "; ".join(graph.errors),
                )
                actual = _project_core_result(graph)
                # Core defines graph membership and preserves multiplicity, but
                # does not prescribe an API serialization order.
                self.assertCountEqual(actual["nodes"], expected["nodes"])
                self.assertCountEqual(
                    actual["relationships"], expected["relationships"]
                )


if __name__ == "__main__":
    unittest.main()
