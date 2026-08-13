# Roadmap

PGM is currently in **Phase 1**. Phases 2 and 3 describe possible future directions and are explicitly out of scope for the current specification, parser, and conformance model.

## Semantic Minimalism

PGM introduces semantic constructs only when they provide measurable practical value for humans, agents, or interoperability.

Future capabilities will be evaluated independently. Their appearance in this roadmap does not reserve syntax, imply implementation, or make them part of PGM 0.3.0.

## Phase 1: PGM

**Practical Knowledge Graph**

**Question:** How can people and agents represent knowledge graphs token-efficiently in the same canonical format?

PGM describes the data. Its role is analogous to JSON: it provides a concrete representation without requiring a validation or ontology layer.

Phase 1 combines:

- Property Graphs
- CommonMark
- Obsidian and other Markdown tools
- agent memory
- Git-based collaboration
- token-efficient context

PGM 0.3.0 belongs to Phase 1 and defines the smallest useful core:

- the core specification
- the reference parser
- the Obsidian plugin

The Phase 1 goal is interoperability around one classified CommonMark link construct, not feature breadth.

## Phase 2: PGM Information Graph

**Structural Information Graph**

**Question:** How can people and agents represent knowledge structures and graph schemas in PGM?

The PGM Information Graph would describe the structure of PGM data. Its role would be analogous to JSON Schema.

Candidate capabilities include:

- node label and node type definitions
- relationship type definitions
- property definitions
- property types and data types
- constraints

Phase 2 is out of scope for PGM 0.3.0. This roadmap defines neither its representation nor its validation language.

The repository's non-normative [`pgm-schema/`](pgm-schema/README.md) directory
is an exploratory example for this phase. It demonstrates a complete M1
domain schema typed by the reflexively closed M2* meta-ontology and a concrete
M0 graph typed by M1, without reserving that vocabulary or promoting it into
PGM 0.3.0. The superseded
three-level M2/M3 design is retained only in the
[archive](archive/pgm-schema-m2-m3/README.md).

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

Phase 3 is out of scope for PGM 0.3.0. Each candidate would require evidence of practical value before standardization.

## Phase 1 Non-Goals

PGM 0.3.0 does not define:

- a Markdown replacement
- a graph database
- a query language
- a custom renderer
- a synchronization protocol
- an information graph
- an ontology graph
- Linked Data semantics

PGM 0.3.0 only defines how classified CommonMark inline links make a CommonMark corpus interpretable as an openCypher-compatible Property Graph.
