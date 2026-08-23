# PGM Schema

PGM Schema is prototype modeling for OKF Knowledge Bundles with PGM
relationships.

The whole model is one rule:

> An OKF concept with `type: Prototype` specifies the Type named by its Concept
> ID. Its other frontmatter entries prototype attributes of that Type's
> instances, and all of its PGM Concept Links prototype the Relationships those
> instances may have. YAML titles optionally add Types and Properties.

There is no M2*, no definition hierarchy, no `identifier`, and no separate
Node Label, Property Key, or Relationship Type registry.

## Prototype concept

`example-schema/people/Person.md`:

```markdown
---
type: Prototype
full_name: Ada Lovelace
born: null
---

# Person

A person may be born in a
[place](../places/Place.md "{type: born_in, year: 1815}").
```

Because the bundle-relative path is `people/Person.md`, the OKF Concept ID and
therefore the specified Type name is:

```text
people/Person
```

This prototype declares:

- instance attributes `full_name` and `born`;
- `Ada Lovelace` as an example for `full_name`;
- no example value for `born`, represented by YAML `null`;
- a `born_in` relationship from `people/Person` to `places/Place`; and
- relationship property `year`, with example value `1815`.

Example values document the shape but impose no datatype or value constraint.
All declared attributes and relationships are optional.

The first H1 SHOULD match the final segment of the Concept ID. Thus
`people/Person.md` uses `# Person`. The full, normative Type name remains
`people/Person`; the heading is only its human-readable reflection.

## Instance

An instance uses the Type Concept ID in its normal OKF `type` field:

```markdown
---
type: people/Person
full_name: Ada Lovelace
---

# Ada Lovelace

[London](../places/London.md "{type: born_in, year: 1815}")
```

It conforms when:

- its `type` exactly names a Prototype Concept ID in the schema bundle;
- every node attribute occurs in that Prototype concept;
- every PGM relationship has a matching Source-Type, Relationship-Type, and
  Target-Type prototype link; and
- every relationship property occurs on that prototype link.

A bare Concept Link is an untyped Relationship prototype without data
Properties. A normal text title has the same graph meaning. A YAML Flow Mapping
may add Properties, and its retained `type` Property additionally selects the
Relationship Type. PGM Schema uses `type` structurally and checks the remaining
keys as permitted data Properties without removing `type` from the core PGM
model.

## Files

- [SPEC.md](SPEC.md) is the normative PGM Schema 0.4.0 Public Draft.
- [example-schema](example-schema) is a complete OKF schema bundle of
  `Prototype` concepts.
- [example-graph](example-graph) is a conforming OKF/PGM instance bundle.
- [validate.py](validate.py) is the prototype-aware validator.
- [test.mjs](test.mjs) contains positive and negative conformance tests.

PGM Schema defines no grammar of its own. OKF supplies Concepts and Concept
Links, Markdown supplies their representation, YAML supplies Properties, and
PGM supplies their graph
interpretation.

## Validation

From this directory, validate the bundled schema and example graph:

```sh
npm test
npm run validate
```

Validate another schema alone:

```sh
node validate.mjs /path/to/schema-bundle
```

Validate another schema and instance bundle:

```sh
node validate.mjs /path/to/schema-bundle /path/to/instance-bundle
```

The Python dependencies of the PGM reference parser are required; install
them from `../parser/requirements.txt`.
