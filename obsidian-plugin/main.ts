import {
  App,
  Editor,
  EditorPosition,
  EditorSuggest,
  EditorSuggestContext,
  EditorSuggestTriggerInfo,
  Modal,
  Notice,
  Plugin,
  TFile,
  normalizePath
} from "obsidian";
import {
  Decoration,
  DecorationSet,
  EditorView,
  MatchDecorator,
  ViewPlugin,
  ViewUpdate
} from "@codemirror/view";

interface PgmRelationship {
  source: string;
  target: string;
  type: string;
  display: string;
  properties: Record<string, string>;
}

const DEFAULT_RELATIONSHIP_TYPES = [
  "APPROVED_BY",
  "PART_OF",
  "MEMBER_OF",
  "DEPENDS_ON",
  "RELATES_TO"
];

const semanticLinkMatcher = new MatchDecorator({
  regexp: /\[[A-Z][A-Z0-9_]*(?:\s*\{[^\]\n]*\})?\]\([^)]+\)/g,
  decoration: Decoration.mark({ class: "pgm-semantic-link" })
});

const pgmHighlightExtension = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet;

    constructor(view: EditorView) {
      this.decorations = semanticLinkMatcher.createDeco(view);
    }

    update(update: ViewUpdate) {
      if (update.docChanged || update.viewportChanged) {
        this.decorations = semanticLinkMatcher.createDeco(update.view);
      }
    }
  },
  {
    decorations: (plugin) => plugin.decorations
  }
);

export default class PgmPlugin extends Plugin {
  relationships: PgmRelationship[] = [];
  relationshipTypes: Set<string> = new Set(DEFAULT_RELATIONSHIP_TYPES);

  async onload() {
    this.registerEditorExtension(pgmHighlightExtension);
    this.registerEditorSuggest(new PgmRelationshipSuggest(this));
    this.registerMarkdownPostProcessor((element) => {
      renderLinksAsLabelAndDestination(element);
    });

    this.addRibbonIcon("git-fork", "Open PGM graph", () => {
      new PgmGraphModal(this.app, this).open();
    });

    this.addCommand({
      id: "scan-pgm-vault",
      name: "Scan vault",
      callback: async () => {
        await this.scanVault();
        new Notice(`PGM: ${this.relationships.length} relationships found`);
      }
    });

    this.addCommand({
      id: "open-pgm-graph",
      name: "Open graph viewer",
      callback: () => {
        new PgmGraphModal(this.app, this).open();
      }
    });

    await this.scanVault();
  }

  async scanVault(): Promise<PgmRelationship[]> {
    const next: PgmRelationship[] = [];
    const files = this.app.vault.getMarkdownFiles();

    for (const file of files) {
      const text = await this.app.vault.cachedRead(file);
      const relationships = extractRelationships(file.path, text);
      for (const relationship of relationships) {
        next.push(relationship);
        this.relationshipTypes.add(relationship.type);
      }
    }

    this.relationships = next;
    return next;
  }
}

class PgmRelationshipSuggest extends EditorSuggest<string> {
  plugin: PgmPlugin;

  constructor(plugin: PgmPlugin) {
    super(plugin.app);
    this.plugin = plugin;
  }

  onTrigger(cursor: EditorPosition, editor: Editor, _file: TFile | null): EditorSuggestTriggerInfo | null {
    const prefix = editor.getLine(cursor.line).slice(0, cursor.ch);
    const match = prefix.match(/\[([A-Za-z_][A-Za-z0-9_]*)?$/);
    if (!match) {
      return null;
    }

    const query = match[1] ?? "";
    return {
      start: { line: cursor.line, ch: cursor.ch - query.length },
      end: cursor,
      query
    };
  }

  getSuggestions(context: EditorSuggestContext): string[] {
    const query = context.query.toUpperCase();
    return Array.from(this.plugin.relationshipTypes)
      .sort()
      .filter((type) => type.startsWith(query))
      .slice(0, 20);
  }

  renderSuggestion(value: string, el: HTMLElement) {
    el.createDiv({ text: value, cls: "pgm-suggestion" });
  }

  selectSuggestion(value: string) {
    if (!this.context) {
      return;
    }
    this.context.editor.replaceRange(value, this.context.start, this.context.end);
  }
}

class PgmGraphModal extends Modal {
  plugin: PgmPlugin;

  constructor(app: App, plugin: PgmPlugin) {
    super(app);
    this.plugin = plugin;
  }

  onOpen() {
    void this.render();
  }

  async render() {
    await this.plugin.scanVault();
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("pgm-modal");
    contentEl.createEl("h2", { text: "Property Graph Markdown" });

    if (this.plugin.relationships.length === 0) {
      contentEl.createEl("p", { text: "No semantic relationships found." });
      return;
    }

    const graphEl = contentEl.createDiv({ cls: "pgm-graph-viewer" });
    renderGraph(graphEl, this.plugin.relationships);
  }
}

function extractRelationships(sourcePath: string, text: string): PgmRelationship[] {
  const relationships: PgmRelationship[] = [];
  const linkRe = /\[([^\]\n]+)\]\(([^)]+)\)/g;
  let match: RegExpExecArray | null;

  while ((match = linkRe.exec(text)) !== null) {
    const label = match[1];
    const destination = match[2].trim().split(/\s+/)[0];
    const parsed = parseSemanticLabel(label);
    if (!parsed) {
      continue;
    }

    const targetPath = normalizeDestination(sourcePath, destination);

    relationships.push({
      source: sourcePath,
      target: targetPath,
      type: parsed.type,
      display: parsed.display,
      properties: parsed.properties
    });
  }

  return relationships;
}

