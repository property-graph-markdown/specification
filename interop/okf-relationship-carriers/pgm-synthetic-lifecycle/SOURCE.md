# Synthetic PGM lifecycle example

This bundle is an invented PGM 0.4.0 example for comparing relationship
carriers. It is **not** an export from Andrew Crenshaw's bundle and does not
claim that OKF has adopted `supersedes` or `contradicts` as relationship types.

The assertions are authored only at Markdown Link occurrences in
`bundle/decisions/decision-002.md`. PGM reads them as directed relationships
from Concept ID `decisions/decision-002` to the linked Concepts:

| Link target | PGM type |
| --- | --- |
| `decisions/decision-001` | `supersedes` |
| `claims/claim-001` | `contradicts` |
| `claims/claim-001` | untyped bare Link; no #16 list entry |
| `claims/claim-missing` | `contradicts`, unresolved target |

The bundle-relative file paths supply the PGM Core Concept IDs. Each present
Concept also declares an invented stable `id: urn:pgm-fixture:…` property for
the separate OKF #22 query illustration; an explicit path-to-id lookup is
needed to cross that boundary. Renaming a file changes its PGM Core Concept ID
but not that `id` property. No symmetry, transitivity,
or lifecycle effect is inferred by PGM Core from either relationship type. The missing
target remains an occurrence and is marked unresolved; it does not produce a
placeholder node or authorize an exclusion.

From the repository root:

```sh
python parser/pgmark.py parse interop/okf-relationship-carriers/pgm-synthetic-lifecycle/bundle --format summary
```
