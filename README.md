# Property Graph Markdown

Property Graph Markdown (PGM) is a semantic profile of OKF, Markdown, and YAML
for representing directed property multigraphs without adding Markdown syntax.

> PGM adds graph semantics, not syntax.

**Website and interactive Ada graph:** [pgm.technology](https://pgm.technology)

## Public Draft status

This repository contains the **PGM 0.4.2 Public Draft 1** profile release. Its
PEP 440 Python package version is `0.4.2a1`. It retains **PGM Core 0.4.0
Public Draft 1** and the independent **PGM Schema 0.4.0 Public Draft 1**, and
adds the optional [PGM OKF Relationship Trust Profile v1](profiles/relationship-trust/SPEC.md).
These drafts are open for implementation feedback; none is a final standard.
The unrelated PGM Schema 0.4.1 draft was withdrawn, and its tag is not reused.

The normative Core document is [SPEC.md](SPEC.md); the Relationship Trust
Profile has its own specification. Please report ambiguities and
interoperability results in the
[issue tracker](https://github.com/property-graph-markdown/specification/issues).
The immutable Core publication snapshot is
[`v0.4.0-public-draft.1`](https://github.com/property-graph-markdown/specification/tree/v0.4.0-public-draft.1).

## The model

Every present non-reserved OKF Concept becomes one Node. Its OKF Concept ID is
the Node identity, its complete YAML frontmatter is retained as Node
Properties, and its required non-empty string `type` is additionally exposed
as the Node Graph Element Type.

```markdown
---
type: Person
name: Alice
age: 42
---

# Alice
```

Every OKF Concept Link occurrence becomes one directed Relationship
occurrence, including an ordinary Link without a title:

```markdown
[Acme](Acme.md)
```

A complete YAML Flow Mapping in the normal Markdown title enriches that
Relationship with Properties. A non-empty string `type` remains in the
Property map and is additionally exposed as the Relationship Graph Element
Type:

```markdown
[Acme](Acme.md "{type: works_for, since: 2024}")
```

The fundamental cases are:

| Markdown | Type | Complete Properties |
| --- | --- | --- |
| `[Acme](Acme.md)` | absent | `{}` |
| `[Acme](Acme.md "Acme Corporation")` | absent | `{}` |
| `[Acme](Acme.md "{}")` | absent | `{}` |
| `[Acme](Acme.md "{since: 2024}")` | absent | `{since: 2024}` |
| `[Acme](Acme.md "{type: works_for}")` | `works_for` | `{type: works_for}` |
| `[Acme](Acme.md "{type: works_for, since: 2024}")` | `works_for` | `{type: works_for, since: 2024}` |

All six Links remain separate occurrences when authored together. Equal graph
values may share a portable semantic `relationship_key`, but PGM Core never
coalesces the source assertions.

## Relationship trust

The optional [Relationship Trust Profile](profiles/relationship-trust/SPEC.md)
preserves `generated` and reuses OKF's `verified` event vocabulary and three
derived trust tiers for each Link occurrence independently. The complete YAML map
remains the Relationship's authored Properties; the tier is a separate view.
For example:

```markdown
[handler](handler.md "{type: calls, verified: {by: 'human:alice', at: '2026-09-02T09:00:00Z'}}")
```

A profile-aware consumer derives `human-reviewed` for this Relationship. A
consumer without the profile still retains the `verified` Property. Neither
the source Concept's trust nor a `direction` or `confidence` Property changes
the tier. The reference processor exposes an opt-in report:

```sh
pgmark trust interop/okf-relationship-carriers/pgm-links --json
```

The [interoperability exercise](interop/okf-relationship-carriers/README.md)
compares this inline authoring model with the still-proposed OKF #16
frontmatter list. It does not claim that OKF has adopted either carrier.

For the review-sized example, start with the self-contained
[Ada Lovelace Demo Vault](demo-vault/index.md). Its 46 Concept Nodes and 124
Relationship occurrences are versioned directly with this specification and
validate with zero warnings. The accompanying
[Demo Vault Schema](demo-vault-schema) defines five prototype Types and 41
permitted Relationship signatures. A compact five-node example remains in
[examples](examples/index.md).

Broken in-bundle Concept Links remain Relationships to unresolved Concept ID
references; they do not create fictional PGM Nodes. A path-bearing fragment
such as `Acme.md#profile` still targets `Acme`. A fragment-only Link such as
`#profile` is local navigation and creates no Relationship.

## Base-format profiles

PGM 0.4.0 Public Draft 1 pins:

- [OKF 0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/3fcbb9f828c2f23d109c855ee403c3a4c81f3a96/okf/SPEC.md)
  at an immutable commit and content hash;
- [CommonMark 0.31.2](https://spec.commonmark.org/0.31.2/) as the reference
  Markdown profile; and
- [YAML 1.2.2](https://yaml.org/spec/1.2.2/) Core Schema, plus explicit safe
  `!!binary`, `!!timestamp`, and `!!set` values.

Accordingly, untagged `yes` and `2026-08-23` are strings, `true` is a boolean,
duplicate Mapping keys are errors, and cyclic YAML aliases are not Property
values. These rules remove parser-dependent scalar and identity differences.

## Portable Relationship identification

The optional normative identification profile defines:

- `pgmkey:v1:sha256:…` for the semantic tuple of source, target, and complete
  Properties; and
- `pgmrel:v1:sha256:…` for one occurrence, using its zero-based ordinal among
  earlier Relationships with the same semantic key in the source document.

Properties first enter a collision-free, fully tagged JSON value model. The
identifier preimages are serialized with
[RFC 8785 JCS](https://www.rfc-editor.org/rfc/rfc8785) and hashed with SHA-256.
This supports reproducible JSON exchange and database loading without making a
database identifier responsible for Core Relationship existence.

## Five-minute demo

Python 3.10 through 3.14 are supported.

```sh
python -m pip install --constraint parser/constraints.txt --editable .
pgmark --version
pgmark validate demo/bundle
pgmark validate demo-vault
pgmark parse demo/bundle --format json
pgmark parse demo-vault --format json
pgmark import-json demo/expected.graph.json --format json
pgmark parse demo/bundle --format cypher
```

The guided demo and reproducible output snapshots are in [demo](demo/README.md).

## Reference outputs

The parser exposes a versioned standalone JSON interchange format and an
informative Cypher adapter for one PGM Core Result:

| Output | Command | Contract |
| --- | --- | --- |
| Summary | `pgmark parse BUNDLE` | Human-readable counts |
| JSON export | `pgmark parse BUNDLE --format json` | Deterministic, lossless PGM JSON Exchange Profile v1 document |
| JSON import | `pgmark import-json FILE --format json` | Validate, import, and deterministically re-export the interchange document |
| Cypher | `--format cypher` | Generic `PGMConcept` / `PGM_RELATIONSHIP` projection |
| Cypher MERGE | `--format cypher --relationship-mode merge` | Idempotent upsert by occurrence ID |

The JSON shape is validated by
[interop/pgm-graph.schema.json](interop/pgm-graph.schema.json). Export followed
by import and re-export is byte-identical for the deterministic pretty-printed
form. Cypher uses generic technical types so typed, untyped, and unresolved
Relationships remain representable. Its placeholder nodes are explicitly
marked and are not PGM Core Nodes.

The JSON Exchange Profile and schema are normative under SPEC §8.1, including
the portable key and ID algorithm in §6. The Cypher field and label names are
informative mapping choices.

## Validation and tests

Run the complete local release gate:

```sh
python -m unittest discover -s tests -v
pgmark validate demo-vault
node pgm-schema/validate.mjs demo-vault-schema demo-vault
cd pgm-schema
NO_UPDATE_NOTIFIER=1 PYTHON=python npm test
NO_UPDATE_NOTIFIER=1 PYTHON=python npm run validate
```

The language-neutral executable Core TCK is documented in
[tests/README.md](tests/README.md). Stable diagnostic codes accompany English
messages. CI repeats the Core tests on Python 3.10 through 3.14 and the separate
PGM Schema tests on Node.js 20, 22, and 24.

## Repository map

- [SPEC.md](SPEC.md): normative PGM Core 0.4.0 Public Draft.
- [Relationship Trust Profile](profiles/relationship-trust/SPEC.md): optional
  OKF-analog per-Relationship trust derivation introduced in this release.
- [demo-vault](demo-vault/index.md): full 46-node Ada Lovelace graph bundled
  with the specification.
- [demo-vault-schema](demo-vault-schema): five prototype Types for validating
  the full Ada graph with PGM Schema.
- [examples](examples/index.md): five-node Ada Lovelace example graph.
- [RATIONALE.md](RATIONALE.md): design decisions and trade-offs.
- [parser](parser/README.md): reference processor and adapters.
- [OKF relationship-carrier exercise](interop/okf-relationship-carriers/README.md):
  informative, executable comparison of PGM Link annotations with the
  frontmatter proposal in OKF #16; not a normative PGM or OKF profile.
- [tests](tests/README.md): executable conformance and interoperability tests.
- [demo](demo/README.md): public walkthrough and output snapshots.
- [pgm-schema](pgm-schema/README.md): separate prototype-based validation
  profile built on PGM Core.
- [CHANGELOG.md](CHANGELOG.md): draft changes.
- [RELEASING.md](RELEASING.md): reproducible publication procedure.

PGM Schema is independent from PGM Core conformance. PGM Core describes the
graph; PGM Schema optionally validates structural names and prototypes.

## License

The specification, reference parser, tests, and PGM Schema are available under
the [MIT License](LICENSE). The complete [Ada Demo Vault](demo-vault/index.md)
is available under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); see its
[attribution notice](demo-vault/ATTRIBUTION.txt).
