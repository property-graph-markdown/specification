# Rationale

PGM is intentionally small. This document explains the design decisions behind the 0.3.0 draft.

## What Kind of Language Is PGM?

PGM is a knowledge-graph representation language for Markdown files. It provides a standard textual representation of a Property Graph while preserving the document as readable Markdown.

## Why CommonMark?

CommonMark is the most precise widely adopted definition of Markdown. It is portable, readable, and already supported by editors, renderers, static site generators, documentation systems, and AI tooling.

PGM does not invent a document language. It gives an existing Markdown corpus a Property Graph interpretation.

## Why Property Graphs?

Property Graphs model labeled nodes and typed, directed relationships with properties on both. This matches, for example, documents approved by people, concepts explained by sources, tasks owned by teams, and records belonging to projects.

The model is practical for AI systems because
1. It allows to provide a structured knowledge graph as source of truth
2. Humans can visualize knowledge graphs quite naturally and thus understand complex topic structures more easiligy
3. Knowledge grapbs can be provisioned for AI Agents as a structured source of truth for improved data quality

## Why Keep Property Graph Semantics in a Markdown Document?

For AI agents, storage is often not the limiting resource; the context window is. Every sidecar representation loaded alongside a document consumes additional tokens. At corpus scale, an agent may already need to read the Markdown prose, so requiring a separate RDF document or NeoçJ database or knowledge graphs would duplicate part of the same knowledge in its context.

With PGM, a knowledge graph can be in the same file as documentation, agent memory, and human-maintained knowledge. For example:

```markdown
# Ada Lovelace
[:Person {name: "Ada Lovelace"}]()
[:Mathematician]()

Ada Lovelace was a matematician born 1815 in London.
[:BORN_IN {year:1815}](London.md).
```

The prose remains useful on its own, while the annotations provide deterministic property graph structure without requiring another representation. This reduces representational duplication and keeps edits to text and graph semantics in the same Git history.

## Why Ordinary Inline Links?

Markdown already has a native construct that combines visible annotation text with an optional destination: the inline link.

```markdown
[:Person {name: "Ada"}]()
[:BORN_IN {year: 1815}](London.md)
```

Both are valid CommonMark and remain inspectable in existing editors, renderers, diffs, and search tools. A PGM processor parses the normal CommonMark link first and then interprets its text and destination.

## Why One Shared Syntax?

Node labels, node properties, relationship types, and relationship properties belong to the same Property Graph model. Expressing them with one construct avoids separate property mechanisms and reserved annotation keywords for node lales.

The lexical form `:CLASS {properties}` is identical for nodes and relationships. Structure supplies the distinction: an empty destination annotates the current node; a non-empty destination creates an outgoing relationship.

## Why Does an Empty Destination Mean the Current Node?

The current Markdown file already identifies the current graph node as the source.

An empty destination is not the same as a destination that resolves to the current node. `[:Person]()` annotates the current node; it does not create a self-relationship such as `(current)-[:Person]->(current)`. A non-empty destination that resolves to the current document would still declare a relationship to that node.

PGM treats a type annotation as the empty-target form of the same relationship-shaped syntax. This is a syntax unification, not a targetless relationship in the resulting Property Graph: when the target is empty, the type and properties annotate the current node and no relationship is emitted. When the target is non-empty, they describe an outgoing relationship. Using these two structural cases keeps the language uniform, simple, and minimal.

An empty CommonMark destination therefore reads naturally as “apply here.” It also avoids custom headings, blocks, HTML attributes, and special label-reference files. CommonMark already normalizes both `()` and `(<>)` to an empty destination, so PGM does not need another parsing rule.

## Why No Reserved LABEL Keyword?

PGM 0.2.1 used `:LABEL` as a special marker and derived the actual label from the link destination.

PGM 0.3.0 writes the label directly:

```markdown
[:Person]()
```

This removes a reserved word, destination-to-label conversion rules, and a special case that prohibited properties. `LABEL` is now an ordinary class name.

## Why YAML Flow Mapping?

Properties need a readable syntax inside link text. YAML flow mappings already provide strings, numbers, booleans, null, and lists:

```markdown
[:Person {name: "Ada", born: 1815, interests: [math, music]}]()
```

