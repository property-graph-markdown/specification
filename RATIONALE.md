# PGM 0.4 rationale

## A semantic profile, not a Markdown extension

PGM's design center is:

> PGM adds graph semantics, not syntax.

OKF already defines Concepts, Concept IDs, and Link assertions in Markdown
documents with YAML frontmatter. Markdown already defines Link text,
destinations, titles, and direction. YAML already defines structured values.
PGM specifies their property-graph interpretation and adds no Link expression,
arrow, type token, or Property mini-language.

CommonMark 0.31.2 is the canonical reference profile, not a proprietary parser
boundary. Another Markdown profile remains usable when it exposes equivalent
parsed Link fields and declares itself in conformance reports.

## Why every Concept Link occurrence remains a Relationship

OKF says a Link from Concept A to Concept B asserts a relationship and
describes the normal graph interpretation as directed and untyped. Requiring a
YAML title would remove OKF relationships rather than enrich them.

PGM therefore maps every Concept Link occurrence to one Relationship
occurrence. YAML metadata can add Properties and a Type, but cannot determine
whether the assertion exists. Repeated Links are repeated assertions and are
not silently removed by the Core processor.

This is intentionally a multigraph interpretation. An application may offer a
deduplicated view based on the portable semantic key, but that view does not
replace the occurrence-preserving PGM Core Result.

## Why fragment-only Links are not Relationships

Obsidian vaults, documentation sites, and CommonMark documents frequently use
`#heading` Links for a table of contents or local navigation. Such a Link has
no Concept path and OKF §6.1 defines cross-Concept Links through absolute or
relative paths. Treating every local heading jump as a self-edge would add
large amounts of accidental graph data.

`Concept.md#heading` still names a Concept and therefore remains a
Relationship; the fragment does not participate in the target Concept ID.
Query-bearing destinations are excluded because OKF defines path identities,
not query-parameter variants of Concepts.

The resolver percent-decodes each path segment once, remains within the bundle
root, rejects encoded separators, and preserves case and Unicode code points.
This prevents filesystem-dependent identities and traversal ambiguities.

## Why broken targets do not become Nodes

OKF requires consumers to tolerate broken Links because a target may represent
not-yet-written knowledge. The assertion therefore survives as a Relationship
to an unresolved Concept ID reference.

A PGM Node, however, is the interpretation of a present Concept. Creating a
Node with no Concept, frontmatter, or required OKF Type would contradict that
definition. PGM Core keeps the dangling reference and exposes resolution as a
derived status.

Graph databases and relational schemas may need an endpoint record. Their
adapters may create a clearly marked placeholder, but it remains an adapter
artifact. When the Concept later appears, the same Concept ID can resolve the
placeholder without changing the original Link assertion.

## Why complete Property maps and `type` are retained

OKF intentionally permits producer-defined frontmatter entries. PGM therefore
does not divide frontmatter into document metadata and domain data. The
complete Mapping becomes Node Properties.

Likewise, the complete YAML Flow Mapping in an eligible Link title becomes
Relationship Properties. A non-empty string `type` is retained and is also
exposed as the Graph Element Type. Removing it would make parsing lossy and
would give one Property special deletion behavior.

An absent, empty, or non-string Relationship `type` naturally leaves the
Relationship untyped. PGM does not invent `UNTYPED` or `RELATED_TO` in its Core
model. Adapters can use a generic native Relationship Type and store the
optional PGM Type separately.

## Why optional Properties use a YAML Flow Mapping title

The normal Markdown title carries metadata without changing visible Link text
or the Concept destination:

```markdown
[Acme](Acme.md "{since: 2024, roles: [architect, developer]}")
```

A complete Flow Mapping gives the annotation an unambiguous boundary while
leaving parsing, escaping, sequences, and nested values to YAML. Link text
remains prose and may change with wording or localization without changing the
graph value.

No title, an ordinary text title, and `{}` all describe an empty Relationship
Property map. They remain separate occurrences if all are authored. A
brace-leading but invalid annotation warrants a warning, yet cannot erase the
baseline OKF assertion or make PGM Core invalid.

## Why PGM pins a YAML profile

Saying only “use YAML” is insufficient for interoperable graph values. YAML
1.1 and YAML 1.2 resolve `yes` differently; many YAML 1.2 libraries still
implicitly construct untagged timestamps even though the YAML 1.2.2 Core
Schema does not. Duplicate keys and application-specific tags also vary by
implementation.

PGM therefore pins YAML 1.2.2 Core Schema for implicit resolution. Untagged
dates are strings; an author who needs a timestamp value writes
`!!timestamp`. Safe explicit binary, timestamp, and set values are supported,
while arbitrary object construction is forbidden.

