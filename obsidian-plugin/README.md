# Property Graph Markdown for Obsidian

This is the minimal Obsidian companion for Property Graph Markdown 0.3.0.

It provides:

- syntax highlighting for classified CommonMark links
- autocomplete for observed node labels and relationship types
- CommonMark-based vault scanning
- node label and node property extraction
- outgoing relationship extraction
- node property conflict diagnostics
- preview rendering that shows `[label](target)` as `label: target`
- conversion of compatible Obsidian wikilinks to canonical CommonMark
- a local typed graph viewer

The plugin is an editor integration, not part of the normative standard.

## Development

Install dependencies and build:

```sh
npm install
npm run build
```

For local testing, place `main.js`, `manifest.json`, and `styles.css` in an Obsidian vault plugin directory:

```text
.obsidian/plugins/property-graph-markdown/
```

Enable **Property Graph Markdown** under **Settings > Community plugins**.

## Commands

- `PGM: Scan vault`
- `PGM: Open graph viewer`
- `PGM: Convert compatible wikilinks to CommonMark`

## Syntax

An empty CommonMark destination annotates the current note:

```markdown
[:Invoice {status: approved, amount: 1532}]()
[:Document]()
```

A non-empty destination creates an outgoing relationship:

```markdown
[:approvedBy {date: 2026-06-26}](peter-meier.md)
```

The vault scanner ignores YAML Front Matter for PGM graph extraction. It uses `markdown-it` to parse normal CommonMark links and Obsidian's YAML parser for flow mappings.

Wikilinks are not extracted as PGM and are not a PGM extension. The conversion command rewrites compatible authoring syntax:

```markdown
[[peter-meier | :approvedBy {date: 2026-06-26}]]
```

to canonical CommonMark:

```markdown
[:approvedBy {date: 2026-06-26}](peter-meier.md)
```

The command resolves existing vault targets and writes a relative CommonMark destination. Front Matter, fenced code blocks, inline-code lines, and unrecognized wikilinks remain unchanged.
