import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "parser" / "pgmark.py"
DEMO = ROOT / "demo"
BUNDLE = DEMO / "bundle"

SNAPSHOTS = (
    ("expected.graph.json", ("--format", "json")),
    ("expected.cypher", ("--format", "cypher")),
    (
        "expected-merge.cypher",
        ("--format", "cypher", "--relationship-mode", "merge"),
    ),
)


def run_cli(
    command: str, path: Path, *arguments: str
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            command,
            str(path),
            *arguments,
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_demo(command: str, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return run_cli(command, BUNDLE, *arguments)


class DemoTests(unittest.TestCase):
    def test_demo_bundle_is_valid(self):
        result = run_demo("validate")
        self.assertEqual(
            result.returncode,
            0,
            result.stderr.decode("utf-8", errors="replace"),
        )
        self.assertEqual(result.stderr, b"")
        self.assertEqual(
            result.stdout,
            b"PGM Core Bundle conforms to 0.4.0 Public Draft: "
            b"2 nodes, 8 relationships, 0 warnings\n",
        )

    def test_demo_export_snapshots_are_byte_exact(self):
        for snapshot_name, arguments in SNAPSHOTS:
            with self.subTest(snapshot=snapshot_name):
                result = run_demo("parse", *arguments)
                self.assertEqual(
                    result.returncode,
                    0,
                    result.stderr.decode("utf-8", errors="replace"),
                )
                self.assertEqual(result.stderr, b"")
                self.assertEqual(
                    result.stdout,
                    (DEMO / snapshot_name).read_bytes(),
                )

    def test_demo_json_import_reexports_byte_exact(self):
        snapshot = DEMO / "expected.graph.json"
        result = run_cli("import-json", snapshot, "--format", "json")
        self.assertEqual(
            result.returncode,
            0,
            result.stderr.decode("utf-8", errors="replace"),
        )
        self.assertEqual(result.stderr, b"")
        self.assertEqual(result.stdout, snapshot.read_bytes())


if __name__ == "__main__":
    unittest.main()
