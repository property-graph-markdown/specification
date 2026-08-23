# PGM 0.4 Rationale

## A semantic profile, not a Markdown extension

PGM's design center is:

> PGM adds graph semantics, not syntax.

OKF already defines a portable collection of Concepts as Markdown documents
with YAML frontmatter. Markdown already defines directed links, link text,
destinations, and optional titles. YAML already defines readable structured
values. PGM only specifies how those constructs map to a Property Graph.

CommonMark 0.31.2 is the reference grammar for canonical PGM Link examples,
not the conceptual boundary of the model. Another Markdown profile is usable
when it exposes equivalent parsed Link text, destination, and title fields.

## Why the interpretation is monotonic over OKF

OKF says a Concept Link from Concept A to Concept B asserts a relationship and
describes its graph view as directed and untyped. Interoperability therefore
requires PGM to preserve that baseline: every OKF Concept becomes a Node and
every OKF Concept Link becomes a Relationship.

Making Relationships depend on a YAML title would invert progressive
enhancement. The same OKF bundle would lose relationships when read as PGM,
and adding optional metadata would unexpectedly determine whether an edge
exists. Under the monotonic rule, enrichment can add a Type or Properties but
cannot delete the underlying OKF Relationship.

This also handles navigational links consistently. If a link targets a Concept
under OKF path rules, it is part of OKF's graph. Authors who need a purely
external or non-conceptual navigation target can use a destination that is not
an OKF Concept ID.

## Why Concepts become Nodes

An OKF Concept already has stable identity: its Concept ID. Its frontmatter is
already the metadata associated with that Concept. Reusing both avoids
authored node IDs, node blocks, classified empty links, and merge rules for
properties repeated through prose.

PGM retains the complete frontmatter map. It does not classify keys as
document metadata versus domain data because OKF intentionally permits
producer-defined keys and does not establish that boundary.

## Why `type` is retained and additionally structural

OKF defines `type` as a Concept Property with special meaning. Removing it
from the Property map would make a PGM parse lossy and would treat one YAML key
differently before an adapter has requested such a projection.

PGM therefore keeps `type` in the complete Node or Relationship Property map
and additionally derives the optional Graph Element Type from a non-empty
string value. This gives processors a convenient structural field without
destroying source data. A database adapter may project that field to a label
or relationship type and omit the redundant stored property in its target.

The same derivation applies symmetrically to Relationships:

```markdown
[Acme](Acme.md "{type: works_for, since: 2024}")
```

Omitting `type` naturally yields an untyped Relationship. A present but empty
or non-string value is preserved as data, leaves the Relationship untyped, and
warrants a diagnostic; PGM does not invent a sentinel such as `UNTYPED`.

## Why optional Properties use a YAML Flow Map title

The Markdown title carries metadata without changing visible Link text or the
Concept destination. A complete YAML Flow Mapping provides a deterministic
Property boundary while delegating values and escaping to established parsers:

```markdown
[Acme](Acme.md "{since: 2024, roles: [architect, developer]}")
```

The title is enrichment, not an edge marker. No title, a normal text title,
and an empty Mapping all retain the baseline untyped Relationship. Link text
remains prose; treating it as a machine type would couple phrasing,
localization, and formatting to graph structure.

The current Concept is the source and the resolved Concept destination is the
target. That makes outgoing arrows redundant. Incoming Relationships are a
query or backlink view, so an authored incoming marker would create duplicate
authority for one edge.

## Why malformed enrichment is non-fatal

A brace-leading title that fails YAML parsing is likely an authoring mistake,
so a diagnostic is useful. It cannot, however, erase the OKF relationship or
make an otherwise valid OKF bundle cease to be PGM. The processor therefore
keeps the ordinary title and baseline Relationship but extracts no partial
Properties. Applications that demand clean annotations can promote the
diagnostic in a separately identified strict profile.

## Why arbitrary YAML values are retained

PGM is an interchange model, not a least-common-denominator database schema.
YAML mappings, sequences, timestamps, binary values, sets, and other values
may be useful even when a specific graph engine accepts only primitive
properties. The exporter is the correct layer for flattening, encoding, or
rejection.

Only outer Mapping keys must be strings because they name Properties. PGM does
not maintain a second whitelist of YAML value types alongside the YAML parser
used by the OKF bundle.

## Why OKF-named Relationship Properties stay opaque

An OKF Concept and a PGM Relationship are different kinds of graph elements.
Keys such as `sources`, `generated`, `verified`, `status`, or `stale_after`
are preserved when authors place them in Relationship Properties, but core PGM
does not silently transfer OKF's Concept-specific contracts to an edge.

Provenance, trust, lifecycle, and attestation are valuable extensions. They
need their own named profile so processors can agree on validation and meaning
instead of inferring semantics from a coincidentally reused key.

## Relationship identity

PGM uses source Concept ID, target Concept ID, and the canonical complete
Relationship Property map as the semantic key. Since `type` remains in that
map, listing it separately in the key would be redundant. Link text and
ordinary titles are source representation rather than graph identity, and
YAML mapping order is presentation rather than semantics.

A bare link and the same link titled `"{}"` may therefore coalesce. An
implementation may hash the semantic tuple as an internal fingerprint; that
hash is neither authored syntax nor a Property.

## Progressive enhancement

A PGM-unaware tool still sees valid OKF, Markdown, and YAML:

- Concepts remain normal files with frontmatter.
- Concept Links remain clickable and keep their OKF relationships.
- YAML annotation titles remain ordinary link titles or tooltips.
- Git diffs, static sites, editors, and search tools need no preprocessing.

PGM-aware processors add typed Properties, validation, export, and graph
navigation without changing the source representation.

## What earlier features were removed

- **Classified link text or titles (`:TYPE`).** Use YAML `type` in a complete
  Flow Mapping title.
- **Properties outside the Markdown title.** Use Concept frontmatter or the
  complete YAML title mapping.
- **`->` and `<-`.** Link destinations already establish direction; incoming
  views come from inverse traversal or backlinks.
- **Empty-target node annotations.** OKF Concepts and frontmatter already
  supply Node identity, Type, and Properties.
- **YAML-title opt-in.** It conflicted with OKF's relationship semantics. Every
  Concept Link is now a baseline Relationship and YAML only enriches it.

## Why the reference export is non-normative

Cypher is a useful illustration and integration target, but it is not the PGM
data model. Cypher labels, mandatory relationship types, and value limits must
not narrow valid PGM. The reference adapter maps typed examples and reports an
explicit target limitation when a source contains an untyped Relationship or
an unsupported YAML value.
