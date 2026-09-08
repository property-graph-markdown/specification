# Property Graph Markdown (PGM) 0.4.0 Public Draft

## Status of this draft

This document is the **PGM 0.4.0 Public Draft**, dated 2026-09-08. It is
published for implementation and community review and is not yet a final
standard. Incompatible corrections remain possible before a final 0.4.0
release.

This draft supersedes PGM 0.3.0. The canonical source is
[`SPEC.md`](https://github.com/property-graph-markdown/specification/blob/main/SPEC.md)
in the Property Graph Markdown specification repository. Feedback and
interoperability reports belong in the repository's
[issue tracker](https://github.com/property-graph-markdown/specification/issues).

An implementation or conformance report MUST identify this document as
`PGM 0.4.0 Public Draft` rather than claiming conformance to a final PGM 0.4.0
standard.

## 1. Scope and normative foundations

Property Graph Markdown (PGM) is a semantic profile of Open Knowledge Format
(OKF), Markdown, and YAML for representing property graphs.

> PGM adds graph semantics, not syntax.

The base formats have separate responsibilities:

- OKF defines Knowledge Bundles, Concepts, Concept IDs, and Concept Links.
- Markdown defines document structure, Link text, destinations, and titles.
- YAML defines metadata mappings and structured Property values.
- PGM maps those existing constructs to Nodes, Relationship occurrences,
  Properties, and optional Graph Element Types.

PGM MUST NOT replace Markdown or YAML with a PGM-specific Link lexer or
Property grammar.

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **NOT RECOMMENDED**, **MAY**, and
**OPTIONAL** are to be interpreted as described in BCP 14 when, and only when,
they appear in all capitals, as specified by
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) and
[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174).

### 1.1 OKF baseline

Every PGM Knowledge Bundle MUST conform to OKF 0.2. The normative OKF text is
[`okf/SPEC.md`](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/3fcbb9f828c2f23d109c855ee403c3a4c81f3a96/okf/SPEC.md)
from `GoogleCloudPlatform/knowledge-catalog` at exact commit
`3fcbb9f828c2f23d109c855ee403c3a4c81f3a96`, with SHA-256
`5a3311d270bebb16d558010e75064f5b75323f284992641732b1c8097511f948`.

PGM publications and conformance reports MUST identify that immutable commit
and MUST NOT substitute a moving branch such as `main`. A PGM processor MUST
apply the OKF 0.2 conformance requirements, including the rules for Concept
frontmatter and the reserved `index.md` and `log.md` documents. It MUST
preserve unknown OKF frontmatter entries and MUST NOT reject an entry merely
because its name is not known to the processor.

The pinned specification, rather than a particular OKF software package, is
the normative authority.

### 1.2 Markdown profile

[CommonMark 0.31.2](https://spec.commonmark.org/0.31.2/) is the reference
Markdown profile for canonical PGM Links. A processor MAY support another
Markdown profile when it exposes equivalent parsed Link text, destination,
and title values. A conformance report MUST name the Markdown profile and
version used.

Markdown parsing happens before PGM interpretation. PGM operates on parsed
Links and does not reinterpret Markdown source characters, title delimiters,
escapes, reference definitions, or images.

Concept and reserved documents are UTF-8. A processor MUST accept LF, CRLF,
and CR line endings and MAY consume exactly one initial UTF-8 BOM as an
encoding signature; that BOM is not Markdown or YAML content. A BOM anywhere
else remains content.

### 1.3 YAML profile

PGM uses [YAML 1.2.2](https://yaml.org/spec/1.2.2/) with the Core Schema for
implicit scalar resolution. In particular, untagged `yes` and
`2026-08-23` are strings, while untagged `true` is a boolean. YAML 1.1
implicit boolean or timestamp resolution MUST NOT be used.

Portable PGM processors MUST support the Core Schema tags and the explicitly
written standard `!!binary`, `!!timestamp`, and `!!set` tags. A processor MUST
NOT construct executable or application-native objects from YAML tags. Other
explicit tags are outside the portable PGM 0.4.0 YAML profile. An unsupported
tag in Concept frontmatter is a PGM Core error. In a Link title it makes only
the optional Relationship annotation unusable under §5.5.

An explicitly tagged timestamp MUST have at most six fractional-second digits
and MUST remain within calendar years 0001 through 9999 after a timezone-aware
value is normalized to UTC. A timestamp outside this portable range is a PGM
Core error in Concept frontmatter and makes only the optional Relationship
annotation unusable under §5.5. Untagged OKF date and timestamp spellings
remain strings under the Core Schema and are unaffected by this restriction.

Duplicate Mapping keys are errors. The outer keys of Concept frontmatter and
Relationship Property maps MUST be strings; nested YAML Mappings MAY use any
acyclic key value supported by this profile. Acyclic aliases are permitted and
have the value of the referenced node. A cyclic YAML representation graph is
not a PGM Property value and is an error in Concept frontmatter; in a Link
title it makes only the optional annotation unusable.

PGM value identity distinguishes nulls, booleans, numbers, strings, binary
values, dates, timestamps, sequences, Mappings, and sets. Values of different
kinds are unequal. Integers and binary64 floats are equal exactly when their
§6.1 reduced rational values are equal; all NaNs share the `nan` identity and
negative zero equals zero. String identity is exact Unicode code-point
identity without normalization. Timezone-aware timestamp identity is its UTC
instant, while timezone-free timestamps remain distinct local values.
Sequences compare in order; Mappings and sets compare independent of source
order using these rules recursively. Mapping keys and set members MUST be
unique under PGM value identity. Canonical PGM Value v1 in §6.1 is the
normative serialization of this same identity, not a different equality rule.

These rules apply identically wherever this specification refers to parsed
YAML values. YAML source spelling, comments, anchors, aliases, and Mapping key
order are presentation and are not graph Properties.

## 2. Design principles

PGM is governed by these principles:

- **Zero new Markdown syntax.** PGM documents use syntax already defined by
  Markdown and YAML.
- **Monotone OKF interpretation.** Every present OKF Concept becomes a Node
  and every OKF Concept Link occurrence becomes a Relationship occurrence.
- **Graceful degradation.** A processor without PGM support still sees an OKF
  bundle containing ordinary Markdown documents and Links.
- **Lossless Properties.** Complete Property maps are retained; deriving a
  Graph Element Type does not remove `type`.
- **Occurrence preservation.** Optional identity or database profiles do not
  remove repeated Link assertions from the PGM Core Result.
- **Tool interoperability.** Implementations SHOULD compose existing OKF,
  Markdown, and YAML processors.
- **Adapter isolation.** Restrictions of JSON, Cypher, or another target
  do not narrow the valid PGM source model.

## 3. Terminology and graph model

This specification uses the following terms:

- **Concept:** a present non-reserved OKF Concept document.
- **Node:** the PGM interpretation of one Concept.
- **Link:** a Link produced by the applicable Markdown parser.
- **Concept Link:** a Link whose destination satisfies §5.1.
- **Relationship occurrence:** the PGM interpretation of one syntactic
  Concept Link occurrence.
- **Target reference:** the resolved Concept ID named by a Relationship,
  whether or not that Concept is present.
- **Resolved Relationship:** a Relationship whose target reference identifies
  a Node in the same Core Result.
- **Node Properties:** the complete YAML frontmatter Mapping of a Concept.
- **Relationship Properties:** the complete YAML Flow Mapping in a Link title
  when it satisfies §5.3.
- **Graph Element Type:** the non-empty string additionally derived from a
  `type` Property.

In this document, a non-empty string contains at least one Unicode code point.
It is not trimmed or normalized; a whitespace-only string is therefore
non-empty and remains distinct from every other string.

A PGM graph is a directed property multigraph. Its Node set contains only
present Concepts. Every Relationship occurrence has a present source Node and
a target Concept ID reference. The target need not be present.

A missing target MUST NOT create a PGM Node and MUST NOT make an otherwise
conforming bundle invalid. A processor MAY expose the derived boolean
`resolved := target Concept ID is present in Nodes`. An adapter MAY materialize
a target-specific placeholder, but that placeholder is not a PGM Node and
MUST be distinguishable from Concept Nodes.

## 4. Concepts as Nodes

Each present non-reserved OKF Concept represents exactly one Node.

The Node identity MUST be the OKF Concept ID: the bundle-relative POSIX-style
path of the Concept file with the exact lowercase `.md` suffix removed. For
example, `people/Alice.md` has Node identity `people/Alice`.

For portable PGM processing, a Concept path MUST NOT contain an empty, `.`, or
`..` segment, a backslash, a C0 control character, or U+007F DELETE. These
restrictions avoid platform-dependent Concept identities while retaining
case-sensitive Unicode names and spaces exactly as authored.

The complete parsed YAML frontmatter Mapping MUST be retained as the Node
Properties. Unknown entries remain ordinary Properties. The required OKF
`type` Property is additionally interpreted as the Node Graph Element Type.
Deriving the Type MUST NOT remove or alter the `type` Property.

```markdown
---
type: Person
name: Alice
age: 42
---
```

This Concept represents one Node whose identity is its Concept ID, whose
Graph Element Type is `Person`, and whose complete Properties are:

```yaml
type: Person
name: Alice
age: 42
```

Reserved `index.md` and `log.md` documents MUST NOT become Nodes.

## 5. Markdown Concept Links as Relationships

### 5.1 Concept Link destinations

After Markdown parsing, a Link destination is a Concept destination only when
all of these rules hold:

1. Interpret the destination as a URI-reference. Its scheme, authority, and
   query components MUST be absent.
2. Its path MUST be non-empty. A fragment-only Link is an intra-document
   navigation Link, not a PGM Concept Link.
3. Before URI parsing, reject an unescaped U+0020 SPACE, C0 control character,
   or U+007F DELETE. Split the URI path into `/`-separated segments and
   percent-decode each segment exactly once as UTF-8. A malformed escape,
   invalid UTF-8, decoded C0 or DELETE character, or a decoded `/` or `\\`
   inside a segment makes it a non-Concept destination. A percent-decoded
   U+0020 SPACE is permitted in a filename.
4. The decoded path MUST end with the exact case-sensitive suffix `.md`.
5. The final segment MUST NOT be the reserved name `index.md` or `log.md`.
6. Resolve a leading `/` from the bundle root and any other path from the
   source Concept document's directory. Remove empty and `.` segments and
   apply `..` segments without permitting traversal above the bundle root.

The fragment component of a path-bearing Concept Link is ignored when deriving
the target Concept ID. Query-bearing Links are not Concept Links. Path text is
case-sensitive and MUST NOT be Unicode-normalized by PGM.

Thus `Other.md#details` refers to Concept ID `Other`, while `#details` alone
does not create a Relationship. A destination that resolves outside the
bundle is not a Concept destination.

### 5.2 Relationship existence, occurrence, and direction

Every Concept Link occurrence in a Concept body represents exactly one
directed Relationship occurrence. Its source is the current Concept ID and its
target is the Concept ID derived under §5.1.

```markdown
[Acme](Acme.md)
```

In a Concept with ID `Alice`, this is one untyped Relationship occurrence from
`Alice` to target reference `Acme`, without Relationship Properties.

Relationship existence MUST NOT depend on Link text, title presence, title
validity, or whether the target Concept is present. A broken Concept Link
therefore remains a Relationship to a not-yet-present Concept ID.

Direction comes entirely from the Markdown source-to-destination Link. PGM has
no incoming marker and no `->` or `<-` syntax. Incoming Relationships are a
query or backlink view.

A conforming Core Result MUST preserve distinct Link occurrences and MUST NOT
coalesce them, even when their source, target, and Properties are equal. Links
in reserved documents, external URI Links, empty destinations, fragment-only
Links, images, and destinations rejected by §5.1 create no PGM Relationship.

### 5.3 Relationship Properties from a Link title

After Markdown title parsing, remove only surrounding YAML separation
characters: U+0020 SPACE, U+0009 TAB, carriage return, and line feed. The
remaining title supplies Relationship Properties if and only if:

1. its first character is `{` and its last character is `}`;
2. the complete title parses under §1.3 as one YAML Flow Mapping; and
3. every outer Mapping key is a string.

The complete parsed Mapping MUST be retained as Relationship Properties. PGM
defines no Property grammar of its own.

```markdown
[Acme](Acme.md "{type: works_for, since: 2024, active: true}")
```

The Relationship has Graph Element Type `works_for` and complete Properties:

```yaml
type: works_for
since: 2024
active: true
```

When `type` is a non-empty string, its value is additionally interpreted as
the Relationship Graph Element Type. Deriving the Type MUST NOT remove or
alter `type` in the Properties.

If `type` is present but is not a non-empty string, the processor MUST preserve
the Property, MUST treat the Relationship as untyped, and SHOULD report a
warning.

Property values MAY be any acyclic YAML value in the profile from §1.3,
including nested sequences and Mappings. A target adapter MAY encode a value
that its native Property model cannot represent; the PGM source remains valid.

### 5.4 Fundamental Relationship cases

All of the following are valid PGM:

| Markdown | Graph Element Type | Complete Properties |
| --- | --- | --- |
| `[Acme](Acme.md)` | absent | `{}` |
| `[Acme](Acme.md "Acme Corporation")` | absent | `{}` |
| `[Acme](Acme.md "{}")` | absent | `{}` |
| `[Acme](Acme.md "{since: 2024}")` | absent | `{since: 2024}` |
| `[Acme](Acme.md "{type: works_for}")` | `works_for` | `{type: works_for}` |
| `[Acme](Acme.md "{type: works_for, since: 2024}")` | `works_for` | `{type: works_for, since: 2024}` |

An untyped Relationship has no Graph Element Type. A processor MUST NOT invent
a type such as `UNTYPED` or `RELATED_TO` in the Core Result.

A bare Link and a Link annotated with `{}` have equal graph values but remain
separate Relationship occurrences when both are present.

### 5.5 Ordinary titles and unusable annotations

A title that does not begin with `{` after those surrounding characters are
removed is an ordinary Markdown title. It supplies no Relationship Properties
and requires no diagnostic.

A brace-leading title that fails any §5.3 condition is likely intended as PGM
metadata. The processor MUST preserve the baseline Relationship occurrence,
MUST attach an empty Relationship Property map, MUST NOT partially recover
Properties, and SHOULD report a warning. The warning does not make the PGM
Core Bundle non-conforming.

An application MAY promote the warning to an application policy failure, but
MUST NOT report that stricter policy as PGM Core conformance.

### 5.6 OKF-named Relationship Properties

A Relationship is not an OKF Concept. A Relationship Property whose name also
appears in OKF Concept frontmatter is an ordinary PGM Property. PGM MUST
preserve it but MUST NOT automatically apply Concept-specific OKF provenance,
trust, lifecycle, or attestation semantics to it.

Additional profiles MAY define such semantics. They MUST identify themselves
and MUST NOT silently change PGM Core conformance.

## 6. Portable Relationship Identification Profile

PGM Core defines Relationship occurrences but does not require a technical
Relationship ID. This section defines the optional, normative **PGM Portable
Relationship Identification Profile v1** for JSON exchange, deterministic
database loading, comparison, and deduplicated application views.

Applying this profile MUST NOT remove or coalesce Core Relationship
occurrences. It assigns two values:

- `relationship_key` identifies a semantic assertion value; equal occurrences
  may share it.
- `relationship_id` identifies one occurrence within a parsed bundle snapshot.

### 6.1 Canonical PGM Value v1

The profile converts the complete Relationship Property map into a
collision-free JSON value called **Canonical PGM Value v1**. Every source
value is explicitly tagged, so an authored Mapping cannot collide with an
encoding envelope.

The self-describing document is
`["pgm-yaml", "v1", tagged-value]`. Each `tagged-value` is a JSON Array
whose first item is a kind name:

```text
null                  -> ["null"]
boolean               -> ["bool", true | false]
integer or float      -> ["number", canonical-number]
string                -> ["string", exact-Unicode-string]
binary                -> ["binary", canonical-base64]
date                  -> ["date", YYYY-MM-DD]
timestamp             -> ["timestamp", canonical-ISO-8601]
sequence              -> ["sequence", [encoded-item, ...]]
mapping               -> ["mapping", [[encoded-key, encoded-value], ...]]
set                   -> ["set", [encoded-item, ...]]
```

Finite numbers use a reduced rational string: `n` when the denominator is 1,
otherwise `n/d`, with a positive denominator. YAML integers are arbitrary
precision. YAML floats are interpreted as IEEE 754 binary64 before conversion
to the exact rational value. `-0` is canonicalized as `0`; non-finite values
use `nan`, `+inf`, and `-inf`. Consequently integer `1` and float `1.0` are
equivalent, while booleans remain distinct from numbers.

Mapping entries are sorted by the lexicographic byte order of the RFC 8785
serialization of each encoded key; equal encoded keys are an error. Sequence
order is preserved. Set items are sorted by their RFC 8785 bytes. Acyclic
aliases are expanded by value and cycles are errors.

Unicode strings are preserved exactly and are not normalized. Lone Unicode
surrogates are errors. Binary values use RFC 4648 base64 with padding.
Timestamp normalization MUST distinguish timezone-free values from instants;
timezone-aware values are normalized to UTC with `Z`. Date and timestamp years
always contain four digits in the range 0001 through 9999; timestamp fractions
contain one through six digits with trailing zeroes removed.

### 6.2 Semantic relationship key

Construct this JSON Array, where the final item is the complete self-describing
Canonical PGM Value document:

```json
[
  "pgm-relationship-key",
  "v1",
  "people/Alice",
  "organizations/Acme",
  ["pgm-yaml", "v1", ["mapping", []]]
]
```

Serialize it using the
[JSON Canonicalization Scheme (JCS), RFC 8785](https://www.rfc-editor.org/rfc/rfc8785),
encode the result as UTF-8, and calculate SHA-256 as specified by
[FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final). The key is:

```text
pgmkey:v1:sha256:<64 lowercase hexadecimal digits>
```

Link text, an ordinary title, a destination fragment, source formatting, and
YAML Mapping order are excluded. The complete Property map, including an
authored `type`, is included.

### 6.3 Relationship occurrence ID

For an occurrence with a given `relationship_key`, determine its zero-based
`occurrence` number by counting preceding Concept Link occurrences in the same
source document with the same `relationship_key`.

Construct and canonicalize this Array:

```json
[
  "pgm-relationship-id",
  "v1",
  "pgmkey:v1:sha256:...",
  "0"
]
```

The ID is:

```text
pgmrel:v1:sha256:<64 lowercase hexadecimal digits>
```

Distinct but identical Link occurrences therefore share a semantic key and
receive distinct occurrence IDs. Reordering unrelated Links does not change
their IDs. No derived occurrence ID can remain attached to one of several
indistinguishable duplicate Links across arbitrary edits; persistent mutable
identity requires an application-level authored ID or database surrogate.

Both identifiers are bundle-relative. A system containing multiple bundles
MUST scope them with an external bundle identifier, for example by treating
the pair `(bundle_id, relationship_id)` as the effective identity.

### 6.4 Profile conformance

An implementation claiming this profile MUST produce exactly the JCS bytes,
keys, occurrence numbering, and IDs defined above. A hash collision detected
between different canonical preimages MUST be reported as an error and MUST
NOT silently merge Relationships.

## 7. Processing and conformance

### 7.1 Conformance classes

PGM 0.4.0 defines these conformance classes:

- A **PGM Core Bundle** conforms when it conforms to the pinned OKF 0.2
  specification and all applicable PGM Core source requirements in §§1–5.
- A **PGM Core Result** conforms when it contains exactly the Nodes and
  Relationship occurrences required by §§3–5, including unresolved target
  references and complete Property maps.
- A **PGM Core Processor** conforms when it accepts every conforming Core
  Bundle, produces a conforming Core Result, and does not narrow the result for
  an export target.
- A **Portable Relationship Identification Processor** conforms when it is a
  Core Processor and additionally satisfies §6.
- A **PGM JSON Exchange Processor** conforms when it is a Portable
  Relationship Identification Processor and additionally exports and imports
  PGM JSON Exchange Profile v1 documents according to §8.1.
- A **PGM Adapter** conforms when it consumes a conforming Core Result,
  identifies its target and mapping, and does not reinterpret a target
  limitation as a Core Bundle error.

### 7.2 Required processing

A conforming Core Processor MUST perform the logical equivalent of:

1. validate the Knowledge Bundle against the pinned OKF baseline;
2. parse Concept frontmatter using §1.3;
3. create one Node for every present non-reserved Concept;
4. retain complete Node Properties and derive the Node Type from `type`;
5. parse each Concept body with the declared Markdown profile;
6. identify Concept Link destinations using §5.1;
7. create one Relationship occurrence for every Concept Link occurrence;
8. retain unresolved target Concept ID references without creating Nodes;
9. parse an eligible complete title Mapping under §5.3, retain its complete
   Properties, and derive its optional Type; and
10. otherwise retain empty Relationship Properties and issue only the warning
    permitted by §5.5.

This is a logical procedure, not a required API or AST shape.

### 7.3 Diagnostics

An **error** is a violation of Core Bundle conformance. A processor MUST NOT
claim a conforming Core Result while an error remains.

A **warning** is non-fatal and MUST NOT remove or alter a required Node or
Relationship occurrence. Ordinary titles and non-Concept Links require no
warning.

An **adapter error** reports that a conforming Core Result cannot be mapped to
a target under the selected adapter policy. It MUST NOT change the Core Bundle
or Core Result conformance status.

Processors SHOULD expose stable machine-readable diagnostic codes in addition
to human-readable messages.

### 7.4 Conformance statements

A reproducible conformance statement MUST identify:

- `PGM 0.4.0 Public Draft` and every claimed conformance class;
- the exact OKF commit and hash from §1.1;
- Markdown profile and version;
- YAML version, schema, supported explicit tags, and alias policy;
- processor name and version; and
- errors, warnings, and adapter errors as separate categories.

A JSON exchange conformance statement MUST additionally identify
`PGM JSON Exchange Profile v1` and the exact schema revision used.

## 8. Interoperability and adapters

PGM-aware authors add machine-readable Relationship Properties through a
standard Markdown title containing YAML. Tools without PGM support continue to
process the same source as ordinary OKF, Markdown, and YAML.

The PGM JSON exchange format and the Cypher projection are adapters, not PGM
syntax. An adapter SHOULD retain technical identifiers separately from
authored Properties and SHOULD use Canonical PGM Value v1 wherever a target's
native values cannot represent the complete YAML value model.

### 8.1 PGM JSON Exchange Profile v1

The optional, normative **PGM JSON Exchange Profile v1** serializes one
conforming PGM Core Result as a JSON Object. Its media-type-neutral format
identifier is `pgm-graph` and its `formatVersion` is the JSON string `1`.
The versioned JSON Schema in
[`interop/pgm-graph.schema.json`](interop/pgm-graph.schema.json) defines the
exchange document shape. An implementation claiming this profile MUST satisfy
both that schema and the semantic requirements in this section.

The top-level `nodes` Array contains only present PGM Nodes. The top-level
`relationships` Array contains every Relationship occurrence, including an
occurrence whose target Concept is absent. For every Relationship, `resolved`
MUST be true if and only if its `target` equals the ID of an item in `nodes`.
An importer MUST NOT turn an unresolved target into a PGM Node.

Every Node and Relationship `properties` member MUST contain the complete
self-describing Canonical PGM Value v1 document from §6.1. This representation
is used instead of an ordinary JSON Object so that binary values, timestamps,
sets, non-string nested Mapping keys, arbitrary-size integers, and non-finite
numbers round-trip without type loss. Import reconstructs the canonical PGM
value; YAML presentation details such as comments, styles, anchors, aliases,
and Mapping order are intentionally outside the Core Result and do not
round-trip.

An importer MUST reject duplicate Node IDs or Relationship IDs, a Relationship
whose source Node is absent, an inconsistent `resolved` flag, a derived `type`
that disagrees with the decoded complete Properties, a non-canonical Property
encoding, or a §6 key, occurrence ordinal, or ID that does not verify against
the imported content. Unknown members are rejected unless a later exchange
format version explicitly defines them. Importing and re-exporting a valid
version 1 document without modifying its Core Result MUST reproduce its
`nodes`, `relationships`, and `diagnostics` data models. The new envelope
identifies the re-exporting processor, so producer metadata MAY change. A
deterministic implementation re-exporting its own document SHOULD reproduce
the same UTF-8 bytes.

Conformance metadata identifies the PGM draft, immutable OKF baseline,
Markdown profile, and YAML profile used to create the result. Diagnostics in
an exchange document MUST contain warnings only: a graph with a Core error is
not a conforming Core Result and MUST NOT be exported as a conforming PGM JSON
Exchange document.

The `conformance` Object MUST contain `PGM Core Processor`, `Portable
Relationship Identification Processor`, and `PGM JSON Exchange Processor` in
its `classes` Array; `processorName` and `processorVersion`; the profile and
schema identifiers; the pinned OKF commit and specification hash; the named
Markdown and YAML profiles; the supported explicit YAML tag URIs, including
all three portable tags from §1.3; the acyclic-alias and cycle policy; and
distinct `error`, `warning`, and `adapter-error` diagnostic categories.
`classes` and `yamlExplicitTags` are unordered sets of unique non-empty
strings. They MAY include additional truthful implementation capabilities;
those additions do not extend the portable PGM value model of this document.
Version 1 fixes the Object members and rejects unknown members so that a
consumer can reproduce the complete conformance statement from the document.

Node `id`, `type`, and `properties` carry the Core Node identity, derived Type,
and complete Properties. Relationship `source`, `target`, `type`, and
`properties` carry the corresponding Core values; `id`, `relationshipKey`, and
`occurrence` carry §6 values. `linkText` and nullable `title` preserve the
parsed Markdown Link label and title as exchange metadata but do not affect
Relationship identity. JSON Object member order and the order of the `nodes`,
`relationships`, and `diagnostics` Arrays have no graph semantics. An importer
MAY reorder them; the reference exporter emits a deterministic order.

### 8.2 Cypher projection

For Cypher targets, a generic native Relationship Type plus a nullable or
optional stored PGM Type can represent both typed and untyped PGM
Relationships. An adapter that instead projects PGM Types to native
Relationship Types MUST report untyped Relationships as an adapter limitation,
not a Core error.

The repository's Cypher projection uses explicitly marked target placeholders
when a target Concept is absent. Such placeholders are adapter artifacts, not
PGM Nodes. Its generic label, generic native Relationship Type, and technical
field names are informative mapping choices. Its portable Relationship keys
and IDs nevertheless conform to §6, and the embedded Property JSON uses §6.1.

## 9. Migration from earlier drafts

Earlier PGM drafts used classified Link expressions such as:

```markdown
[Acme](:WORKS_FOR {since: 2024} -> Acme.md)
```

The canonical replacement is a normal Markdown destination and, when metadata
is needed, a YAML Flow Mapping in the normal Markdown title:

```markdown
[Acme](Acme.md "{type: works_for, since: 2024}")
```

PGM 0.4.0 removes:

- `:RELATIONSHIP_TYPE` declarations in favor of the retained YAML `type`
  Property;
- PGM-specific Property expressions outside a Link title;
- authored arrow and incoming-link markers;
- node annotations in Link text; and
- a PGM Relationship lexer or parser grammar.

Ordinary Concept Links require no migration: every occurrence is already an
untyped OKF Relationship assertion. Adding a valid YAML title enriches that
occurrence; it does not opt the Link into the graph.

PGM 0.3 implementations that coalesced equal Links MUST preserve each Link
occurrence in their 0.4 Core Result. They MAY expose the shared §6
`relationship_key` as a deduplicated application view.

## 10. Security and resource considerations

Processors MUST use safe YAML construction and MUST NOT instantiate arbitrary
objects from tags. They SHOULD impose documented resource limits for YAML
aliases, nesting, Markdown size, and graph size.

Path resolution MUST apply §5.1 before filesystem access and MUST prevent
bundle-root traversal, including traversal hidden by percent-encoding.

Portable Relationship hashes identify canonical content; they do not prove
authorship, integrity, authorization, or trust. Applications requiring those
properties need an authenticated transport or signature profile.

The complete design is:

> OKF provides Concepts and Link assertions. Markdown represents the Links.
> YAML provides Properties. PGM interprets every Concept Link occurrence as a
> Property Graph Relationship.
