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
  normalizePath,
  parseLinktext,
  parseYaml
} from "obsidian";
import {
  Decoration,
  DecorationSet,
  EditorView,
  MatchDecorator,
  ViewPlugin,
  ViewUpdate
} from "@codemirror/view";
import MarkdownIt from "markdown-it";

interface PgmRelationship {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
}

interface PgmNode {
  id: string;
  labels: string[];
  properties: Record<string, unknown>;
  relationships: PgmRelationship[];
}

interface PgmParsedAnnotation {
  className: string;
  properties: Record<string, unknown>;
}

interface PgmExtraction {
  node: PgmNode;
  errors: string[];
}

const DEFAULT_CLASS_NAMES = [
  "Person",
  "Mathematician",
  "Document",
  "approvedBy",
  "partOf",
  "memberOf",
  "dependsOn",
  "relatesTo"
];

const CLASS_NAME_SOURCE = "[A-Za-z][A-Za-z0-9_]*";
const PROPERTY_MAP_SOURCE = "(?:[ \\t]+\\{[^}\\n]*\\})?";
const COMMONMARK_SEMANTIC_LINK_SOURCE =
  `\\[:${CLASS_NAME_SOURCE}${PROPERTY_MAP_SOURCE}\\]\\((?:<>|[^)\\n]*)\\)`;
const SUGGEST_TRIGGER_RE = /\[:([A-Za-z_][A-Za-z0-9_]*)?$/;

const semanticLinkMatcher = new MatchDecorator({
  regexp: new RegExp(COMMONMARK_SEMANTIC_LINK_SOURCE, "g"),
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
  nodes: Map<string, PgmNode> = new Map();
  nodeLabels: Map<string, Set<string>> = new Map();
  classNames: Set<string> = new Set(DEFAULT_CLASS_NAMES);
  validationErrors: string[] = [];

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
        const diagnostic = this.validationErrors.length > 0
          ? `, ${this.validationErrors.length} validation errors`
          : "";
        new Notice(`PGM: ${this.relationships.length} relationships${diagnostic}`);
      }
    });

    this.addCommand({
      id: "open-pgm-graph",
      name: "Open graph viewer",
      callback: () => {
        new PgmGraphModal(this.app, this).open();
      }
    });

    this.addCommand({
      id: "convert-pgm-wikilinks",
      name: "Convert compatible wikilinks to CommonMark",
      editorCallback: (editor, context) => {
        const file = context.file;
        if (!file) {
          new Notice("PGM: No active Markdown file");
          return;
        }

        const result = convertSemanticWikilinks(
          editor.getValue(),
          file.path,
          (linkPath) => this.app.metadataCache.getFirstLinkpathDest(linkPath, file.path)
        );
        if (result.count === 0) {
          new Notice("PGM: No compatible wikilinks found");
          return;
        }

        editor.setValue(result.markdown);
        new Notice(`PGM: Converted ${result.count} wikilinks to CommonMark`);
      }
    });

    await this.scanVault();
  }

  async scanVault(): Promise<PgmRelationship[]> {
    const next: PgmRelationship[] = [];
    const nextNodes = new Map<string, PgmNode>();
    const nextLabels = new Map<string, Set<string>>();
    const nextErrors: string[] = [];
    const files = this.app.vault.getMarkdownFiles();

    for (const file of files) {
      const text = await this.app.vault.cachedRead(file);
      const extraction = extractSemanticAnnotations(file.path, text);
      nextNodes.set(file.path, extraction.node);
      if (extraction.node.labels.length > 0) {
        nextLabels.set(file.path, new Set(extraction.node.labels));
      }
      for (const label of extraction.node.labels) {
        this.classNames.add(label);
      }
      for (const relationship of extraction.node.relationships) {
        next.push(relationship);
        this.classNames.add(relationship.type);
      }
      for (const error of extraction.errors) {
        nextErrors.push(`${file.path}: ${error}`);
      }
    }

    this.relationships = next;
    this.nodes = nextNodes;
    this.nodeLabels = nextLabels;
    this.validationErrors = nextErrors;
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
    const match = prefix.match(SUGGEST_TRIGGER_RE);
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
    const query = context.query.toLowerCase();
    return Array.from(this.plugin.classNames)
      .sort()
      .filter((type) => type.toLowerCase().startsWith(query))
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

    if (this.plugin.validationErrors.length > 0) {
      const errors = contentEl.createEl("ul", { cls: "pgm-validation-errors" });
      for (const error of this.plugin.validationErrors) {
        errors.createEl("li", { text: error });
      }
    }

    if (this.plugin.relationships.length === 0 && this.plugin.nodeLabels.size === 0) {
      contentEl.createEl("p", { text: "No PGM annotations found." });
      return;
    }

    const graphEl = contentEl.createDiv({ cls: "pgm-graph-viewer" });
    renderGraph(graphEl, this.plugin.relationships, this.plugin.nodeLabels);
  }
}

