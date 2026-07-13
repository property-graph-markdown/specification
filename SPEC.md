# Property Graph Markdown (PGM) 0.3.0 Public Draft

## Status

This document defines Property Graph Markdown (PGM) version 0.3.0 Public Draft.

PGM is an open, vendor-neutral specification for representing openCypher-compatible Property Graphs in CommonMark.

The key words `SHALL`, `SHOULD`, and `MAY` are to be interpreted as described in RFC 2119.

## Motivation

Markdown is evolving from a documentation language into a knowledge representation language for hybrid human-AI systems.

Markdown has become the de facto standard for software documentation, knowledge bases, AI agent memory, RAG corpora, and human-maintained knowledge. It is human-readable, machine-readable, portable, version-control friendly, and token-efficient.

Property Graphs enrich knowledge by assigning labels and properties to nodes and explicit types, direction, and optional properties to relationships. Combining Markdown with Property Graph semantics creates an enriched source of truth for AI agents while preserving human readability.

## Design Principles

1. Every PGM document SHALL remain valid CommonMark.
2. The information model SHALL map directly to the openCypher Property Graph model.
3. The language extension SHALL be minimal.
4. Existing Markdown tooling SHALL continue to work unchanged.
5. Human readability SHOULD be preferred over compact syntax.
6. Every additional grammar rule SHOULD be justified.
7. Existing standards SHOULD be reused wherever possible.
8. Each relationship SHOULD have exactly one authoritative source in the corpus.
9. Node and relationship semantics SHALL use one annotation construct.

## Abstract Information Model

A PGM corpus is a set of Markdown documents interpreted as a Property Graph.

The graph consists of nodes with identifiers, labels, and properties, and directed relationships with types, source nodes, target nodes, and properties.

One Markdown document represents one node. A classified CommonMark inline link represents either an annotation of that node or an outgoing relationship, depending only on whether the parsed link destination is empty.

## Classified Links

A processor SHALL first parse a document as CommonMark. It SHALL NOT replace, fork, or redefine CommonMark link parsing.

A successfully parsed CommonMark inline link is a PGM classified link only when its link text matches `ClassExpression`:

```ebnf
ClassExpression ::= ":" ClassName (Whitespace PropertyMap)?

ClassName ::= Identifier

Identifier ::= Letter (Letter | Digit | "_")*

PropertyMap ::= YAMLFlowMapping
```

`PropertyMap` delegates to YAML 1.2 Flow Mapping. Its keys SHALL be strings. Its values MAY be strings, numbers, booleans, null, lists of supported values, or other scalar value types supported by the processor's openCypher mapping.

Class names are case-sensitive. Uppercase names MAY be used by convention but are not required. PGM 0.3.0 reserves no class name, including `LABEL`.

Links whose text does not match `ClassExpression` SHALL remain ordinary Markdown links, whether their destination is empty or non-empty.

## Node Representation

One Markdown file SHALL represent one graph node.

The node identifier SHALL be the canonical path of the Markdown file within the corpus.

A classified link with an empty destination SHALL annotate the node represented by the current document.

```markdown
[:Person {name: "Ada Lovelace", born: 1815}]()
[:Mathematician]()
```

The class name SHALL be added to the node's label set. The optional property map SHALL add properties to the node itself, not to a label assignment.

Multiple node annotations are cumulative. Repeated labels SHALL be deduplicated. Repeated declarations of a node property with equivalent values SHALL be accepted. Conflicting values for the same node property key SHALL produce a validation error; processors SHALL NOT silently apply last-declaration-wins semantics.

CommonMark parses both of the following as links with an empty destination:

```markdown
[:Person]()
[:Person](<>)
```

Processors SHALL normalize both forms to the same node annotation semantics. The first form is canonical for PGM serialization and examples.

## YAML Front Matter

PGM does not assign graph semantics to YAML Front Matter. Graph semantics are expressed exclusively using classified CommonMark links.

A processor SHALL NOT derive node labels or node properties from Front Matter fields such as `labels`, `properties`, or any other metadata key. Front Matter MAY remain in a document for use by Markdown tools and document-management systems.

The complete PGM graph semantics of a document SHALL be recoverable without parsing its Front Matter.

## Relationship Representation

A classified link with a non-empty destination SHALL declare one outgoing relationship from the current document node to the node identified by the destination.

```markdown
[:BORN_IN {year: 1815}](London.md)
```

The class name SHALL be the relationship type. The optional property map SHALL belong to that relationship instance.

PGM 0.3.0 defines only outgoing relationships. The current document is the source and the link destination is the target. A relationship SHALL be authored in the document representing its source node. PGM does not define `->` or `<-` direction markers.

For file destinations without a URI scheme, processors SHALL resolve relative destinations against the directory of the source Markdown document before canonicalization. URI destinations MAY be retained as external node identifiers.

Two relationships with the same source, type, and target but different property maps SHALL remain distinct relationships.

## Semantic Relationship Key

