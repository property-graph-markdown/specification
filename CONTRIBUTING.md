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
- `GRAMMAR.ebnf`, only to preserve the explicit no-independent-grammar notice
- examples and tests, when behavior changes

## Parser Changes

The reference parser favors readability over optimization. Please keep it small, direct, and easy to inspect.

Run:

```sh
python -m unittest discover -s tests
```

## Open Standard Direction

PGM should not depend on one editor, graph database, AI system, or vendor.

The guiding principle is:

> PGM adds graph semantics, not syntax.
