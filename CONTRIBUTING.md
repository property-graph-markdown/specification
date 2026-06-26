# Contributing

Thank you for helping shape Property Graph Markdown.

PGM is intended to become an open, vendor-neutral specification for interpreting CommonMark corpora as openCypher-compatible Property Graphs.

## Good Contributions

We welcome:

- grammar feedback
- parser improvements
- relationship examples
- interoperability reports
- editor integrations
- use cases from documentation, knowledge bases, AI memory, and RAG corpora

## Design Bias

PGM should remain small.

When proposing a change, please explain:

- what problem it solves;
- why existing CommonMark, YAML, and openCypher concepts are not enough;
- how it affects human readability;
- how it affects existing Markdown tooling;
- whether it belongs in the core specification or an extension.

## Specification Changes

Specification changes should update:

- `SPEC.md`
- `RATIONALE.md`
- `GRAMMAR.ebnf`, if grammar changes are involved
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

> Introduce the smallest possible extension to CommonMark that enables Markdown corpora to be interpreted as openCypher-compatible Property Graphs.
