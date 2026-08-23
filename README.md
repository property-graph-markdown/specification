# Property Graph Markdown

Property Graph Markdown (PGM) is a semantic profile of OKF, Markdown, and YAML
for representing property graphs.

> PGM adds graph semantics, not syntax.

OKF provides Concepts and Concept Links. Markdown provides their link
representation. YAML provides Properties. PGM maps them monotonically to a
Property Graph: every Concept becomes a Node and every Concept Link becomes a
directed Relationship.

## The complete model

An OKF Concept's Concept ID is its Node identity. Its complete YAML frontmatter
is the Node Property map. The required `type` Property is retained and its
non-empty string value is additionally interpreted as the Node's Graph Element
Type:

```markdown
---
type: Person
name: Alice
age: 42
---

# Alice
```

Every OKF Concept Link is a Relationship, including an ordinary link without a
title:

```markdown
[Acme](Acme.md)
```

A complete YAML Flow Mapping in the normal Markdown title enriches that same
Relationship with Properties. A non-empty string `type` remains a Property and
is additionally interpreted as the Relationship's Graph Element Type:

```markdown
[Acme](Acme.md "{type: works_for, since: 2024}")
```

The fundamental cases are:

| Markdown | Relationship Type | Complete Properties |
| --- | --- | --- |
| `[Acme](Acme.md)` | absent | `{}` |
| `[Acme](Acme.md "{since: 2024}")` | absent | `{since: 2024}` |
| `[Acme](Acme.md "{type: works_for}")` | `works_for` | `{type: works_for}` |
| `[Acme](Acme.md "{type: works_for, since: 2024}")` | `works_for` | `{type: works_for, since: 2024}` |

An empty Flow Mapping (`"{}"`) is graph-equivalent to the bare link. A normal
text title remains human-facing source metadata and still yields the baseline
untyped Relationship:

```markdown
[Acme](Acme.md "Acme Corporation")
```

If a brace-leading title is not a valid complete YAML Flow Mapping, a processor
keeps the baseline Relationship, attaches no Properties, and reports a
non-fatal diagnostic. This preserves OKF meaning even when optional PGM
enrichment is malformed.

PGM defines no `:RELATIONSHIP_TYPE`, arrow, incoming-link marker, or property
mini-language. CommonMark 0.31.2 is the reference grammar for canonical Link
syntax; compatible Markdown profiles may expose the same parsed link fields.

## Why this composes well

- Existing OKF bundles retain every Concept and Concept Link in the PGM graph.
- Markdown and OKF tools continue to process PGM documents normally.
- YAML parsers handle scalar, sequence, mapping, nested, and tagged values.
- Adding a Flow Mapping title enriches a Relationship instead of opting it in.
- Concrete exporters remain free to map or reject target-incompatible YAML
  values and untyped Relationships without narrowing valid PGM.

OKF-named keys in a Relationship map are opaque Properties in core PGM. A
separate profile may assign provenance or lifecycle semantics, but core PGM
does not transfer Concept-only OKF semantics to Relationships.

## Reference parser

Install and run:

```sh
python -m pip install -r parser/requirements.txt
python parser/pgmark.py parse examples
python parser/pgmark.py parse examples --cypher
python -m unittest discover -s tests
```

The bundled Cypher example uses typed Relationships because the target adapter
requires a relationship type. Untyped Relationships remain valid PGM; the
adapter reports its target-specific limitation rather than rejecting the
source model.

See [SPEC.md](SPEC.md) for the normative Public Draft and
[RATIONALE.md](RATIONALE.md) for the design rationale. [GRAMMAR.ebnf](GRAMMAR.ebnf)
records that PGM has no independent grammar.

## PGM Schema

[PGM Schema](pgm-schema/README.md) is a separate prototype-based validation
profile. It uses all core PGM Relationships, including bare and otherwise
untyped Concept Links, and adds no Markdown syntax.
