# PGM Schema

PGM Schema 0.4.0 Public Draft is prototype modeling for OKF Knowledge Bundles
with PGM Relationships. Its normative Core basis is
[PGM 0.4.0 Public Draft](../SPEC.md), including OKF 0.2 at pinned commit
`3fcbb9f828c2f23d109c855ee403c3a4c81f3a96` and specification SHA-256
`5a3311d270bebb16d558010e75064f5b75323f284992641732b1c8097511f948`.

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
born: 0
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
- neutral numeric placeholder `0` for `born`;
- a `born_in` relationship from `people/Person` to `places/Place`; and
- relationship property `year`, with example value `1815`.

Prototype attributes and relationship data Properties always carry a
non-null example or neutral placeholder. Use `""` for strings, `0` for
numbers, `false` for booleans, `[]` for sequences, and `{}` for mappings.
Inside a double-quoted Markdown Link title, use YAML single quotes for an empty
string, for example `{type: observed, incident: ''}`. A missing value such as
`incident:` is YAML null, not an empty string, and is invalid in a prototype.

These values document the intended shape but impose no datatype, default, or
value constraint. All declared attributes and relationships are optional.

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

Core PGM preserves every Concept Link occurrence. PGM Schema adds one
schema-specific rule: a schema bundle may contain at most one prototype
occurrence for the same `(Source Type, Relationship Type, Target Type)`
signature. A second occurrence is a `PGMS_DUPLICATE_SIGNATURE` error even when
its Properties—and therefore its portable PGM Relationship key—differ. This is
not Core coalescing. Instance bundles may contain multiple occurrences of one
permitted signature; the validator checks and preserves each one.

## Files

- [SPEC.md](SPEC.md) is the normative PGM Schema 0.4.0 Public Draft.
- [example-schema](example-schema) is a complete OKF schema bundle of
  `Prototype` concepts.
- [example-graph](example-graph) is a conforming OKF/PGM instance bundle.
- [../demo-vault-schema](../demo-vault-schema) and
  [../demo-vault](../demo-vault/index.md) are the five-Type schema and full
  46-node Ada Lovelace instance bundled with the PGM specification.
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

From the repository root, validate the complete Ada Demo Vault:

```sh
node pgm-schema/validate.mjs demo-vault-schema demo-vault
```

The Python dependencies of the PGM reference parser are required; install
them from `../parser/requirements.txt`. PGM Schema reuses the same thin local
OKF adapter and therefore adds no `reference-agent` runtime dependency.

The validator emits stable codes in the form `error [CODE]: message`. Human
prose may change without changing the condition. Exit statuses are:

- `0`: schema and optional instance conform;
- `1`: validation failed;
- `2`: invalid command-line invocation.

The JavaScript wrapper propagates the Python validator's exit status unchanged.