function extractSemanticAnnotations(sourcePath: string, text: string): PgmExtraction {
  const node: PgmNode = {
    id: sourcePath,
    labels: [],
    properties: {},
    relationships: []
  };
  const errors: string[] = [];
  const body = withoutFrontMatter(text);
  extractCommonMarkAnnotations(node, body, errors);
  return { node, errors };
}

function extractCommonMarkAnnotations(
  node: PgmNode,
  text: string,
  errors: string[]
) {
  const parser = new MarkdownIt("commonmark");
  const tokens = parser.parse(text, {});

  for (const token of tokens) {
    if (token.type !== "inline" || !token.children) {
      continue;
    }

    const children = token.children;
    let index = 0;
    while (index < children.length) {
      const child = children[index];
      if (child.type !== "link_open") {
        index += 1;
        continue;
      }

      const destination = child.attrGet("href") ?? "";
      const labelParts: string[] = [];
      index += 1;
      while (index < children.length && children[index].type !== "link_close") {
        if (children[index].content) {
          labelParts.push(children[index].content);
        }
        index += 1;
      }

      applyCommonMarkAnnotation(node, labelParts.join(""), destination, errors);
      index += 1;
    }
  }
}

function applyCommonMarkAnnotation(
  node: PgmNode,
  label: string,
  destination: string,
  errors: string[]
) {
  if (!label.trim().startsWith(":")) {
    return;
  }

  try {
    const parsed = parseClassExpression(label);
    if (destination === "") {
      if (!node.labels.includes(parsed.className)) {
        node.labels.push(parsed.className);
      }
      mergeNodeProperties(node, parsed.properties, errors);
      return;
    }

    addRelationship(node, normalizeDestination(node.id, destination), parsed);
  } catch (error) {
    errors.push(errorMessage(error));
  }
}

function addRelationship(
  node: PgmNode,
  targetPath: string,
  parsed: PgmParsedAnnotation
) {
  const id = relationshipFingerprint(node.id, parsed.className, targetPath, parsed.properties);
  if (node.relationships.some((relationship) => relationship.id === id)) {
    return;
  }

  node.relationships.push({
    id,
    source: node.id,
    target: targetPath,
    type: parsed.className,
    properties: parsed.properties
  });
}

function relationshipFingerprint(
  source: string,
  relationshipType: string,
  target: string,
  properties: Record<string, unknown>
): string {
  return JSON.stringify([
    source,
    relationshipType,
    target,
    canonicalProperties(properties)
  ]);
}

function canonicalProperties(properties: Record<string, unknown>): Record<string, unknown> {
  const canonical: Record<string, unknown> = {};
  for (const key of Object.keys(properties).sort()) {
    canonical[key] = canonicalPropertyValue(properties[key]);
  }
  return canonical;
}

function canonicalPropertyValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(canonicalPropertyValue);
  }
  return value;
}

function parseClassExpression(label: string): PgmParsedAnnotation {
  if (label.includes("->") || label.includes("<-")) {
    throw new Error("Direction markers are not supported in PGM 0.3.0");
  }

  const match = label.trim().match(/^:([A-Za-z][A-Za-z0-9_]*)(?:[ \t]+(\{.*\}))?$/);
  if (!match) {
    throw new Error(`Malformed PGM class expression: ${label}`);
  }

  const properties = parsePropertyMap(match[2]);
  return {
    className: match[1],
    properties
  };
}

function tryParseClassExpression(label: string): PgmParsedAnnotation | null {
  try {
    return parseClassExpression(label);
  } catch {
    return null;
  }
}

function parsePropertyMap(source: string | undefined): Record<string, unknown> {
  if (!source) {
    return {};
  }

  let parsed: unknown;
  try {
    parsed = parseYaml(source);
  } catch {
    throw new Error("Invalid YAML flow mapping");
  }

  if (!isRecord(parsed)) {
    throw new Error("Property map must be a YAML flow mapping");
  }
  const properties: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(parsed)) {
    const normalized = normalizePropertyValue(value);
    if (!isPropertyValue(normalized)) {
      throw new Error(`Property ${key} has an unsupported value type`);
    }
    properties[key] = normalized;
  }
  return properties;
}

function mergeNodeProperties(
  node: PgmNode,
  additions: Record<string, unknown>,
  errors: string[]
) {
  for (const [key, value] of Object.entries(additions)) {
    if (!(key in node.properties)) {
      node.properties[key] = value;
      continue;
    }
    if (!propertyValuesEqual(node.properties[key], value)) {
      errors.push(`Conflicting node property ${key}`);
    }
  }
}

