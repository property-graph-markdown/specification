# PGM Schema 0.4.0 Public Draft

## 1. Scope

PGM Schema is a prototype-based schema profile for OKF Knowledge Bundles with
Property Graph Markdown (PGM) relationships.

PGM Schema adds no syntax. It gives schema meaning to ordinary OKF concepts
whose frontmatter has exactly this modeling-role marker:

```yaml
type: Prototype
```

Each Prototype concept specifies one graph type. Its OKF Concept ID is the
name of that type. Its remaining frontmatter entries are prototype values for
attributes of the type's instances, not attributes of the type itself. Its PGM
relationships prototype the relationships that instances of the type may
have.

PGM Schema replaces separate meta-ontologies, definition kinds, property-key
registries, relationship-type registries, domain declarations, and range
declarations with this single prototype rule.

The key words `MUST`, `MUST NOT`, `SHALL`, `SHOULD`, and `MAY` are to be
interpreted as described in RFC 2119.

## 2. Normative bases

A PGM Schema bundle SHALL conform to OKF 0.2 and PGM 0.4.0.

OKF defines Knowledge Bundles, concept documents, Concept IDs, YAML
frontmatter, reserved `index.md` and `log.md` documents, and Concept Links.
PGM interprets every Concept as a Node and every Concept Link as a directed
typed or untyped Relationship. A complete YAML Flow Mapping title optionally
enriches a Relationship with Properties and a derived Type.

PGM Schema changes none of those meanings. It only interprets a bundle of
`Prototype` concepts as a schema for another OKF/PGM bundle.

## 3. Core rule

For every non-reserved concept document `c` in a schema bundle:

```text
frontmatter(c).type = "Prototype"
typeName(c) = conceptID(c)
```

An OKF Concept ID is the bundle-relative POSIX-style path of the concept file
with the `.md` suffix removed. Therefore:

```text
people/Person.md  ->  people/Person
Place.md          ->  Place
```

The `type: Prototype` value describes the document's modeling role. It is not
the name of the type being specified and it is not an attribute of that type's
instances. No `identifier` field is used.

Type names are case-sensitive and path-sensitive. A type reference SHALL equal
the complete Concept ID. `Person`, `people/Person`, and `people/person` are
three different type names.

## 4. Prototype model

Let a schema bundle denote:

```text
S = (T, A, R, P)
```

where:

- `T` is the finite set of Type names, equal to the Concept IDs of all
  Prototype concepts in the schema bundle;
- `A : T -> P(String)` maps each Type to its permitted node-attribute keys;
- `R` is a set of permitted relationship signatures
  `(sourceType, relationshipType?, targetType)`, where the Relationship Type
  may be absent; and
- `P : R -> P(String)` maps each relationship signature to its permitted data
  Property keys, excluding the structural `type` key.

`P(X)` denotes the power set of `X`.

Example values may accompany entries in `A` and `P`, but they are not part of
the conformance predicates. PGM Schema defines structure by key presence, not
datatypes or value equality.

## 5. Schema bundle

### 5.1 Bundle boundary

A schema SHALL be supplied as one explicit OKF Knowledge Bundle root.
Subdirectories MAY organize Prototype concepts and become part of their Type
names.

Every non-reserved concept in that bundle SHALL have `type: Prototype`.
Reserved OKF `index.md` and `log.md` documents MAY occur and do not specify
Types.

The bundle SHALL contain at least one Prototype concept.

### 5.2 Type names

The Type name is derived only from the Concept ID. A processor SHALL NOT derive
it from a heading, title, filename stem alone, `identifier`, prose, tags, or a
relationship.

Because OKF Concept IDs are unique within a bundle, no additional Type
identifier registry or namespace directory is required.

The first level-one heading SHOULD equal the final path segment of the Concept
ID, preserving its exact spelling. For example, `people/Person.md` SHOULD
begin its body with `# Person`. This heading is a human-readable reflection of
the Concept ID only; it does not define or override the complete Type name
`people/Person`.

### 5.3 Attribute prototypes

For a Prototype concept `c`, every top-level frontmatter entry except `type`
declares one permitted attribute of instances of `typeName(c)`:

```text
A(typeName(c)) = keys(frontmatter(c)) - {type}
```

There is no separate distinction between OKF metadata keys and domain
attribute keys in a prototype. If `title`, `description`, `tags`, `sources`,
or another OKF field is present, that key is also declared as an attribute of
the specified Type's instances. A prototype's display name therefore belongs
in its first H1 rather than in a special frontmatter `name` field.

An author declares an attribute without an example value by assigning YAML
`null`:

```yaml
born: null
```

Any other valid PGM/OKF YAML value is an example:

```yaml
full_name: Ada Lovelace
interests: [mathematics, music]
address: {city: London, country: UK}
```

Example values are informative. A processor SHALL NOT infer a datatype,
requiredness, enumeration, default, nested schema, or value constraint from
them.

### 5.4 Relationship prototypes

Every PGM Relationship authored in a Prototype concept declares one permitted
relationship signature.

For a Concept Link in Prototype concept `s`:

```markdown
[Target](../places/Place.md "{type: born_in, year: 1815}")
```

- the Source Type is `typeName(s)`;
- the Relationship Type is the PGM Graph Element Type `born_in`;
- the link destination SHALL resolve to another Prototype concept `t` in the
  same schema bundle;
- the Target Type is `typeName(t)`; and
- every YAML Mapping entry except structural `type` is a permitted data
  Property for that signature.

