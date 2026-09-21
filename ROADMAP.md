# Roadmap

PGM is currently in **Phase 1**. Phases 2 and 3 describe possible future directions and are explicitly out of scope for the current specification, parser, and conformance model.

## Semantic Minimalism

PGM introduces graph semantics only when they provide measurable practical
value for humans, agents, or interoperability. It does not introduce Markdown
syntax where OKF, Markdown, or YAML already provides the required structure.

Future capabilities will be evaluated independently. Their appearance in this roadmap does not reserve syntax, imply implementation, or make them part of PGM 0.4.0.

## Phase 1: PGM

**Practical Knowledge Graph**

**Question:** How can people and agents represent knowledge graphs token-efficiently in the same canonical format?

PGM describes the data. Its role is analogous to JSON: it provides a concrete representation without requiring a validation or ontology layer.

Phase 1 combines:

- Property Graphs
- Markdown, with CommonMark as the canonical reference profile
- Obsidian and other Markdown tools
- agent memory
- Git-based collaboration
- token-efficient context

PGM 0.4.0 belongs to Phase 1 and defines the smallest useful core:

- the PGM Core specification;
- the reference parser and validator;
- a Demo Vault;
- the versioned JSON round-trip exchange profile; and
- the reference Cypher projection.

The Phase 1 goal is interoperability around a monotonic property-graph
interpretation of OKF Concepts and all OKF Concept Links. Optional YAML Flow
Mapping titles enrich Relationships with Properties and Types; they do not
control Relationship existence.

## Phase 2: PGM Information Graph

**Structural Information Graph**

**Question:** How can people and agents represent knowledge structures and graph schemas in PGM?

The PGM Information Graph describes the structure of PGM data. Its role is
analogous to JSON Schema.

The prototype profile provides:

- Type names derived from OKF Concept IDs
- permitted node attributes prototyped in frontmatter
- permitted PGM relationships prototyped as Concept Links, with optional YAML
  annotations
- implicit Source and Target Types from the prototype link endpoints
- permitted relationship properties prototyped in YAML Flow Mapping titles

Phase 2 remains outside the PGM 0.4.0 core. Its first independent profile is
[PGM Schema](pgm-schema/SPEC.md), which defines the representation and
validation language for these structural capabilities without adding PGM
syntax.

The repository's [`pgm-schema/`](pgm-schema/README.md) directory contains the
PGM Schema 0.4.1 Public Draft, a schema Knowledge Bundle of `Type` concepts, a
conforming instance bundle, and executable conformance tests. Datatypes,
required properties, cardinalities, inheritance, uniqueness, and inference
remain outside the current PGM Schema draft. Superseded M2/M3 artifacts are not
part of the active tree; earlier versions remain recoverable through Git
history.

## Phase 3: PGM Ontology Graph

**Semantic Information Graph**

**Question:** Which explicit Linked Data semantic constructs provide measurable practical value to PGM?

The PGM Ontology Graph would add global identities and Linked Data semantics. Candidate capabilities would be introduced incrementally rather than as a mandatory all-or-nothing ontology layer.

The following stages are conceptual examples, not proposed PGM syntax.

### Stage 1: Global Identities

Map a PGM concept to an established global identity:

```text
Person owl:sameAs wikidata:Q5
Person owl:sameAs schema:Person
```

Global identity mapping has potentially high value for discovery and interoperability.

### Stage 2: Namespace Mapping

Map a relationship type to an external vocabulary:

```text
BORN_IN owl:equivalentProperty schema:birthPlace
```

Such mappings could support deterministic RDF export without changing the Phase 1 document syntax.

### Stage 3: Class Hierarchies

Express specialization between concepts:

```text
Professor rdfs:subClassOf Person
```

Class hierarchies may provide high value for search, validation, and inference.

### Stage 4: Inverse Relationships

Declare inverse relationship types:

```text
PARENT_OF owl:inverseOf CHILD_OF
```

### Stage 5: Transitive Relationships

Mark relationships whose meaning is transitive:

```text
PART_OF rdf:type owl:TransitiveProperty
```

Phase 3 is out of scope for PGM 0.4.0. Each candidate would require evidence of practical value before standardization.

## Phase 1 Non-Goals

PGM 0.4.0 does not define:

- a Markdown replacement
- a graph database
- a query language
- a custom renderer
- an editor plugin
- a synchronization protocol
- an information graph
- an ontology graph
- Linked Data semantics

PGM 0.4.0 only defines how OKF Concepts become Nodes, all OKF Concept Links
become Relationships, and optional YAML annotations supply Relationship
Properties and Graph Element Types.
