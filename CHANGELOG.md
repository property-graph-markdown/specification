# Changelog

This file records user-visible changes to Property Graph Markdown. Public-draft
tag `vX.Y.Z-public-draft.N` maps to PEP 440 Python package version `X.Y.ZaN`
while the specification remains under review.

## 0.4.1 Public Draft 1 / Python 0.4.1a1 - 2026-09-21

### Changed

- PGM Schema 0.4.1 requires `type: Type` on prototype concepts. The previous
  `type: Prototype` marker is rejected; migrate schema documents by changing
  only that frontmatter value. Instance Type names and prototype semantics
  remain unchanged.
- Updated the schema reference validator, conformance tests, example schema,
  and Ada Demo Vault schema to the new marker.
- The Python distribution and reference processor advance to `0.4.1a1` while
  PGM Core conformance remains `0.4.0 Public Draft` and JSON Exchange remains
  v1. The JSON example records the updated processor version.
- Release metadata now distinguishes the package/schema release version from
  the independently versioned PGM Core baseline.

## 0.4.0 Public Draft 1 / Python 0.4.0a1 - 2026-09-08

### Added

- A monotonic property-graph interpretation of OKF 0.2 Knowledge Bundles.
- Complete YAML Property maps for Nodes and Relationships.
- A thin local validator for the pinned OKF 0.2 conformance baseline.
- The versioned, schema-backed PGM JSON Exchange Profile v1 with strict
  import and deterministic byte-identical re-export.
- Deterministic reference-parser, JSON-roundtrip, and Cypher-export tests.
- The independent prototype-based PGM Schema validation profile.
- The self-contained 46-node, 124-relationship Ada Lovelace Demo Vault and its
  five-Type PGM Schema prototype bundle.
- Reproducible release constraints, continuous integration, and public-draft
  packaging instructions.

### Changed

- Every OKF Concept Link now yields a directed Relationship, including bare
  links and links with ordinary Markdown titles.
- A complete YAML Flow Mapping in a Link title enriches that Relationship
  rather than opting it into the graph.
- A non-empty string `type` remains in the complete Property map and is also
  interpreted structurally as the Graph Element Type.
- The reference parser composes CommonMark and YAML processors instead of
  maintaining a PGM-specific Link lexer or Property grammar.
- Prototype attributes and Relationship data Properties require non-null
  example or neutral placeholder values. Canonical neutral placeholders are
  `""`, `0`, `false`, `[]`, and `{}`; an omitted YAML value remains null and
  is rejected by the PGM Schema validator.

### Removed

- Earlier classified-link markers and direction syntax.
- Experimental adapters outside the 0.4.0 Public Draft release scope; JSON
  interchange and Cypher remain.
- Historical milestone artifacts from the active release tree; they remain
  available through Git history.
