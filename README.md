# Property Graph Markdown

**Property Graph Markdown (PGM)** is an open, vendor-neutral proposal for representing openCypher-compatible Property Graphs in CommonMark.

Markdown is evolving from a documentation language into a knowledge representation language for hybrid human-AI systems.

Markdown is already the de facto format for software documentation, knowledge bases, AI agent memory, RAG corpora, and human-maintained notes. It is human-readable, machine-readable, portable, version-control friendly, and token-efficient.

Property Graphs add something Markdown does not have by itself: explicit relationship types, direction, and optional relationship properties. PGM combines these strengths with the smallest possible extension to CommonMark.

PGM is not a Markdown replacement. Every PGM document is still valid CommonMark.

## One-Page Explanation

PGM interprets an ordinary Markdown corpus as a Property Graph:

1. One Markdown file is one graph node.
2. YAML frontmatter defines node labels and node properties.
3. Ordinary CommonMark links define outgoing relationships when their visible label is a relationship descriptor.
4. A relationship descriptor is `:` plus a relationship type and an optional YAML flow mapping.
5. The link destination is canonical and identifies the target node.

That is the whole core language.

PGM 0.1.2 intentionally defines only outgoing relationships. A relationship is authored once, in the Markdown file representing its source node. This prevents conflicting definitions of the same edge across two files.

```markdown
---
labels: [Invoice, Document]
status: approved
amount: 1532
currency: CHF
---
# Invoice 2026-001

[:approvedBy {date: 2026-06-26}](Peter%20Meier.md)
[:partOf](Project%20Apollo.md)
```

The document remains Markdown. Existing editors, renderers, search tools, diff tools, and static site generators continue to work.

## Generated Graph

```mermaid
graph LR
    invoice["Invoice 2026-001.md<br/>:Invoice :Document"]
    peter["Peter Meier.md"]
    project["Project Apollo.md"]
    invoice -- "approvedBy {date: 2026-06-26}" --> peter
    invoice -- "partOf" --> project
```

## Generated openCypher

```cypher
MERGE (n:Invoice:Document {id:"Invoice 2026-001.md"})
SET
    n.status = "approved",
    n.amount = 1532,
    n.currency = "CHF"
MERGE (p {id:"Peter Meier.md"})
MERGE (n)-[:approvedBy {
    date: date("2026-06-26")
}]->(p)
MERGE (q {id:"Project Apollo.md"})
MERGE (n)-[:partOf]->(q)
```

## Installation

Clone the repository and install the reference parser dependencies:

```sh
git clone https://github.com/property-graph-markdown/specification.git
cd specification
python -m pip install -r parser/requirements.txt
```

The parser is intentionally small. If `PyYAML` is unavailable, it falls back to a minimal YAML subset for the core examples.

## Parser Usage

Generate openCypher from a Markdown directory:

```sh
python parser/pgmark.py parse examples --cypher
```

Run the tests:

```sh
python -m unittest discover -s tests
```

Use the parser as a library:

```python
from parser.pgmark import parse_corpus, graph_to_cypher

graph = parse_corpus("examples")
print(graph_to_cypher(graph))
```

## Project Layout

```text
SPEC.md              Normative 0.1.2 draft specification
RATIONALE.md         Design rationale
GRAMMAR.ebnf         Minimal relationship-label grammar
examples/            Small coherent Invoice-Person-Project graph
parser/              Python reference parser
tests/               Parser tests and core cases
obsidian-plugin/     Minimal Obsidian editor integration
```

## Roadmap

PGM 0.1.2 focuses only on the smallest useful core:

- Core specification
- Reference parser
- Obsidian plugin

Future ideas such as namespaces, ontology validation, RDF export, embedded graph queries, and inference rules are intentionally excluded from 0.1.2. They can be explored only after the core remains simple, interoperable, and obvious.

## Guiding Principle

Introduce the smallest possible extension to CommonMark that enables Markdown corpora to be interpreted as openCypher-compatible Property Graphs.
