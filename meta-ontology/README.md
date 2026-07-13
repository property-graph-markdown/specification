# PGM Meta-Ontology

The PGM meta-ontology describes the smallest useful structure of a PGM ontology.

A PGM ontology defines:

- node labels
- relationship types
- property keys

The files in this directory are themselves written in PGM.

Each definition file uses the node annotation `[:NodeLabel]()` to identify
itself as a node-label definition. The empty destination applies the annotation
to that file's own graph node.

PGM does not define constraint relationships between those elements. Any node
label may use any property key. Any relationship type may connect any source node
to any target node. Validation, profiles, and domain constraints are outside the
PGM core.

## Core labels

- [NodeLabel](NodeLabel.md)
- [RelationshipType](RelationshipType.md)
- [PropertyKey](PropertyKey.md)

PGM defines no built-in property keys. There is no reserved `name`,
`description`, `status`, or similar property key in PGM. Domain ontologies MAY
document their own property keys as PGM nodes labeled `PropertyKey`.

Property flow mappings and value typing are delegated to YAML. Markdown
structure and inline links are delegated to CommonMark. YAML Front Matter has
no PGM graph semantics.