Core PGM still retains `type` in the complete Relationship Property map. PGM
Schema projects that retained value into the relationship signature and
excludes only that key from `P`; it does not mutate the PGM source or AST.

A relationship property with YAML `null` is declared without an example. Any
other value is informative example data. Values do not constrain instances.

The same Relationship Type MAY occur on several Source Types and MAY point to
several Target Types. Source and Target constraints are implicit in the
prototype link; no domain or range declarations exist.

After PGM semantic-key coalescing, a conforming schema SHALL contain at most
one prototype relationship for a given
`(sourceType, relationshipType, targetType)` signature. Authors SHALL combine
all permitted relationship-property keys into that one relationship.

An unannotated Concept Link or a Concept Link with an ordinary title prototypes
an untyped Relationship without data Properties. A Flow Mapping title without
`type` prototypes an untyped Relationship with data Properties. An empty Flow
Mapping is equivalent to the unannotated link. PGM Schema MUST NOT invent a
Type.

## 6. Instance-bundle conformance

An instance bundle conforms to a schema `S` when it conforms to OKF and PGM
and all rules in this section hold. The schema and instance bundle roots are
independent; Type names always come from Concept IDs in the schema bundle.

### 6.1 Node Types

For every non-reserved instance concept `v`:

```text
frontmatter(v).type in T
```

The value SHALL equal a complete Type name exactly. The instance concept's own
Concept ID does not determine its Type.

### 6.2 Node attributes

For every instance concept `v`:

```text
keys(frontmatter(v)) - {type} subset-of A(frontmatter(v).type)
```

Prototype attributes are permitted, not required. Instance values need not
equal prototype example values and need not have the same YAML value shape.

### 6.3 Relationships

Every PGM relationship target SHALL resolve to an instance concept within the
validation scope. For every instance relationship `e`, this signature SHALL
exist in `R`:

```text
(
  frontmatter(source(e)).type,
  relationshipType(e),
  frontmatter(target(e)).type
) in R
```

Thus one prototype link simultaneously specifies the permitted Relationship
Type, its Source Type, and its Target Type.

### 6.4 Relationship properties

For every instance relationship `e` with matching signature `r`:

```text
keys(properties(e)) - {type} subset-of P(r)
```

Prototype relationship properties are permitted, not required. Their example
values impose no value constraints. The retained `type` Property is checked by
the relationship-signature rule rather than as a free data Property.

### 6.5 Closed structural interpretation

PGM Schema is closed for structural names: undeclared Types, node attributes,
relationship signatures, and relationship properties are errors.

It is open for presence and values: declared attributes, relationships, and
relationship properties are optional, and their values are unconstrained.

## 7. Conformance classes

This specification defines three conformance classes:

- A **schema bundle** conforms when every concept is a valid `Prototype`
  concept and every prototype relationship resolves unambiguously inside the
  bundle.
- An **instance bundle** conforms relative to one conforming schema bundle
  when all of its graph structure matches the prototypes.
- A **PGM Schema processor** conforms when it applies the deterministic
  procedure below and never reports a non-conforming bundle as conforming.

A processor MAY validate a schema without an instance bundle. It SHALL
validate the schema successfully before using it to validate instances.

## 8. Deterministic processing

A conforming processor SHALL:

1. receive an explicit schema-bundle root;
2. validate that bundle as OKF and PGM;
3. exclude reserved OKF documents;
4. require `type: Prototype` on every remaining concept;
5. derive `T` from the concepts' bundle-relative Concept IDs;
6. derive `A` from all frontmatter keys except `type`;
7. resolve every PGM prototype Relationship, including ordinary Concept Links,
   to a Prototype concept in the same bundle;
8. derive `R` and `P` from the resolved prototype links and reject duplicate
   signatures;
9. when an instance bundle is supplied, validate its node Types, attributes,
   relationship signatures, targets, and relationship-property keys; and
10. report conformance only when no error remains.

A processor SHOULD report the source Concept ID, offending key or
relationship signature, and expected prototype in each diagnostic.

## 9. Canonical authoring pattern

A Prototype concept needs no definition scaffolding beyond ordinary OKF,
Markdown, and YAML:

```markdown
---
type: Prototype
full_name: Ada Lovelace
born: null
---

# Person

Represents a person.

A person may be born in a
[place](../places/Place.md "{type: born_in, year: 1815}").
```

If this file is `people/Person.md`, it specifies Type `people/Person` with
permitted instance attributes `full_name` and `born`, plus this relationship
prototype:

```text
(people/Person)-[:born_in {year}]->(places/Place)
```

The first H1 reflects the local Type name `Person`. The prose and heading
document the Type for people and agents but do not add schema constraints.

## 10. Non-goals

PGM Schema 0.4.0 has no:

- M2 or M2* meta-ontology;
- Node Label, Property Key, or Relationship Type definition classes;
- separate identifiers or symbol registries;
- domain or range declaration vocabulary;
- datatypes, required attributes, defaults, cardinalities, or uniqueness;
- inheritance, imports, inference, inverses, or global Linked Data identity;
- schema semantics in headings, prose, non-Concept Links, or filenames beyond
  their OKF Concept IDs.

Additional profiles MAY add constraints, but they SHALL identify themselves
separately and SHALL NOT change a PGM Schema 0.4.0 conformance result silently.

## 11. Conformance statement

A reproducible conformance result SHOULD identify:

- OKF version `0.2`;
- PGM version `0.4.0`;
- PGM Schema version `0.4.0`;
- the schema-bundle root and exact Type Concept IDs; and
- the instance-bundle root and exact validation scope, if supplied.
