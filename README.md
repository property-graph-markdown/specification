# Property Graph Markdown

Property Graph Markdown (PGM) is a semantic profile of OKF, Markdown, and YAML
for representing directed property multigraphs without adding Markdown syntax.

> PGM adds graph semantics, not syntax.

## Public Draft status

This repository implements **PGM 0.4.0 Public Draft 1**, dated 2026-08-23. Its
PEP 440 Python package version is `0.4.0a1`. It is ready for implementation
feedback from the OKF, Markdown, Obsidian, graph database, and
knowledge-management communities, but it is not a final standard. Incompatible
corrections may still be made before final 0.4.0.

The normative document is [SPEC.md](SPEC.md). Please report ambiguities and
interoperability results in the
[issue tracker](https://github.com/property-graph-markdown/specification/issues).

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
pgmark parse demo/bundle --format json
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
cd pgm-schema
NO_UPDATE_NOTIFIER=1 PYTHON=python npm test
NO_UPDATE_NOTIFIER=1 PYTHON=python npm run validate
```

The language-neutral executable Core TCK is documented in
[tests/README.md](tests/README.md). Stable diagnostic codes accompany English
messages. CI repeats the Core tests on Python 3.10 through 3.14 and the separate
PGM Schema tests on Node.js 20, 22, and 24.

## Repository map

- [SPEC.md](SPEC.md): normative PGM 0.4.0 Public Draft.
- [RATIONALE.md](RATIONALE.md): design decisions and trade-offs.
- [parser](parser/README.md): reference processor and adapters.
- [tests](tests/README.md): executable conformance and interoperability tests.
- [demo](demo/README.md): public walkthrough and output snapshots.
- [pgm-schema](pgm-schema/README.md): separate prototype-based validation
  profile built on PGM Core.
- [CHANGELOG.md](CHANGELOG.md): draft changes.
- [RELEASING.md](RELEASING.md): reproducible publication procedure.

PGM Schema is independent from PGM Core conformance. PGM Core describes the
graph; PGM Schema optionally validates structural names and prototypes.
