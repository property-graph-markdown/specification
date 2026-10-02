# Changelog

This file records user-visible changes to Property Graph Markdown. The
`v0.4.2-public-draft.N` publication tags map to PEP 440 Python package
versions `0.4.2aN`. PGM Core and PGM Schema retain their independent 0.4.0
Public Draft semantics in this profile release.

## 0.4.2 Public Draft 1 / Python 0.4.2a1 - 2026-10-02

### Added

- The optional PGM OKF Relationship Trust Profile v1, preserving `generated`
  and applying OKF-analog `verified` event forms and three derived tiers
  independently to each PGM Link occurrence.
- An opt-in `pgmark trust` report and tests for absent, machine, human, and
  malformed verification events. Profile errors do not alter Core conformance.
- A reproducible OKF #16 interoperability exercise contrasting inline PGM
  Link annotations with a proposed frontmatter relationship list.

### Unchanged

- PGM Core 0.4.0, PGM JSON Exchange Profile v1, and PGM Schema 0.4.0 retain
  their source and exchange semantics. Trust tiers are derived in a separate
  view, never inserted into the authored Relationship Property map.
- Physical Link direction remains from the containing Concept to the Link
  destination; a `direction` Property does not reverse it.

The `v0.4.1-public-draft.1` tag belongs to a withdrawn, unrelated PGM Schema
draft and is not reused.

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
