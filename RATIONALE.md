# Rationale

PGM is intentionally small. This document explains the design decisions behind the 0.3.0 draft.

## Why CommonMark?

CommonMark is the most precise widely adopted definition of Markdown. It is portable, readable, and already supported by editors, renderers, static site generators, documentation systems, and AI tooling.

PGM does not invent a document language. It gives an existing Markdown corpus a Property Graph interpretation.

## Why Ordinary Inline Links?

Markdown already has a native construct that combines visible annotation text with an optional destination: the inline link.

```markdown
[:Person {name: "Ada"}]()
[:BORN_IN {year: 1815}](London.md)
```

Both are valid CommonMark and remain inspectable in existing editors, renderers, diffs, and search tools. A PGM processor parses the normal CommonMark link first and then interprets its text and destination.

## Why One Shared Syntax?

Node labels, node properties, relationship types, and relationship properties belong to the same Property Graph model. Expressing them with one construct avoids separate metadata schemas and reserved annotation keywords.

The lexical form `:CLASS {properties}` is identical for nodes and relationships. Structure supplies the distinction: an empty destination annotates the current node; a non-empty destination creates an outgoing relationship.

## Why Does an Empty Destination Mean the Current Node?

The current Markdown file already identifies the current graph node. A second target identifier would add no information to a node annotation.

An empty CommonMark destination therefore reads naturally as “apply here.” It also avoids custom headings, blocks, HTML attributes, and special label-reference files. CommonMark already normalizes both `()` and `(<>)` to an empty destination, so PGM does not need another parsing rule.

## Why No Reserved LABEL Keyword?

PGM 0.2.1 used `:LABEL` as a special marker and derived the actual label from the link destination.

PGM 0.3.0 writes the label directly:

```markdown
[:Person]()
```

This removes a reserved word, destination-to-label conversion rules, and a special case that prohibited properties. `LABEL` is now an ordinary class name.

## Why No Graph Semantics in Front Matter?

Front Matter is widely used, but CommonMark does not define it. Different tools parse it differently and reserve different keys.

PGM 0.3.0 keeps Front Matter available as ordinary document metadata while making the graph completely recoverable from classified CommonMark links. This gives node and relationship properties the same visible syntax and removes the previous split between block metadata and inline graph semantics.

## Why YAML Flow Mapping?

Properties need a readable syntax inside link text. YAML flow mappings already provide strings, numbers, booleans, null, and lists:

```markdown
[:Person {name: "Ada", born: 1815, interests: [math, music]}]()
```

PGM delegates flow-mapping syntax to YAML instead of defining a property mini-language. YAML block mappings and Front Matter are not part of PGM graph extraction.

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

## Why Property Graphs?

Property Graphs model labeled nodes and typed, directed relationships with properties on both. This matches documents approved by people, concepts explained by sources, tasks owned by teams, and records belonging to projects.

The model is practical for AI systems because it preserves local human-readable text while adding explicit graph structure.

## Why openCypher?

openCypher is a widely understood query model for Property Graphs. It gives PGM a concrete semantic target without requiring a particular database vendor.

## Why Not RDF?

RDF is powerful, but PGM is deliberately shaped around the Property Graph model used by openCypher. RDF export may be useful later; it is not the smallest core for this proposal.

## Why Not HTML Extensions or Custom Blocks?

HTML attributes and custom blocks would add source noise, grammar, and renderer complexity. PGM keeps graph semantics where Markdown authors already express connections: inline links in prose, lists, and notes.

## Why Keep 0.3.0 So Small?

PGM should feel like CommonMark, YAML, or OpenAPI: a specification first, not an application framework.

Namespaces, ontology validation, RDF export, embedded graph queries, and inference rules remain excluded until the unified core has proven stable and interoperable.
