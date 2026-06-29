# PGM Reference Parser

`pgmark.py` is the small Python reference parser for Property Graph Markdown 0.1.1.

It performs four steps:

1. Recursively scans Markdown files.
2. Parses YAML frontmatter into node labels and node properties.
3. Extracts CommonMark links whose visible label is a relationship descriptor.
4. Emits openCypher-compatible statements.

## Install

```sh
python -m pip install -r parser/requirements.txt
```

`PyYAML` is recommended. If it is unavailable, the parser uses a small fallback parser for the core YAML subset used in the examples and tests.

## Usage

```sh
python parser/pgmark.py parse examples --cypher
```

## Library Usage

```python
from pathlib import Path
import sys

sys.path.insert(0, str(Path("parser")))
from pgmark import graph_to_cypher, parse_corpus

graph = parse_corpus("examples")
print(graph_to_cypher(graph))
```

## Scope

This parser is a reference implementation, not a full Markdown application framework. It is intentionally readable and small so the specification can be understood through code.
