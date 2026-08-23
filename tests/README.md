# PGM Core Technology Compatibility Kit

This directory contains the language-neutral Technology Compatibility Kit
(TCK) for Property Graph Markdown 0.4.0 Public Draft.

- `core.yaml` is the portable test manifest. Each case contains a complete
  in-memory Knowledge Bundle and its normative Core expectation.
- `tck.schema.json` defines the manifest format with JSON Schema 2020-12.
- `test_tck.py` is the reference runner for the bundled Python processor.
- the other `test_*.py` files test the reference implementation and optional
  profiles beyond the language-neutral Core contract.

Run the TCK from the repository root:

```sh
python -m unittest discover -s tests -p 'test_tck.py' -v
```

Run the complete reference implementation suite:

```sh
python -m unittest discover -s tests -v
```

## Manifest contract

Every case has four fields:

- `id` is a stable, unique test identifier;
- `description` states the behavior being tested;
- `files` maps bundle-relative POSIX paths to complete UTF-8 Markdown files;
- `expect` states whether the bundle conforms and, only for a conforming
  bundle, the complete normative Core Result.

All values outside the embedded Markdown files are restricted to the JSON data
model so implementations can consume the manifest without reproducing
Python-specific YAML objects. Strings that resemble dates are quoted in
expectations deliberately. The embedded source remains authoritative for YAML
1.2.2 Core Schema resolution.

For a conforming case, every expected Node contains its normative OKF Concept
ID, derived Graph Element Type, and complete Property map. Every expected
Relationship occurrence contains its source and target Concept IDs, derived
`resolved` state, optional Graph Element Type, and complete Property map.
Repeated equal Relationship objects in the array assert distinct occurrences;
the runner compares multiplicity without imposing a result serialization
order. A broken target remains a Relationship target and does not create a
Node.

The Core TCK deliberately has no technical Relationship ID, semantic key, or
occurrence-number field. Those values belong to the optional Portable
Relationship Identification Profile in §6. Link text and Markdown title are
also absent because they are not fields of the Core graph model. §6
canonicalization and identifiers, the PGM JSON Exchange Profile, and adapter
serializations are tested separately by the Python implementation tests.

For a non-conforming case, `expect` contains only `conforms: false`. The runner
requires at least one error but does not compare a partial graph: PGM Core does
not define a partial Core Result for an invalid bundle.

## Diagnostics

Diagnostics are not part of Core TCK equality. A conforming case must have no
errors. Warnings are non-fatal and cannot remove or alter a required Node or
Relationship occurrence, but reporting a warning and exposing a stable
machine-readable diagnostic code are `SHOULD` requirements. Implementations
may therefore differ in warning presence, code, message, localization, and
document attribution without failing this language-neutral Core TCK.

## Using the TCK in another implementation

1. Validate `core.yaml` against `tck.schema.json`.
2. For each case, create an isolated bundle from `files` without adding any
   implicit files.
3. Process it with the CommonMark 0.31.2 and YAML 1.2.2 Core profiles required
   by PGM 0.4.0 Public Draft.
4. For a conforming case, verify that no error occurred and compare the
   normative Node and Relationship fields as unordered multisets.
5. For a non-conforming case, verify only that at least one error occurred.
6. Report failures by case `id` and field path; do not compare diagnostics.

An implementation may use a different internal AST, parser library, graph
database, diagnostic vocabulary, or output order. Core conformance depends
only on the observable normative result described here.