PGM delegates flow-mapping syntax to YAML instead of defining a property mini-language.

## Why Is Formal Domain Semantics Optional?

Formal vocabularies are valuable when deterministic validation or logical inference is required. They can also be expensive in the common case because they explicitly state facts that a human or language model can often infer from the surrounding text and names. For example, an OWL vocabulary might declare:

```turtle
:bornIn
    rdf:type owl:ObjectProperty ;
    rdfs:domain :Person ;
    rdfs:range :City .
```

The corresponding PGM document can express the operational graph fact directly:

```markdown
[:Person]()
Born in [:BORN_IN](London.md).
```

The concise form does not replace formal validation, nor does it assert the domain and range constraints shown above. It covers the common authoring and agent-context case efficiently. A separate formal layer may be applied when a system needs stronger guarantees, without making that layer a prerequisite for every PGM corpus.

## Why Only Outgoing Relationships?

The Markdown file is the source node and a non-empty link destination is the target node. A separate arrow would repeat information already present in the structure.

Allowing incoming declarations would make two files possible authorities for one edge and require conflict or merge rules. PGM therefore authors each relationship once, in its source document, and defines no `->` or `<-` markers.

## Why a Natural Relationship Key?

PGM needs stable relationship semantics without adding an authored ID syntax. Source, type, target, and the canonical property map already contain the complete authored meaning of a relationship.

PGM therefore uses `(source, type, target, canonical(properties))` as the natural key. Reordering links does not change that key. Equal annotations coalesce, while relationships with different properties remain distinct.

A processor may hash this tuple for an internal fingerprint. That hash is not a PGM property and is not required in Markdown. Database-specific physical identity remains the graph database's responsibility.

## Why Both CREATE and MERGE Exports?

`CREATE` is the direct snapshot form and is appropriate when importing into an empty target. Its repeatability depends on clearing or replacing that target before each import; `CREATE` itself is not idempotent on a populated graph.

`MERGE` can match the complete natural relationship key and is therefore idempotent for repeated execution of the same corpus export. It does not remove stale relationships after source changes, so full synchronization remains an integration concern.

## Why Are Node Property Conflicts Errors?

Multiple node annotations let labels and properties remain near relevant prose. This requires deterministic merge behavior.

Equivalent declarations are harmless. Different values for the same key are ambiguous, so PGM reports a validation error instead of choosing the first or last declaration silently.

## Why Is the File Path Canonical?

The file is the unit Markdown tools already understand. It has a path, title, version history, and links. Using the canonical corpus path as node identity avoids embedded IDs and custom node delimiters.

For relationships, the visible class expression defines the type and properties; the destination remains the machine-readable target reference.

## Why Are Wikilinks Conversion-Only?

Wikilinks are useful in Obsidian, Logseq, and Foam, but they are not CommonMark. PGM therefore keeps classified CommonMark links as the complete core syntax.

Treating wikilinks as a second semantic input language would weaken interoperability and leave no natural empty-destination form for node annotations. Editor integrations may instead convert recognizable wikilinks to canonical CommonMark links before extraction. After conversion, every processor sees the same document and semantics.


## Why openCypher?

openCypher is a widely understood query model for Property Graphs. It gives PGM a concrete semantic target without requiring a particular database vendor.

## Why Not RDF?

RDF is powerful, but PGM is deliberately shaped around the Property Graph model used by openCypher. PGM is not primarily intended to compete with RDF; it addresses a different authoring center of gravity.

As a design shorthand, RDF and OWL optimize knowledge for formal interoperability and logical reasoners. PGM optimizes knowledge for people, Git workflows, and AI agents while retaining a deterministic transformation to a Property Graph. That goal leads directly to minimal syntax, high readability, inline use in prose, version-control-friendly files, and no mandatory parallel representation.

RDF export may be useful later, but it is not the smallest core for this proposal.

## Why Not HTML Extensions or Custom Blocks?

HTML attributes and custom blocks would add source noise, grammar, and renderer complexity. PGM keeps graph semantics where Markdown authors already express connections: inline links in prose, lists, and notes.

## Why Keep 0.3.0 So Small?

PGM should feel like CommonMark, YAML, or OpenAPI: a specification first, not an application framework.
