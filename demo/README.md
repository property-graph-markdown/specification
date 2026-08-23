# PGM 0.4.0 Public Draft 1 demo

This five-minute demo is an ordinary OKF 0.2 Knowledge Bundle. It shows every
fundamental PGM Relationship form, repeated assertions, a path-bearing
fragment, an unresolved target, an intra-document fragment, and an external
Link.

Install the reference processor from the repository root:

```sh
python -m pip install --constraint parser/constraints.txt --editable .
```

Validate the bundle and export the standalone PGM JSON Exchange Profile v1
document:

```sh
pgmark validate demo/bundle
pgmark parse demo/bundle --format json
```

The checked-in JSON can be imported, validated, and deterministically
re-exported:

```sh
pgmark import-json demo/expected.graph.json --format json
```

Generate the informative Cypher projection in snapshot or idempotent MERGE
mode:

```sh
pgmark parse demo/bundle --format cypher
pgmark parse demo/bundle --format cypher --relationship-mode merge
```

The checked-in `expected.graph.json`, `expected.cypher`, and
`expected-merge.cypher` files are reproducible snapshots. The JSON graph is
validated by `interop/pgm-graph.schema.json`, imported, and re-exported
byte-for-byte by the test suite.

The JSON Exchange Profile preserves the unresolved `future/Partner` target
without inventing a PGM Core Node. The Cypher projection materializes an
explicitly marked placeholder for that target; this adapter node is not a PGM
Core Node.

Run every release check with:

```sh
python -m unittest discover -s tests -v
```
