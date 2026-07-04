# Property Graph Markdown for Obsidian

This is a minimal Obsidian plugin for Property Graph Markdown 0.2.0.

It provides:

- syntax highlighting for semantic links
- autocomplete for relationship types
- vault scanning
- semantic relationship extraction
- `:LABEL` extraction as node labels
- preview rendering that shows `[label](target)` as `label: target`
- experimental semantic wikilinks
- a simple local graph viewer with relationship labels

The plugin is intentionally small. It is an editor companion for the standard, not the standard itself.

## Development

Install dependencies:

```sh
npm install
```

Build:

```sh
npm run build
```

For local testing, copy `main.js`, `manifest.json`, and `styles.css` into an Obsidian vault plugin folder such as:

```text
.obsidian/plugins/property-graph-markdown/
```

## Commands

- `PGM: Scan vault`
- `PGM: Open graph viewer`

## Syntax

The plugin recognizes links such as:

```markdown
[:LABEL](Ontology/Invoice.md)
[:approvedBy {date: 2026-06-26}](peter-meier.md)
```

`[:LABEL](Ontology/Invoice.md)` adds the label `Invoice` to the current node. It remains a normal Markdown or Obsidian link, but it is not shown as a Property Graph relationship.

It also prototypes the optional semantic wikilink extension:

```markdown
[[peter-meier | :approvedBy {date: 2026-06-26}]]
```