The semantic key of a relationship SHALL be the tuple:

```text
(source, type, target, canonical(properties))
```

Property maps SHALL be canonicalized for key comparison by sorting mapping keys lexicographically, preserving list order, and preserving scalar values. Numerically equivalent integer and floating-point values SHALL compare as equivalent; booleans SHALL remain distinct from numbers. YAML presentation details such as whitespace, quoting style, and mapping-key order SHALL NOT affect the semantic key.

Two classified links with the same semantic relationship key SHALL denote the same relationship and SHALL be coalesced by a processor. This permits idempotent natural-key matching while preserving relationships whose properties differ.

PGM defines no syntax for a technical or database relationship identifier. Physical relationship identity SHALL be delegated to the target graph implementation.

A processor MAY derive a deterministic fingerprint from the semantic key for indexing, diagnostics, or intermediate models. Such a fingerprint is a processing detail; it SHALL NOT be added to the authored relationship property map or required in a PGM document.

## openCypher Export

A snapshot serializer MAY emit relationships using `CREATE`:

```cypher
CREATE (source)-[:BORN_IN {year: 1815}]->(target)
```

This mode assumes that the target contains no relationships from the imported snapshot. `CREATE` is deterministic under that precondition, but it is not idempotent when the same script is rerun against an already populated graph.

A natural-key serializer MAY instead emit the complete semantic key using `MERGE`:

```cypher
MERGE (source)-[:BORN_IN {year: 1815}]->(target)
```

When the target adapter uses source and target nodes, relationship type, and the complete canonical property map as its match key, repeated execution of the same export is idempotent. Relationships with different property maps remain distinct.

A database adapter MAY materialize the semantic fingerprint as technical database metadata when exact property-set matching or database constraints require it. Such metadata belongs to the adapter and is not PGM syntax or an authored relationship property.

Natural-key `MERGE` does not remove relationships that disappeared from a later corpus version. Full synchronization and stale-relationship deletion are database integration concerns outside PGM core.

## Processing Model

A conforming processor SHALL:

1. Traverse a corpus of Markdown documents.
2. Create one node for each Markdown document.
3. Exclude YAML Front Matter from graph extraction without interpreting its fields.
4. Parse the remaining document as CommonMark.
5. Inspect successfully parsed inline links.
6. Treat only links whose link text matches `ClassExpression` as classified links.
7. Normalize `()` and `(<>)` as empty destinations.
8. Apply empty-destination annotations to the current node.
9. Resolve non-empty destinations to canonical node identifiers.
10. Derive the semantic relationship key for each non-empty-destination annotation.
11. Coalesce annotations with equivalent semantic relationship keys.
12. Validate cumulative node property declarations.
13. Emit, store, or expose an openCypher-compatible Property Graph.

A processor SHOULD report malformed link text beginning with `:` as a non-conforming annotation without rejecting unrelated document content.

A processor SHALL report conflicting node property declarations as validation errors and SHALL NOT serialize the graph as valid until those conflicts are resolved.

## Compatibility

PGM documents SHALL be valid CommonMark documents.

PGM core defines no new block syntax, inline syntax, HTML extensions, fenced directives, or renderer behavior. A Markdown renderer that does not understand PGM SHALL render classified links as ordinary links.

Front Matter compatibility is non-semantic: Front Matter may be preserved for other tools, but a PGM processor SHALL ignore it during graph extraction.

Wikilinks are not PGM syntax and SHALL NOT produce graph semantics directly. An editor integration MAY convert a wikilink authoring form to a classified CommonMark link before PGM extraction.

## Migration from 0.2.1

PGM 0.2.1 used YAML Front Matter for node properties and the reserved `:LABEL` annotation for node labels. PGM 0.3.0 replaces both mechanisms with empty-destination classified links.

Previous:

```markdown
---
name: Ada Lovelace
born: 1815
---

[:LABEL](Ontology/Person.md)
[:LABEL](Ontology/Mathematician.md)
```

PGM 0.3.0:

```markdown
[:Person {name: "Ada Lovelace", born: 1815}]()
[:Mathematician]()
```

Previous `:LABEL` annotations SHALL be rewritten using the destination-derived label as the empty-destination class name:

```markdown
[:LABEL](Ontology/Person.md)
```

becomes:

```markdown
[:Person]()
```

Existing relationship annotations of the form `[:TYPE {properties}](target.md)` require no syntax change.

Some earlier prototypes used Front Matter fields named `labels` and `properties`. Those fields likewise have no PGM 0.3.0 graph semantics and SHALL be migrated to empty-destination classified links when they are intended to describe the graph.

## Conformance

A document conforms to PGM 0.3.0 if it is valid CommonMark, every intended graph annotation is a classified CommonMark link, and cumulative node property declarations do not conflict.

A processor conforms to PGM 0.3.0 if it implements the processing model and preserves semantic relationship keys.

Extensions MAY be implemented, but they SHALL NOT change the meaning of conforming PGM 0.3.0 documents.
