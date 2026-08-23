# Property Graph Markdown (PGM) 0.4.0 Public Draft

## 1. Scope

Property Graph Markdown (PGM) is a semantic profile of Open Knowledge Format
(OKF), Markdown, and YAML for representing property graphs.

PGM defines a property-graph interpretation of OKF Concepts, Markdown Links,
and YAML metadata without introducing additional Markdown syntax.

> PGM adds graph semantics, not syntax.

The responsibilities of the base formats are separate:

- OKF defines Knowledge Bundles, Concepts, Concept IDs, and concept documents.
- Markdown defines document structure, Link text, destinations, and titles.
- YAML defines metadata mappings and structured Property values.
- PGM defines how those existing constructs map to Nodes, Relationships,
  Properties, and Graph Element Types.

Every PGM Knowledge Bundle MUST conform to OKF 0.2. PGM uses CommonMark 0.31.2
as the reference grammar for canonical Markdown Links. An implementation MAY
support another Markdown profile when its parsed Link model exposes equivalent
text, destination, and title fields. PGM MUST NOT replace Markdown or YAML with
a PGM-specific Link lexer or Property grammar.

The normative OKF 0.2 text is `okf/SPEC.md` from
`GoogleCloudPlatform/knowledge-catalog` at commit
`3fcbb9f828c2f23d109c855ee403c3a4c81f3a96`, with SHA-256
`5a3311d270bebb16d558010e75064f5b75323f284992641732b1c8097511f948`.

The key words `MUST`, `MUST NOT`, `SHALL`, `SHOULD`, and `MAY` are to be
interpreted as described in RFC 2119.

## 2. Design principles

PGM is governed by these principles:

- **Zero new Markdown syntax.** Every PGM document uses syntax already defined
  by Markdown and YAML.
- **Graceful degradation.** A processor without PGM support still sees an OKF
  bundle containing ordinary Markdown documents and Links.
- **Semantic enrichment.** PGM preserves the OKF graph and enriches existing
  constructs rather than replacing or filtering their meaning.
- **Symmetry.** Nodes and Relationships both receive complete YAML Property
  maps and both derive their optional Graph Element Type from `type`.
- **Human readability.** PGM files remain normal Markdown files with normal
  YAML metadata and Link titles.
- **Tool interoperability.** Implementations SHOULD compose existing OKF,
  Markdown, and YAML processors.
- **Lossless core.** Target-specific restrictions belong to exporters and
  additional validation profiles, not to the PGM source model.

## 3. Terminology and graph model

This specification uses the following terms:

- **Concept:** an OKF Concept, represented by one concept document.
- **Node:** the Property Graph interpretation of a Concept.
- **Link:** a Link parsed according to the applicable Markdown profile.
- **Concept Link:** a Link whose destination resolves, or is intended to
  resolve, to a Concept ID under the OKF path rules.
- **Relationship:** the Property Graph interpretation of a Concept Link.
- **Node Properties:** the complete YAML frontmatter mapping of a Concept.
- **Relationship Properties:** the complete YAML Flow Mapping in a Link title,
  when the title is such a mapping.
- **Graph Element Type:** the string value additionally derived from the
  `type` Property of a Node or Relationship.

A PGM graph is a directed property graph whose Nodes have stable OKF Concept
IDs, whose Relationships may be typed or untyped, and whose Property values
are YAML values.

PGM is a monotone interpretation of OKF: every OKF Concept becomes a Node and
every OKF Concept Link becomes a Relationship. YAML annotations MAY add graph
semantics but MUST NOT remove the baseline Node or Relationship.

## 4. Concepts as Nodes

Each non-reserved OKF Concept represents exactly one Node.

The Node identity MUST be the OKF Concept ID: the bundle-relative POSIX-style
path of the concept file with the `.md` suffix removed. For example,
`people/Alice.md` has Node identity `people/Alice`.

The complete parsed YAML frontmatter mapping MUST be retained as the Node
Properties. PGM makes no additional distinction between OKF metadata and
domain Properties.

The required OKF `type` Property is additionally interpreted as the Node's
Graph Element Type. Deriving the Graph Element Type MUST NOT remove or alter
the `type` entry in the Node Properties.

Normative example:

```markdown
---
type: Person
name: Alice
age: 42
---
```

The Node has the Concept ID as identity, Graph Element Type `Person`, and these
Node Properties:

```yaml
type: Person
name: Alice
age: 42
```

OKF `index.md` and `log.md` files are reserved documents and MUST NOT become
Nodes.

## 5. Markdown Concept Links as Relationships

