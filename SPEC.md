# Property Graph Markdown (PGM) 0.1.2 Public Draft

## Status

This document defines Property Graph Markdown (PGM) version 0.1.2 Public Draft.

PGM is an open, vendor-neutral specification for representing openCypher-compatible Property Graphs in CommonMark.

The key words `SHALL`, `SHOULD`, and `MAY` are to be interpreted as described in RFC 2119.

## Motivation

Markdown is evolving from a documentation language into a knowledge representation language for hybrid human-AI systems.

Markdown has become the de facto standard for software documentation, knowledge bases, AI agent memory, RAG corpora, and human-maintained knowledge. It is human-readable, machine-readable, portable, version-control friendly, and token-efficient.

Property Graphs enrich knowledge by assigning explicit types, direction, and optional properties to relationships. Combining Markdown with Property Graph semantics creates an enriched source of truth for AI agents while preserving human readability.

## Design Principles

1. Every PGM document SHALL remain valid CommonMark.
2. The information model SHALL map directly to the openCypher Property Graph model.
3. The language extension SHALL be minimal.
4. Existing Markdown tooling SHALL continue to work unchanged.
5. Human readability SHOULD be preferred over compact syntax.
6. Every additional grammar rule SHOULD be justified.
7. Existing standards SHOULD be reused wherever possible.
8. Each relationship SHOULD have exactly one authoritative source in the corpus.

## Abstract Information Model

A PGM corpus is a set of Markdown documents interpreted as a Property Graph.

The graph consists of:

- nodes
- node labels
- node properties
- directed relationships
- relationship types
- relationship properties

The information model is compatible with the openCypher Property Graph model.

## Node Representation

One Markdown file SHALL represent one graph node.

The node identifier SHALL be the canonical path of the Markdown file within the corpus.

If a Markdown file begins with YAML frontmatter, the frontmatter MAY define node labels and node properties.

The reserved frontmatter property `labels` SHALL define node labels. Its value SHALL be a string or a sequence of strings.

All other frontmatter properties SHALL be interpreted as node properties.

Example:

```markdown
---
labels: [Invoice, Document]
status: approved
amount: 1532
currency: CHF
---
```

This represents one node with labels `Invoice` and `Document` and properties `status`, `amount`, and `currency`.

## Relationship Representation

A CommonMark hyperlink whose visible label is a relationship descriptor SHALL be interpreted as a semantic relationship.

The hyperlink destination SHALL define the related node identifier.

The visible link label SHALL define the relationship descriptor. The relationship descriptor SHALL contain the relationship type and MAY contain relationship properties.

PGM 0.1.2 only defines outgoing relationships. The relationship SHALL be authored in the Markdown file that represents the source node.

Example:

```markdown
[:approvedBy](Peter%20Meier.md)
```

This defines an outgoing relationship of type `approvedBy` from the current document node to `Peter Meier.md`.

PGM 0.1.2 does not define direction-marker syntax. A label containing `->` or `<-` SHALL NOT create a PGM relationship.

This restriction avoids redundant syntax and duplicate or conflicting definitions of the same relationship across two Markdown files.

## Relationship Grammar

The semantic hyperlink label grammar is:

```ebnf
SemanticRelationshipLabel ::=
    RelationshipDescriptor

RelationshipDescriptor ::=
    ":" RelationshipType PropertyMap?

RelationshipType ::= Identifier

Identifier ::= Letter (Letter | Digit | "_")*

PropertyMap ::= YAMLFlowMapping
```

Relationship types SHALL be case-sensitive. Uppercase relationship types MAY be used by convention, but are not required by this specification.

`PropertyMap` SHALL be a YAML 1.2 flow mapping.

Example:

```markdown
[:approvedBy {date: 2026-06-26}](Peter%20Meier.md)
```

The relationship type is `approvedBy`. The relationship property map contains `date: 2026-06-26`. The relationship target is `Peter Meier.md`.

## Processing Model

A conforming processor SHALL:

1. Traverse a corpus of Markdown documents.
2. Create one node for each Markdown document.
3. Parse YAML frontmatter, when present.
4. Assign node labels from the reserved `labels` property.
5. Assign all other frontmatter entries as node properties.
6. Parse CommonMark hyperlinks.
7. Treat only hyperlinks whose visible label is a relationship descriptor as semantic relationships.
8. Parse semantic relationship labels according to the grammar.
9. Resolve hyperlink destinations to canonical node identifiers.
10. Emit, store, or expose an openCypher-compatible Property Graph.

A conforming processor SHOULD ignore ordinary hyperlinks.

A conforming processor SHOULD report relationship labels that use `->` or `<-` as non-conforming without creating a relationship.

A conforming processor SHOULD report malformed semantic relationships without rejecting the entire document.

## Compatibility

PGM documents SHALL be valid CommonMark documents.

PGM does not define new block syntax, inline syntax, HTML extensions, fenced directives, or renderer behavior.

A Markdown renderer that does not understand PGM SHALL still render PGM documents as ordinary Markdown.

## Conformance

A document conforms to PGM 0.1.2 if:

- it is valid CommonMark;
- any node metadata intended for PGM is encoded as YAML frontmatter;
- any semantic relationship labels follow the grammar in this specification.

A processor conforms to PGM 0.1.2 if it implements the processing model above and preserves the semantics defined by the abstract information model.

Extensions MAY be implemented, but they SHALL NOT change the meaning of conforming PGM 0.1.2 documents.