function parseSemanticLabel(label: string): {
  type: string;
  display: string;
  properties: Record<string, string>;
} | null {
  const match = label.trim().match(/^([A-Z][A-Z0-9_]*)(?:\s*(\{.*\}))?$/);
  if (!match) {
    return null;
  }

  return {
    type: match[1],
    display: "",
    properties: parsePropertyMap(match[2])
  };
}

function parsePropertyMap(source: string | undefined): Record<string, string> {
  if (!source) {
    return {};
  }

  const inner = source.trim().replace(/^\{/, "").replace(/\}$/, "").trim();
  if (!inner) {
    return {};
  }

  const properties: Record<string, string> = {};
  for (const part of inner.split(",")) {
    const index = part.indexOf(":");
    if (index === -1) {
      continue;
    }
    const key = part.slice(0, index).trim();
    const value = part.slice(index + 1).trim();
    properties[key] = value;
  }
  return properties;
}

function renderLinksAsLabelAndDestination(root: HTMLElement) {
  const links = Array.from(root.querySelectorAll("a[href]")) as HTMLAnchorElement[];

  for (const link of links) {
    if (link.dataset.pgmRenderedDestination === "true") {
      continue;
    }
    if (link.querySelector("img, svg")) {
      continue;
    }

    const label = link.textContent?.trim() ?? "";
    const destination = readableDestination(link);
    if (!label || !destination || label === destination) {
      continue;
    }

    const labelEl = document.createElement("span");
    labelEl.classList.add("pgm-link-label");
    labelEl.textContent = `${label}: `;

    link.parentElement?.insertBefore(labelEl, link);
    link.textContent = destination;
    link.dataset.pgmRenderedDestination = "true";
    link.classList.add("pgm-link-destination");
  }
}

function readableDestination(link: HTMLAnchorElement): string {
  const raw = link.getAttribute("data-href") ?? link.getAttribute("href") ?? "";
  const destination = raw.trim();
  if (!destination) {
    return "";
  }
  return safeDecode(destination);
}

function normalizeDestination(sourcePath: string, destination: string): string {
  const noFragment = destination.split("#")[0];
  const decoded = safeDecode(noFragment);

  if (/^[a-z][a-z0-9+.-]*:/i.test(decoded)) {
    return decoded;
  }

  const slash = sourcePath.lastIndexOf("/");
  const prefix = slash === -1 ? "" : sourcePath.slice(0, slash + 1);
  return normalizePath(prefix + decoded);
}

function safeDecode(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function renderGraph(container: HTMLElement, relationships: PgmRelationship[]) {
  const nodeSet = new Set<string>();
  for (const relationship of relationships) {
    nodeSet.add(relationship.source);
    nodeSet.add(relationship.target);
  }
  const nodes: string[] = Array.from(nodeSet).sort();
  const width = 760;
  const height = 520;
  const radius = Math.min(width, height) / 2 - 80;
  const centerX = width / 2;
  const centerY = height / 2;
  const positions = new Map<string, { x: number; y: number }>();

  nodes.forEach((node, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(nodes.length, 1) - Math.PI / 2;
    positions.set(node, {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius
    });
  });

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.classList.add("pgm-graph-svg");

  const defs = document.createElementNS(svg.namespaceURI, "defs");
  const marker = document.createElementNS(svg.namespaceURI, "marker");
  marker.setAttribute("id", "pgm-arrow");
  marker.setAttribute("viewBox", "0 0 10 10");
  marker.setAttribute("refX", "9");
  marker.setAttribute("refY", "5");
  marker.setAttribute("markerWidth", "6");
  marker.setAttribute("markerHeight", "6");
  marker.setAttribute("orient", "auto-start-reverse");
  const arrow = document.createElementNS(svg.namespaceURI, "path");
  arrow.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
  arrow.classList.add("pgm-edge-arrow");
  marker.appendChild(arrow);
  defs.appendChild(marker);
  svg.appendChild(defs);

  for (const relationship of relationships) {
    const source = positions.get(relationship.source);
    const target = positions.get(relationship.target);
    if (!source || !target) {
      continue;
    }

    const line = document.createElementNS(svg.namespaceURI, "line");
    line.setAttribute("x1", String(source.x));
    line.setAttribute("y1", String(source.y));
    line.setAttribute("x2", String(target.x));
    line.setAttribute("y2", String(target.y));
    line.setAttribute("marker-end", "url(#pgm-arrow)");
    line.classList.add("pgm-edge");
    svg.appendChild(line);

    const label = document.createElementNS(svg.namespaceURI, "text");
    label.setAttribute("x", String((source.x + target.x) / 2));
    label.setAttribute("y", String((source.y + target.y) / 2 - 8));
    label.classList.add("pgm-edge-label");
    label.textContent = relationship.type;
    svg.appendChild(label);
  }

  for (const node of nodes) {
    const position = positions.get(node);
    if (!position) {
      continue;
    }

    const circle = document.createElementNS(svg.namespaceURI, "circle");
    circle.setAttribute("cx", String(position.x));
    circle.setAttribute("cy", String(position.y));
    circle.setAttribute("r", "34");
    circle.classList.add("pgm-node");
    svg.appendChild(circle);

    const label = document.createElementNS(svg.namespaceURI, "text");
    label.setAttribute("x", String(position.x));
    label.setAttribute("y", String(position.y + 52));
    label.classList.add("pgm-node-label");
    label.textContent = shortName(node);
    svg.appendChild(label);
  }

  container.appendChild(svg);
}

function shortName(path: string): string {
  const withoutExtension = path.replace(/\.md$/i, "");
  const slash = withoutExtension.lastIndexOf("/");
  return slash === -1 ? withoutExtension : withoutExtension.slice(slash + 1);
}