### 5.1 Relationship existence and direction

Every Concept Link in a Concept body represents one directed Relationship.
The source is the current Concept and the target is the Concept ID obtained by
resolving the Link destination under the OKF path rules.

```markdown
[Acme](Acme.md)
```

In a Concept with ID `Alice`, this represents an untyped Relationship from
`Alice` to `Acme` without Relationship Properties.

Relationship existence MUST NOT depend on Link text, a Link title, or whether
the title contains YAML. Link text is the human-readable representation of the
target and does not define a Relationship Type by default.

Direction is supplied entirely by Markdown's source-to-destination Link
structure. PGM defines no incoming marker and no `->` or `<-` syntax. Incoming
Relationships are obtained by inverse graph traversal or backlinks.

Absolute bundle-relative and relative Concept Links MUST be resolved as
defined by OKF. A fragment-only destination refers to the current Concept. A
broken Concept Link remains a Relationship to its resolved, not-yet-present
Concept ID and MUST NOT make the PGM document invalid.

Links to external URIs, empty destinations, images, and Links in reserved OKF
documents do not link one Concept to another and therefore do not create PGM
Relationships.

### 5.2 Relationship Properties from a Link title

After Markdown parsing, a processor MUST interpret a Link title as a
Relationship Property map if and only if the complete title, allowing
surrounding YAML whitespace, successfully parses as one YAML Flow Mapping
whose outer keys are strings.

The complete parsed mapping MUST be retained as the Relationship Properties.
PGM defines no Property grammar of its own.

```markdown
[Acme](Acme.md "{type: works_for, since: 2024, active: true}")
```

This Relationship has Graph Element Type `works_for` and these Relationship
Properties:

```yaml
type: works_for
since: 2024
active: true
```

When `type` is a non-empty string, its value is additionally interpreted as
the Relationship's Graph Element Type. Deriving that Type MUST NOT remove or
alter `type` in the Relationship Properties.

If `type` is present but is not a non-empty string, the processor MUST preserve
the Property, MUST treat the Relationship as untyped, and SHOULD report a
non-fatal diagnostic.

The outer YAML Mapping keys MUST be strings because they are Property names.
Property values MAY be any YAML value accepted by the YAML processor used for
the OKF bundle, including scalars, sequences, mappings, and recursively nested
combinations:

```markdown
[Acme](Acme.md "{type: works_for, roles: [architect, developer], context: {team: platform}}")
```

PGM MUST NOT reject a Property value merely because a graph database, query
language, or serialization target cannot represent it. Mapping, encoding, or
rejecting unsupported values is an exporter or additional-profile concern.

### 5.3 Fundamental Relationship cases

The following cases are all valid PGM.

Untyped Relationship without Properties:

```markdown
[Acme](Acme.md)
```

Untyped Relationship with Properties:

```markdown
[Acme](Acme.md "{since: 2024}")
```

Typed Relationship without other Properties:

```markdown
[Acme](Acme.md "{type: works_for}")
```

Typed Relationship with additional Properties:

```markdown
[Acme](Acme.md "{type: works_for, since: 2024}")
```

An untyped Relationship has no Graph Element Type. A processor MUST NOT invent
a type such as `UNTYPED` or `RELATED_TO`.

An empty Flow Mapping is valid and supplies an empty Relationship Property
map. It is graph-semantically equivalent to the same Concept Link without a
title:

```markdown
[Acme](Acme.md "{}")
```

### 5.4 Ordinary titles and invalid Flow Maps

A title that does not parse completely as a YAML Flow Mapping remains an
ordinary Markdown title. It supplies no Relationship Properties, but the
Concept Link still creates an untyped Relationship.

```markdown
[Acme](Acme.md "Acme Corporation")
```

This rule also applies to a title that begins with `{` but is not a valid YAML
Flow Mapping, or whose outer Mapping keys are not strings. The processor MUST
preserve the title, MUST create the baseline Relationship, and MUST NOT
partially recover Properties from the unusable mapping. It SHOULD report a
non-fatal diagnostic so that authors can detect a likely annotation error. A
stricter application MAY promote that diagnostic to an application-level
error, but the source remains conforming PGM.

The title delimiters and escaping remain Markdown concerns. Canonical PGM
examples use straight ASCII quotation marks. After Markdown parsing removes
the title delimiters and resolves Markdown escapes, PGM supplies the complete
title value to the YAML parser.

### 5.5 OKF-named Properties on Relationships

