# PGM Reference Parser

`pgmark.py` is the small Python reference parser for Property Graph Markdown 0.3.0.

It:

1. Recursively scans Markdown files.
2. Excludes YAML Front Matter from graph extraction.
3. Parses ordinary CommonMark inline links.
4. Recognizes link text matching `:CLASS {properties}`.
5. Applies empty-destination annotations to the current node.
6. Creates outgoing relationships for non-empty destinations.
7. Derives canonical semantic fingerprints and coalesces duplicates.
8. Validates cumulative node properties.
9. Emits openCypher-compatible statements.

## Install

```sh
python -m pip install -r parser/requirements.txt
```

The parser uses `markdown-it-py` for CommonMark links and prefers PyYAML for flow mappings. A compact fallback covers the core flow-mapping subset when PyYAML is unavailable.

## Usage

```sh
python parser/pgmark.py parse examples --cypher
```

This emits a `CREATE` snapshot for an empty relationship target. For idempotent natural-key relationships:

```sh
python parser/pgmark.py parse examples --cypher --relationship-mode merge
```

Warnings describe malformed annotation attempts. Conflicting node properties are validation errors; the CLI exits with status 1 and does not emit Cypher for an invalid graph.

## Library Usage

```python
from pathlib import Path
import sys

sys.path.insert(0, str(Path("parser")))
from pgmark import graph_to_cypher, parse_corpus

graph = parse_corpus("examples")
print(graph_to_cypher(graph))
print(graph_to_cypher(graph, relationship_mode="merge"))
```

Each parsed `Node` contains its labels, properties, and outgoing relationships. Each `Relationship` has an internal SHA-256 fingerprint derived from source, type, target, and canonical properties. This fingerprint is not PGM syntax or an authored graph property. `Graph.relationships` provides a flattened view.

## Scope

This is a readable reference implementation, not a full Markdown framework. YAML Front Matter may remain in source documents, but the parser intentionally ignores it for graph semantics.
