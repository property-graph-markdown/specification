# Rationale

PGM is intentionally small. This document explains the design decisions behind the 0.1.2 draft.

## Why CommonMark?

CommonMark is the most precise widely adopted definition of Markdown. It is portable, readable, and already supported by editors, renderers, static site generators, documentation systems, and AI tooling.

PGM uses CommonMark because the goal is not to invent a document language. The goal is to give existing Markdown corpora a minimal graph interpretation.

## Why Ordinary Hyperlinks?

Markdown already has a native way to connect documents: links.

Using ordinary hyperlinks means PGM works in existing Markdown tools without plugins, custom renderers, or preprocessing. A semantic relationship still looks like a readable sentence fragment in a note.

```markdown
[:partOf](project-apollo.md)
```

The link remains useful to humans even when no graph processor is present.

## Why No Direction Marker?

Property Graph relationships are directed, but PGM 0.1.2 only allows outgoing relationships.

Once incoming relationships are excluded, a direction marker no longer carries information. The Markdown file is the source node. The link destination is the target node.

PGM 0.1.2 therefore does not define `->` or `<-`.

Allowing both incoming and outgoing relationship syntax would make two Markdown files potential authorities for the same graph edge. For example, `invoice.md` could define an outgoing `approvedBy` relationship to `peter.md`, while `peter.md` could define an incoming `approvedBy` relationship from `invoice.md` with different properties. That would require conflict-resolution rules, merge semantics, or precedence rules.

PGM avoids that complexity. A relationship is authored once, in the source node document.

## Why a Colon Relationship Marker?

PGM must distinguish semantic relationships from ordinary prose links.

The 0.1.2 grammar uses an openCypher-style relationship marker: `[:type]`.

The colon makes intent explicit without requiring uppercase naming conventions. Links such as `[Read more](invoice.md)` remain ordinary Markdown links, while `[:approvedBy](peter.md)` is visibly graph syntax.

## Why YAML?

YAML frontmatter is already common in Markdown systems such as static site generators, documentation tools, and note-taking applications.

PGM uses YAML frontmatter for node labels and node properties because it is already the conventional place for document metadata.

The reserved key `labels` maps directly to Property Graph labels. All other keys become node properties.

PGM does not define body-level node label syntax such as `:Invoice`. Node labels are document metadata, and frontmatter is already the Markdown ecosystem's established metadata channel. Keeping labels in YAML avoids a second way to describe the same node.

## Why YAML Flow Mapping?

Relationship properties need a compact but readable syntax inside a link label.

YAML flow mappings already provide this:

```markdown
[:approvedBy {date: 2026-06-26}](peter-meier.md)
```

PGM delegates property-map syntax to YAML rather than defining a new mini-language.

## Why Are Semantic Wikilinks Optional?

Wikilinks are useful in tools such as Obsidian, Logseq, and Foam, but they are not CommonMark links.

PGM therefore keeps CommonMark hyperlinks as the core syntax and treats semantic wikilinks as an optional processor extension.

```markdown
[[peter-meier | :approvedBy {date: 2026-06-26}]]
```

This gives Obsidian users a natural authoring form without making PGM depend on an editor-specific link model.

## Why Property Graphs?

Property Graphs model typed, directed relationships with properties on both nodes and relationships. This matches many real knowledge tasks:

- documents approved by people
- issues caused by incidents
- concepts explained by sources
- tasks owned by teams
- records belonging to projects

Property Graphs are also practical for AI systems because they preserve local human-readable text while adding explicit relationship structure.

## Why openCypher?

openCypher is a widely understood query model for Property Graphs. It gives PGM a concrete target without requiring a specific database vendor.

PGM does not require Neo4j, Memgraph, RedisGraph, or any other implementation. It uses openCypher compatibility as the common semantic shape.

## Why Not RDF?

RDF is powerful and important, but it is not the smallest fit for this proposal.

PGM is designed around the Property Graph model: nodes with labels and properties, and directed relationships with types and properties. That model maps naturally to openCypher and to how many users already think about graph databases.

RDF export may be useful later, but RDF is intentionally not the core information model for PGM 0.1.2.

## Why Not HTML Extensions?

HTML extensions would remain valid Markdown, but they are harder to read, noisier in source form, and less pleasant in everyday notes.

PGM favors syntax that a human can understand while reading raw Markdown.

```markdown
[:dependsOn](service-api.md)
```

This is clearer than an equivalent HTML attribute block for most authors.

## Why Not Custom Markdown Blocks?

Custom blocks would add grammar and tooling complexity.

PGM wants relationships to live where authors already express connections: links in prose, lists, and notes. A custom block format would separate graph semantics from the human text and would make the extension feel like a framework.

## Why One File Equals One Node?

The file is the unit that Markdown tools already understand. It has a path, a title, metadata, version history, and links.

Using one file as one node gives PGM an immediate canonical identity model without inventing node delimiters, embedded IDs, or custom blocks.

## Why Is the Link Destination Canonical?

The visible label of a PGM semantic link defines the relationship descriptor.

The destination is the stable machine-readable reference to the target node. PGM therefore treats the destination as canonical.

## Why Keep 0.1.2 So Small?

PGM should feel like CommonMark, YAML, or OpenAPI: a specification first, not an application framework.

Features such as namespaces, ontology validation, RDF export, embedded graph queries, and inference rules are useful ideas. They are excluded from 0.1.2 because the core must remain obvious, interoperable, and easy to implement.
