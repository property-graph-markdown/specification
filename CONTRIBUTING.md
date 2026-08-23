# Contributing

Thank you for helping shape Property Graph Markdown.

PGM is intended to become an open, vendor-neutral semantic profile for
interpreting OKF Knowledge Bundles as Property Graphs.

## Good Contributions

We welcome:

- semantic-mapping feedback
- parser improvements
- relationship examples
- interoperability reports
- editor integrations
- use cases from documentation, knowledge bases, AI memory, and RAG corpora

## Design Bias

PGM should remain small.

When proposing a change, please explain:

- what problem it solves;
- why existing OKF, Markdown, and YAML concepts are not enough;
- how it affects human readability;
- how it affects existing Markdown tooling and the CommonMark reference
  profile;
- whether it belongs in the core specification or an extension.

## Specification Changes

Specification changes should update:

- `SPEC.md`
- `RATIONALE.md`
- the JSON exchange schema when its versioned contract changes
- examples and tests, when behavior changes

## Parser Changes

The reference parser favors readability over optimization. Please keep it
small, direct, and easy to inspect. Its runtime stack is intentionally limited
to `markdown-it-py`, `ruamel.yaml`, and `jsonschema`; do not add
`reference-agent` as a runtime dependency. Any external OKF validator belongs
in supplemental CI and must not replace validation against the pinned OKF
commit.

Run the complete reference checks from the repository root:

```sh
python -m unittest discover -s tests -v
npm --prefix pgm-schema test
npm --prefix pgm-schema run validate
```

Behavioral changes need a language-neutral case in `tests/core.yaml` whenever
the outcome is a normative Core Result or conformance decision. Recommended
warnings and reference diagnostic codes belong in implementation tests, not in
the Core pass criteria. JSON exchange changes need an export-import-export test
and schema validation. Cypher changes need deterministic CREATE and MERGE
snapshots.

## Open Standard Direction

PGM should not depend on one editor, graph database, AI system, or vendor.

The guiding principle is:

> PGM adds graph semantics, not syntax.