Aliases are presentation for repeated values. Acyclic aliases are expanded by
value; cycles cannot be represented consistently in JSON, Cypher, or the
property-graph model and are rejected. Duplicate Mapping keys are rejected
rather than resolved by parser-specific first-wins or last-wins behavior.

## Why Relationship identification has two levels

OKF does not define Relationship IDs, duplicate elimination, or hashing. PGM
must therefore preserve Link occurrences independently from any database
identity policy.

Two portable values serve different purposes:

- `relationship_key` identifies the semantic assertion tuple of source,
  target, and complete Properties. It supports comparison, grouping, and a
  deliberately deduplicated view.
- `relationship_id` adds a zero-based ordinal among equal preceding assertions
  in the same source document. It allows identical parallel Relationships to
  coexist in JSON and Cypher.

Unrelated Link insertions do not affect the ordinal. Inserting an identical
Link before another identical Link necessarily changes which indistinguishable
occurrence receives which ordinal. Stable identity across arbitrary Property
or endpoint edits requires an authored application ID or database surrogate;
it cannot be derived from content alone.

The identifiers are bundle-relative because OKF does not define a global
Bundle ID. Multi-bundle stores scope them with an external bundle identifier.

## Why the canonical value encoding is fully tagged

JSON objects alone cannot distinguish a YAML date from an authored Mapping
that happens to look like a technical date wrapper. JSON also cannot directly
carry sets, binary values, non-string nested Mapping keys, large integers,
NaN, or infinity without implementation-dependent loss.

Canonical PGM Value v1 therefore tags every value and represents Mappings as
sorted entry arrays. No authored Mapping or Sequence can collide with the
technical envelope. Numbers are encoded as reduced rational strings, so large
integers remain exact and numerically equal integer/float values compare
equally. Booleans remain distinct from numbers.

The resulting number-free JSON subset is serialized with RFC 8785 JCS and
hashed with SHA-256. Unicode is preserved without normalization, as required by
JCS. Golden vectors make cross-language implementations testable.

This encoding round-trips the canonical PGM value, not YAML presentation.
Comments, scalar style, anchor names, aliases, and authored Mapping order are
intentionally not recovered.

## Why validation stays local and auditable

The immutable OKF specification is normative; a moving package or `main`
branch cannot define reproducible conformance. The reference processor applies
the pinned OKF checks through a small local adapter and then applies the PGM
YAML, path, and graph rules.

`markdown-it-py`, `ruamel.yaml`, and `jsonschema` are implementation choices,
not normative PGM dependencies. The executable language-neutral TCK records
only normative Core behavior so other languages can test the same contract.
Portable IDs, JSON exchange, reference diagnostics, and adapter snapshots are
tested separately because they belong to different conformance classes or are
recommended implementation behavior.

Errors, warnings, and adapter errors are separate. An invalid optional
Relationship annotation is a warning because the Core Relationship survives.
A Cypher mapping limitation is an adapter error and cannot make the OKF
or PGM source invalid.

## Why JSON and Cypher remain adapters

PGM is a source and graph model, not a query language or database schema. The
reference outputs demonstrate faithful mappings:

- JSON carries the complete typed value representation and portable IDs. Its
  strict importer verifies derived fields so export-import-export preserves the
  same Core Result rather than trusting inconsistent cached values.
- Cypher uses generic technical Node and Relationship Types so untyped PGM
  Relationships remain representable.

Authored Properties stay inside the canonical JSON value instead of competing
with technical fields such as `pgm_concept_id` or `pgm_relationship_id`.
The JSON exchange retains unresolved targets as references without inventing
Nodes; the Cypher projection materializes them only as marked adapter
placeholders.

These envelope names, labels, and fields are informative. The PGM Core semantics
and the optional portable identification algorithm remain independent of a
specific database.

## Why OKF-named Relationship Properties stay opaque

An OKF Concept and a PGM Relationship are different graph elements. Keys such
as `sources`, `generated`, `verified`, `status`, or `stale_after` remain
ordinary Relationship Properties unless a separately named profile defines
their edge semantics. Coincidentally reusing an OKF field name must not silently
transfer Concept-specific provenance or lifecycle rules.

## What earlier drafts removed

PGM 0.4 removes classified Link text or titles such as `:TYPE`, Property
expressions outside a Markdown title, authored `->`/`<-` markers, and
empty-target node annotations. OKF Concepts already provide Node identity and
frontmatter; Markdown destinations already provide direction; YAML already
provides structured values.
