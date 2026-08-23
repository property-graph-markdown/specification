# PGM Reference Parser

`pgmark.py` is the readable reference processor for Property Graph Markdown
0.4.0. It composes existing processors instead of implementing a PGM grammar:

1. read OKF Concept documents and Concept IDs;
2. retain complete frontmatter as Node Properties and derive the Node Type
   from its retained `type` Property;
3. parse each body with the CommonMark reference profile;
4. turn every OKF Concept Link into a directed Relationship; and
5. when a complete title is a YAML Flow Mapping, retain the complete Mapping
   as Relationship Properties and derive an optional Relationship Type from
   its retained `type` Property.

```markdown
[Acme](Acme.md)
[Acme](Acme.md "Acme Corporation")
[Acme](Acme.md "{since: 2024}")
[Acme](Acme.md "{type: works_for, since: 2024}")
```

All four links are Relationships. The first two are untyped and have no
Properties, the third is untyped with `since`, and the fourth is typed with the
complete Properties `type` and `since`.

The `Relationship` model retains `source`, `target`, `link_text`, `title`, an
optional derived `type`, and the complete Property map. Link text and an
ordinary title are source metadata, not graph labels or Properties. Invalid
brace-leading YAML enrichment produces a warning while retaining the baseline
Relationship.

Install and run:

```sh
python -m pip install -r parser/requirements.txt
python parser/pgmark.py parse examples
python parser/pgmark.py parse examples --cypher
python -m unittest discover -s tests
```

The non-normative Cypher adapter projects `type` to a node label or
relationship type and omits the redundant stored `type` Property in Cypher. It
reports a target-specific error for untyped Relationships or YAML values that
Cypher cannot represent; those limitations do not make the source invalid PGM.

Use `--relationship-mode merge` for idempotent Relationship export by the
complete semantic key instead of snapshot `CREATE` statements.
