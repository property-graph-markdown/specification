# PGM Reference Processor

`pgmark.py` is the readable reference parser, validator, and adapter driver for
the PGM 0.4.0 Public Draft. It composes existing processors instead of
implementing a PGM grammar:

1. validate the pinned OKF 0.2 rules through the local auditable adapter;
2. parse Concept frontmatter as safe YAML 1.2.2 Core Schema values;
3. retain the complete Mapping and derive the Node Type from `type`;
4. parse each body with CommonMark 0.31.2;
5. turn every qualifying Concept Link occurrence into one directed
   Relationship, including links to absent Concepts; and
6. parse only a complete YAML Flow Mapping title as optional Relationship
   Properties and derive an optional Type from its retained `type` Property.

```markdown
[Acme](Acme.md)
[Acme](Acme.md "Acme Corporation")
[Acme](Acme.md "{since: 2024}")
[Acme](Acme.md "{type: works_for, since: 2024}")
```

All four links are Relationships. The first two are untyped and have no
Properties, the third is untyped with `since`, and the fourth is typed with the
complete Properties `type` and `since`.

The `Relationship` model retains `source`, `target`, `link_text`, `title`, an
optional derived `type`, and the complete Property map. It also carries a
portable semantic `key`, a zero-based ordinal among equal assertions, and a
distinct occurrence `id`. Equal links are never coalesced. Link text and an
ordinary title are source metadata, not graph labels or Properties. Invalid
brace-leading enrichment produces a warning while retaining the baseline
Relationship.

Install and run:

```sh
python -m pip install -r parser/requirements.txt
python parser/pgmark.py validate demo/bundle
python parser/pgmark.py parse demo/bundle --format summary
python parser/pgmark.py parse demo/bundle --format json
python parser/pgmark.py import-json demo/expected.graph.json --format json
python parser/pgmark.py parse demo/bundle --format cypher
python parser/pgmark.py import-json demo/expected.graph.json --format cypher
python parser/pgmark.py parse demo/bundle --format cypher --relationship-mode merge
python -m unittest discover -s tests -v
```

The reference processor supports CPython 3.10 through 3.14. The separate PGM
Schema tooling is tested with Node.js 20, 22, and 24.

## Reproducible conformance statement

`pgmark` 0.4.0a1 claims `PGM Core Processor`, `Portable Relationship
Identification Processor`, and `PGM JSON Exchange Processor`. Its fixed bases
and policies are:

- PGM 0.4.0 Public Draft and PGM JSON Exchange Profile v1, schema
  `urn:pgm:schema:graph:1`;
- OKF 0.2 commit `3fcbb9f828c2f23d109c855ee403c3a4c81f3a96`, specification
  SHA-256 `5a3311d270bebb16d558010e75064f5b75323f284992641732b1c8097511f948`;
- CommonMark 0.31.2 and YAML 1.2.2 Core Schema;
- explicit safe tag URIs `tag:yaml.org,2002:binary`,
  `tag:yaml.org,2002:set`, and `tag:yaml.org,2002:timestamp`; and
- acyclic aliases expanded by value, cycles rejected.

Core errors, warnings, and adapter errors remain separate categories. Every
JSON exchange document repeats this statement in its strict `conformance`
object together with the processor name and version.

The CLI returns `0` on success, `1` for a Core conformance, JSON import, or
adapter failure, and `2` for command-line misuse or an invalid input path or
input kind. Invalid UTF-8 in an OKF Markdown document is a Core error and
therefore returns `1`.

For filesystem safety, the reference processor reads regular files only and
does not follow symbolic-link input roots or symbolic-link Markdown files.
PGM does not make one fixed bundle-size threshold a source-conformance rule;
deployments processing untrusted bundles should additionally impose operating
system limits on memory, CPU time, input bytes, and file count. The parser
itself always rejects unsafe YAML tags, cyclic aliases, traversal, and invalid
UTF-8 without executing authored content.

## JSON exchange

The normative version 1 `pgm-graph` exchange envelope is deterministic and
round-trips a complete Core Result. Properties use the fully tagged Canonical
PGM Value v1 rather than ordinary JSON objects. Nested mappings and sequences,
heterogeneous lists, binary values, explicit timestamps, sets, large integers,
non-string nested keys, and non-finite numbers therefore remain lossless. The
importer validates both the JSON Schema and derived graph invariants before it
constructs a `Graph`.

## Cypher projection

The Cypher adapter uses the generic `PGMConcept` label and
`PGM_RELATIONSHIP` native Relationship Type, so typed and untyped PGM
Relationships are equally representable. Authored Types are stored separately
in `pgm_type`; complete Properties are stored as Canonical PGM Value JSON in
`pgm_properties_json`. Technical IDs use reserved `pgm_*` fields and cannot
collide with authored Property keys. Absent targets become explicitly marked
Cypher placeholders, never PGM Nodes.

The default `create` mode preserves every occurrence in a snapshot. Use
`--relationship-mode merge` for idempotent loading by the portable occurrence
ID. Adapter failures are separate from PGM Core validation errors.