A Relationship is not an OKF Concept. A Relationship Property whose name also
appears in OKF Concept frontmatter is therefore an ordinary YAML Property in
the PGM core. PGM MUST preserve it but MUST NOT automatically apply the
OKF-Concept-specific meaning or validation rules to it.

Additional profiles MAY define provenance, trust, lifecycle, attestation, or
other semantics for Relationships. Such profiles MUST identify themselves
separately and MUST NOT change core PGM conformance silently.

## 6. Relationship identity

The semantic key of a Relationship is:

```text
(source Concept ID, target Concept ID, canonical(complete Relationship Properties))
```

The complete Property map includes `type` when authored. Link text and an
ordinary, non-YAML Link title are not part of the key.

Scalar kinds and values are preserved during canonicalization. Numerically
equivalent integer and floating-point values compare as equivalent, while
booleans remain distinct from numbers. Mapping-key order and unordered YAML
collection presentation do not affect the key; sequence order is preserved.

Equal Relationships MAY be coalesced. Consequently a bare Link and the same
Link annotated with `{}` MAY coalesce. Relationships with different Property
maps remain distinct. PGM does not require an authored technical Relationship
ID.

## 7. Processing and conformance

A conforming PGM processor MUST perform the logical equivalent of these steps:

1. validate and read the OKF Knowledge Bundle;
2. identify non-reserved OKF Concepts and their Concept IDs;
3. parse Concept frontmatter with the bundle's YAML processor;
4. create one Node per Concept, retain the complete frontmatter mapping as its
   Node Properties, and derive its Graph Element Type from `type`;
5. parse each Concept body with a Markdown parser;
6. identify Links whose destinations are OKF Concept Links;
7. create one outgoing Relationship for every Concept Link;
8. preserve Link text and title in the source representation;
9. when the complete title parses as a YAML Flow Mapping, retain the complete
   mapping as Relationship Properties and derive the optional Graph Element
   Type from `type`; and
10. otherwise retain an empty Relationship Property map and optionally report
    a non-fatal diagnostic for a title that appears intended as YAML.

This sequence is architectural guidance, not a requirement to expose a
particular parser API or AST.

A logical Relationship representation will commonly contain:

```text
source
target
label
title
type?       # derived from properties["type"] when it is a non-empty string
properties  # complete YAML Flow Mapping, including type when present
```

The AST shape above and all database export examples are non-normative.

## 8. Progressive enhancement and interoperability

PGM is an OKF-compatible progressive enhancement. A normal OKF Knowledge
Bundle already supplies Concepts, YAML metadata, and directed untyped Concept
Links. Under PGM those constructs retain their OKF meaning and additionally
receive a Property Graph interpretation.

PGM-aware authors MAY add machine-readable Relationship Properties through a
standard Markdown Link title containing YAML. OKF and Markdown tools that do
not implement PGM still process the same source as ordinary frontmatter and
Links. No source preprocessing or graph opt-in is required.

Concrete exports such as Cypher or Neo4j are adapters, not PGM syntax. An
adapter MAY reject or explicitly map untyped Relationships, composite YAML
values, or Graph Element Types that its target cannot represent. Such a
restriction does not make the PGM source invalid.

## 9. Migration from earlier drafts

Earlier PGM drafts defined classified Link expressions such as:

```markdown
[Acme](:WORKS_FOR {since: 2024} -> Acme.md)
```

or placed `:TYPE {properties}` in Link text or titles. Those constructs require
a PGM-specific relationship grammar. The canonical replacement uses a normal
Markdown destination and, when metadata is needed, a YAML Flow Mapping as the
normal Markdown title:

```markdown
[Acme](Acme.md "{type: works_for, since: 2024}")
```

The following earlier features are not part of PGM 0.4.0:

- `:RELATIONSHIP_TYPE` declarations: replaced by the YAML `type` Property;
- PGM-specific `{...}` expressions outside a Link title: replaced by YAML
  frontmatter for Nodes and a YAML Flow Mapping title for Relationships;
- authored `->` and `<-` markers: replaced by Markdown Link direction and
  inverse traversal or backlinks;
- node annotations in Link text: replaced by OKF Concept frontmatter; and
- PGM relationship lexer/parser productions: replaced by Markdown and YAML
  parsing followed by the semantic mappings in this specification.

Ordinary Concept Links require no migration: they are untyped Relationships,
consistent with OKF. Adding a YAML Flow Mapping title enriches an existing
Relationship; it does not opt the Link into the graph.

The complete design can be summarized as:

> OKF provides Concepts. Markdown provides Links. YAML provides Properties.
> PGM turns them into a Property Graph.