function propertyValuesEqual(left: unknown, right: unknown): boolean {
  if (typeof left === "number" && typeof right === "number") {
    return left === right;
  }
  if (Array.isArray(left) && Array.isArray(right)) {
    return left.length === right.length
      && left.every((value, index) => propertyValuesEqual(value, right[index]));
  }
  return typeof left === typeof right && left === right;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isPropertyValue(value: unknown): boolean {
  if (typeof value === "number") {
    return Number.isFinite(value);
  }
  if (value === null || ["string", "boolean"].includes(typeof value)) {
    return true;
  }
  return Array.isArray(value) && value.every(isPropertyValue);
}

function normalizePropertyValue(value: unknown): unknown {
  if (value instanceof Date) {
    return value.toISOString().slice(0, 10);
  }
  if (Array.isArray(value)) {
    return value.map(normalizePropertyValue);
  }
  return value;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function withoutFrontMatter(text: string): string {
  const match = text.match(/^(?:\uFEFF)?---[ \t]*\r?\n[\s\S]*?\r?\n---[ \t]*(?:\r?\n|$)/);
  return match ? text.slice(match[0].length) : text;
}

function convertSemanticWikilinks(
  markdown: string,
  sourcePath: string,
  resolveTarget: (linkPath: string) => TFile | null
): { markdown: string; count: number } {
  const lines = markdown.match(/[^\n]*(?:\n|$)/g) ?? [];
  let count = 0;
  let inFrontMatter = false;
  let fenceCharacter = "";
  let fenceLength = 0;

  const converted = lines.map((line, index) => {
    const content = line.replace(/\r?\n$/, "");
    if (index === 0 && /^(?:\uFEFF)?---[ \t]*$/.test(content)) {
      inFrontMatter = true;
      return line;
    }
    if (inFrontMatter) {
      if (/^---[ \t]*$/.test(content)) {
        inFrontMatter = false;
      }
      return line;
    }

    const fence = content.match(/^ {0,3}(`{3,}|~{3,})/);
    if (fence) {
      const character = fence[1][0];
      if (!fenceCharacter) {
        fenceCharacter = character;
        fenceLength = fence[1].length;
      } else if (fenceCharacter === character && fence[1].length >= fenceLength) {
        fenceCharacter = "";
        fenceLength = 0;
      }
      return line;
    }
    if (fenceCharacter || content.includes("`")) {
      return line;
    }

    return line.replace(
      /\[\[([^\]\n|]+?)\s*\|\s*(:[^\n]*?)\]\]/g,
      (original, rawTarget: string, rawLabel: string) => {
        const label = rawLabel.trim();
        if (!tryParseClassExpression(label)) {
          return original;
        }

        const destination = commonMarkDestinationForWikilink(
          rawTarget.trim(),
          sourcePath,
          resolveTarget
        );
        count += 1;
        return `[${label}](${destination})`;
      }
    );
  });

  return { markdown: converted.join(""), count };
}

function commonMarkDestinationForWikilink(
  target: string,
  sourcePath: string,
  resolveTarget: (linkPath: string) => TFile | null
): string {
  const parsed = parseLinktext(target);
  const resolved = parsed.path ? resolveTarget(parsed.path) : null;
  let path = parsed.path;

  if (resolved) {
    path = relativeMarkdownPath(sourcePath, resolved.path);
  } else if (path && !/^[a-z][a-z0-9+.-]*:/i.test(path) && !path.toLowerCase().endsWith(".md")) {
    path = `${path}.md`;
  }

  return encodeURI(`${path}${parsed.subpath}`)
    .replace(/\(/g, "%28")
    .replace(/\)/g, "%29");
}

function relativeMarkdownPath(sourcePath: string, targetPath: string): string {
  const sourceParts = sourcePath.split("/");
  sourceParts.pop();
  const targetParts = targetPath.split("/");

  while (sourceParts.length > 0 && targetParts.length > 0 && sourceParts[0] === targetParts[0]) {
    sourceParts.shift();
    targetParts.shift();
  }

  return `${"../".repeat(sourceParts.length)}${targetParts.join("/")}`;
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

    const rawLabel = link.textContent?.trim() ?? "";
    const destination = readableDestination(link);
    const annotation = tryParseClassExpression(rawLabel);
    if (annotation) {
      link.classList.add("pgm-semantic-link");
    }
    if (!rawLabel || !destination || rawLabel === destination) {
      continue;
    }
    const label = annotation ? rawLabel.slice(1) : rawLabel;

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

  if (!decoded && destination.startsWith("#")) {
    return sourcePath;
  }

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

function renderGraph(
  container: HTMLElement,
  relationships: PgmRelationship[],
  nodeLabels: Map<string, Set<string>>
) {
  const nodeSet = new Set<string>();
  for (const relationship of relationships) {
    nodeSet.add(relationship.source);
    nodeSet.add(relationship.target);
  }
  for (const node of nodeLabels.keys()) {
    nodeSet.add(node);
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
    const labels = Array.from(nodeLabels.get(node) ?? []);
    label.textContent = labels.length > 0 ? `${shortName(node)} :${labels.join(" :")}` : shortName(node);
    svg.appendChild(label);
  }

  container.appendChild(svg);
}

function shortName(path: string): string {
  const withoutExtension = path.replace(/\.md$/i, "");
  const slash = withoutExtension.lastIndexOf("/");
  return slash === -1 ? withoutExtension : withoutExtension.slice(slash + 1);
}
