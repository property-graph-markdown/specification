---
okf_version: '0.2'
---

# Ada Lovelace example graph

This small OKF Knowledge Bundle demonstrates the complete PGM Core mapping in
five ordinary Markdown documents:

- [Ada Lovelace](ada-lovelace.md) is a `Person` Node with four typed outgoing
  Relationship occurrences.
- [Charles Babbage](charles-babbage.md) contributes the reciprocal
  `collaborated_with` occurrence.
- [Augustus De Morgan](augustus-de-morgan.md),
  [the Analytical Engine](analytical-engine.md), and [London](london.md) are
  target Nodes.

From the repository root:

```sh
pgmark validate examples
pgmark parse examples --format json
pgmark parse examples --format cypher
```

The bundle validates to **5 Nodes, 5 Relationships, and 0 warnings**. Expected
Cypher projections are committed as [CREATE output](expected.cypher) and
[MERGE output](expected-merge.cypher).
