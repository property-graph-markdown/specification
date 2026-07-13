# Roadmap

## PGM 0.3.0

PGM 0.3.0 defines the smallest useful core:

- Core specification
- Reference parser
- Obsidian plugin

The 0.3.0 goal is interoperability around one classified CommonMark link construct, not feature breadth.

## Future Ideas

The following ideas are intentionally excluded from version 0.3.0:

- namespaces
- ontology validation
- RDF export
- embedded graph queries
- inference rules

These may be explored after the core syntax and information model have proven stable.

## Non-Goals for 0.3.0

PGM 0.3.0 does not define:

- a Markdown replacement
- a graph database
- a query language
- a custom renderer
- a schema language
- an ontology language
- a synchronization protocol

PGM 0.3.0 only defines how classified CommonMark inline links make a CommonMark corpus interpretable as an openCypher-compatible Property Graph.
