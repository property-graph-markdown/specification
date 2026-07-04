# Property Graph Markdown (PGM) 0.2.0 Public Draft

## Status

This document defines Property Graph Markdown (PGM) version 0.2.0 Public Draft.

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

If a Markdown file begins with YAML frontmatter, the frontmatter MAY define node properties.

YAML frontmatter SHALL NOT define node labels in PGM core.

All frontmatter properties SHALL be interpreted as node properties. The property name `labels` has no reserved PGM meaning.

Node labels SHALL be declared using the reserved semantic link annotation `:LABEL`.

Example:

```markdown
---
status: approved
amount: 1532
currency: CHF
---

[:LABEL](Ontology/Invoice.md)
[:LABEL](Ontology/Document.md)
```

This represents one node with labels `Invoice` and `Document` and properties `status`, `amount`, and `currency`.

The label name SHALL be derived from the hyperlink destination by taking the final path segment and removing a `.md` extension, if present. For example, `Ontology/Invoice.md` defines the node label `Invoice`.

## Relationship Representation

A CommonMark hyperlink whose visible label is a semantic link annotation SHALL be interpreted as a PGM semantic link.

The hyperlink destination SHALL define the target reference.

The visible link label SHALL define the annotation. The annotation SHALL contain an annotation type and MAY contain a property map.

If the annotation type is `LABEL`, the semantic link SHALL define a node label on the current document node and SHALL NOT create a Property Graph relationship.

For all other annotation types, the semantic link SHALL define an outgoing relationship. PGM 0.2.0 only defines outgoing relationships. The relationship SHALL be authored in the Markdown file that represents the source node.

Example:

```markdown
[:LABEL](Ontology/Person.md)
[:approvedBy](Peter%20Meier.md)
```

This defines the node label `Person` on the current document node and an outgoing relationship of type `approvedBy` from the current document node to `Peter Meier.md`.

PGM 0.2.0 does not define direction-marker syntax. A label containing `->` or `<-` SHALL NOT create a PGM relationship.

This restriction avoids redundant syntax and duplicate or conflicting definitions of the same relationship across two Markdown files.

## Semantic Link Grammar

The semantic hyperlink label grammar is:

```ebnf
SemanticLinkLabel ::=
    ":" AnnotationType PropertyMap?

AnnotationType ::= Identifier

Identifier ::= Letter (Letter | Digit | "_")*

PropertyMap ::= YAMLFlowMapping
```

`LABEL` is a reserved annotation type and SHALL be interpreted as a label declaration, not as a relationship type.

A `LABEL` annotation SHALL NOT include a `PropertyMap`.

Annotation types SHALL be case-sensitive. Uppercase relationship types MAY be used by convention, but are not required by this specification.

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
4. Assign all frontmatter entries as node properties.
5. Parse CommonMark hyperlinks.
6. Treat only hyperlinks whose visible label is a semantic link annotation as PGM semantic links.
7. For semantic links with annotation type `LABEL`, assign a node label to the current document node and do not create a relationship.
8. For all other semantic links, create outgoing relationships using the annotation type as the relationship type.
9. Resolve hyperlink destinations to canonical node identifiers.
10. Emit, store, or expose an openCypher-compatible Property Graph.

A conforming processor SHOULD ignore ordinary hyperlinks.

A conforming processor SHOULD report semantic link labels that use `->` or `<-` as non-conforming without creating a relationship.

A conforming processor SHOULD report malformed semantic links without rejecting the entire document.

## Optional Extensions

Processors MAY implement optional extensions for environments that define additional Markdown-like link syntax.

Extensions SHALL NOT change the meaning of conforming PGM core documents.

### Semantic Wikilinks

A processor MAY support semantic wikilinks for environments such as Obsidian.

A semantic wikilink has the form:

```markdown
[[Target | :annotationType {property: value}]]
```

The target part SHALL identify the target reference. The annotation part SHALL follow the PGM semantic link label grammar without the surrounding CommonMark link brackets.

If the annotation type is `LABEL`, a semantic wikilink SHALL define a node label on the current document node and SHALL NOT create a Property Graph relationship.

For all other annotation types, a semantic wikilink SHALL define an outgoing relationship from the current document node to the target node.

The target resolution rules for wikilinks are implementation-defined. A processor SHOULD canonicalize semantic wikilink targets to the same node identifier form used for CommonMark hyperlink destinations.

Semantic wikilinks are not part of the PGM core syntax because wikilinks are not defined by CommonMark. A conforming core processor MAY ignore semantic wikilinks.

## Compatibility

PGM documents SHALL be valid CommonMark documents.

PGM core does not define new block syntax, inline syntax, HTML extensions, fenced directives, or renderer behavior.

A Markdown renderer that does not understand PGM SHALL still render PGM documents as ordinary Markdown.

## Conformance

A document conforms to PGM 0.2.0 if:

- it is valid CommonMark;
- any node properties intended for PGM are encoded as YAML frontmatter;
- any semantic link labels follow the grammar in this specification.

A processor conforms to PGM 0.2.0 if it implements the processing model above and preserves the semantics defined by the abstract information model.

Extensions MAY be implemented, but they SHALL NOT change the meaning of conforming PGM 0.2.0 documents.
