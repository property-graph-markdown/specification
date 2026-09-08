# Changelog

This file records user-visible changes to Property Graph Markdown. Public-draft
tag `v0.4.0-public-draft.N` maps to PEP 440 Python package version `0.4.0aN`
while the specification remains under review.

## Unreleased

- No changes yet.

## 0.4.0 Public Draft 1 / Python 0.4.0a1 - 2026-09-08

### Added

- A monotonic property-graph interpretation of OKF 0.2 Knowledge Bundles.
- Complete YAML Property maps for Nodes and Relationships.
- A thin local validator for the pinned OKF 0.2 conformance baseline.
- The versioned, schema-backed PGM JSON Exchange Profile v1 with strict
  import and deterministic byte-identical re-export.
- Deterministic reference-parser, JSON-roundtrip, and Cypher-export tests.
- The independent prototype-based PGM Schema validation profile.
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
