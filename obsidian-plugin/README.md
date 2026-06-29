# Property Graph Markdown for Obsidian

This is a minimal Obsidian plugin for Property Graph Markdown 0.1.2.

It provides:

- syntax highlighting for semantic relationship links
- autocomplete for relationship types
- vault scanning
- semantic relationship extraction
- preview rendering that shows `[label](target)` as `label: target`
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
[:approvedBy {date: 2026-06-26}](peter-meier.md)
```
