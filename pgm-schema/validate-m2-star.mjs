import { readFile, readdir } from "node:fs/promises";
import { dirname, posix } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const levels = ["M0", "M1", "M2*"];
const errors = [];

function fail(message) {
  errors.push(message);
}

function isPropertyValue(value) {
  if (value === null) return true;
  if (["string", "boolean"].includes(typeof value)) return true;
  if (typeof value === "number") return Number.isFinite(value);
  return Array.isArray(value) && value.every(isPropertyValue);
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, canonical(item)])
    );
  }
  return value;
}

function splitTopLevel(source, delimiter) {
  const parts = [];
  let start = 0;
  let quote = null;
  let escaped = false;
  let depth = 0;

  for (let index = 0; index < source.length; index += 1) {
    const character = source[index];
    if (quote === '"') {
      if (escaped) {
        escaped = false;
      } else if (character === "\\") {
        escaped = true;
      } else if (character === quote) {
        quote = null;
      }
      continue;
    }
    if (quote === "'") {
      if (character === "'" && source[index + 1] === "'") {
        index += 1;
      } else if (character === quote) {
        quote = null;
      }
      continue;
    }
    if (character === '"' || character === "'") {
      quote = character;
    } else if (character === "[" || character === "{") {
      depth += 1;
    } else if (character === "]" || character === "}") {
      depth -= 1;
      if (depth < 0) throw new Error("unbalanced flow collection");
    } else if (character === delimiter && depth === 0) {
      parts.push(source.slice(start, index).trim());
      start = index + 1;
    }
  }

  if (quote || escaped || depth !== 0) throw new Error("unterminated flow value");
  parts.push(source.slice(start).trim());
  return parts;
}

function mappingColon(source) {
  let quote = null;
  let escaped = false;
  let depth = 0;
  for (let index = 0; index < source.length; index += 1) {
    const character = source[index];
    if (quote === '"') {
      if (escaped) escaped = false;
      else if (character === "\\") escaped = true;
      else if (character === quote) quote = null;
      continue;
    }
    if (quote === "'") {
      if (character === "'" && source[index + 1] === "'") index += 1;
      else if (character === quote) quote = null;
      continue;
    }
    if (character === '"' || character === "'") quote = character;
    else if (character === "[" || character === "{") depth += 1;
    else if (character === "]" || character === "}") depth -= 1;
    else if (character === ":" && depth === 0) return index;
  }
  return -1;
}

function parseQuotedYamlString(source) {
  if (source[0] === '"') return JSON.parse(source);
  if (source[0] === "'" && source.at(-1) === "'") {
    return source.slice(1, -1).replaceAll("''", "'");
  }
  throw new Error("invalid quoted YAML string");
}

function parseYamlValue(source) {
  const value = source.trim();
  if (!value) throw new Error("missing YAML value");
  if (value.startsWith("[") && value.endsWith("]")) {
    const inner = value.slice(1, -1).trim();
    return inner ? splitTopLevel(inner, ",").map(parseYamlValue) : [];
  }
  if (value.startsWith("{") && value.endsWith("}")) {
    return parseYamlFlowMapping(value);
  }
  if (value.startsWith('"') || value.startsWith("'")) {
    return parseQuotedYamlString(value);
  }
  const lower = value.toLowerCase();
  if (lower === "true" || lower === "false") return lower === "true";
  if (lower === "null" || value === "~") return null;
  if (/^[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$/.test(value)) {
    const number = Number(value);
    if (!Number.isFinite(number)) throw new Error("non-finite YAML number");
    return number;
  }
  return value;
}

function parseYamlFlowMapping(source) {
  const text = source.trim();
  if (!text.startsWith("{") || !text.endsWith("}")) {
    throw new Error("property map must use YAML flow braces");
  }
  const inner = text.slice(1, -1).trim();
  if (!inner) return {};
  const entries = [];
  const keys = new Set();
  for (const item of splitTopLevel(inner, ",")) {
    const colon = mappingColon(item);
    if (colon < 1) throw new Error("invalid YAML mapping entry");
    const keySource = item.slice(0, colon).trim();
    const key = keySource.startsWith('"') || keySource.startsWith("'")
      ? parseQuotedYamlString(keySource)
      : keySource;
    if (keys.has(key)) throw new Error(`duplicate YAML mapping key ${key}`);
    keys.add(key);
    entries.push([key, parseYamlValue(item.slice(colon + 1))]);
  }
  return Object.fromEntries(entries);
}

function parseExpression(expression, sourcePath) {
  const match = expression.match(
    /^((?::[A-Za-z][A-Za-z0-9_]*)+)(?:[ \t]+(\{.*\}))?$/
  );
  if (!match) {
    fail(`${sourcePath}: malformed or non-canonical PGM class expression ${JSON.stringify(expression)}`);
    return null;
  }

  const labels = [...match[1].matchAll(/:([A-Za-z][A-Za-z0-9_]*)/g)]
    .map((item) => item[1]);
  let properties = {};
  if (match[2]) {
    try {
      properties = parseYamlFlowMapping(match[2]);
    } catch {
      fail(`${sourcePath}: property map is not supported YAML flow syntax`);
      return null;
    }
  }
  for (const [key, value] of Object.entries(properties)) {
    if (!/^[A-Za-z][A-Za-z0-9_]*$/.test(key)) {
      fail(`${sourcePath}: property key ${key} does not use canonical underscore naming`);
    }
    if (!isPropertyValue(value)) {
      fail(`${sourcePath}: property ${key} has an unsupported PGM/YAML value`);
    }
  }
  return { labels, properties };
}

const paths = [];
for (const level of levels) {
  const entries = await readdir(`${root}/${level}`, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isDirectory()) {
      fail(`${level}/${entry.name}: nested schema directories are not allowed`);
    } else if (entry.name.endsWith(".md")) {
      paths.push(`${level}/${entry.name}`);
    }
  }
}
paths.sort();
const pathSet = new Set(paths);
const documents = new Map();

for (const sourcePath of paths) {
  const source = await readFile(`${root}/${sourcePath}`, "utf8");
  const h1Count = source.split(/\r?\n/).filter((line) => /^# (?!#)/.test(line)).length;
  if (h1Count !== 1) fail(`${sourcePath}: expected exactly one H1, found ${h1Count}`);

  const annotations = [];
  const linkPattern = /\[([^\]\r\n]+)\]\(([^)\r\n]*)\)/g;
  for (const link of source.matchAll(linkPattern)) {
    if (!link[1].startsWith(":")) continue;
    const parsed = parseExpression(link[1], sourcePath);
    if (!parsed) continue;
    let authoredDestination;
    try {
      authoredDestination = decodeURI(link[2]);
    } catch {
      fail(`${sourcePath}: relationship target contains invalid percent encoding`);
      continue;
    }
    const kind = authoredDestination === "" ? "node" : "relationship";
    const destination = kind === "relationship"
      ? posix.normalize(posix.join(posix.dirname(sourcePath), authoredDestination))
      : "";

    if (kind === "relationship") {
      if (parsed.labels.length !== 1) {
        fail(`${sourcePath}: a relationship requires exactly one type`);
      }
      if (!/^[A-Z][A-Z0-9_]*$/.test(parsed.labels[0] ?? "")) {
        fail(`${sourcePath}: relationship type ${parsed.labels[0] ?? "<missing>"} is not UPPERCASE_UNDERSCORE`);
      }
      if (
        authoredDestination.startsWith("/")
        || /^[A-Za-z][A-Za-z0-9+.-]*:/.test(authoredDestination)
        || !authoredDestination.endsWith(".md")
      ) {
        fail(`${sourcePath}: relationship target ${authoredDestination} is not a vault-relative Markdown path`);
      } else {
        const normalized = posix.normalize(authoredDestination);
        if (normalized !== authoredDestination) {
          fail(`${sourcePath}: relationship target ${authoredDestination} is not canonical`);
        }
        if (posix.dirname(destination) !== posix.dirname(sourcePath)
          || authoredDestination !== posix.basename(destination)) {
          fail(`${sourcePath}: active schema links must use a same-directory Markdown basename`);
        }
        if (!pathSet.has(destination)) {
          fail(`${sourcePath}: unresolved relationship target ${authoredDestination}`);
        }
      }
    } else if (parsed.labels.length === 0 && Object.keys(parsed.properties).length === 0) {
      fail(`${sourcePath}: empty node annotation`);
    }
    annotations.push({
      source: sourcePath,
      kind,
      destination,
      labels: parsed.labels,
      properties: parsed.properties
    });
  }

  const nodes = annotations.filter(({ kind }) => kind === "node");
  if (nodes.length !== 1) {
    fail(`${sourcePath}: expected exactly one owning node annotation, found ${nodes.length}`);
  }
  if ((nodes[0]?.labels.length ?? 0) !== 1) {
    fail(`${sourcePath}: schema definition nodes require exactly one classifier label`);
  }
  documents.set(sourcePath, { source, annotations, node: nodes[0] });
}

const vocabulary = new Map();
const normalizedSymbols = new Map();
for (const sourcePath of paths.filter((item) => item.startsWith("M2*/"))) {
  const properties = documents.get(sourcePath)?.node?.properties ?? {};
  const identifier = properties.identifier;
  if (Object.keys(properties).length !== 1) {
    fail(`${sourcePath}: owning annotation must contain exactly the identifier property`);
  }
  if (typeof identifier !== "string" || !/^[A-Za-z][A-Za-z0-9_]*$/.test(identifier)) {
    fail(`${sourcePath}: expected one canonical string identifier on the owning annotation`);
    continue;
  }
  const stem = posix.basename(sourcePath, ".md");
  if (identifier !== stem) {
    fail(`${sourcePath}: identifier ${identifier} is not identical to its file stem ${stem}`);
  }
  const normalized = identifier.toLowerCase();
  const duplicate = normalizedSymbols.get(normalized);
  if (duplicate) {
    fail(`${sourcePath}: duplicate M2* identifier ${identifier}, first defined by ${duplicate}`);
  } else {
    normalizedSymbols.set(normalized, sourcePath);
    vocabulary.set(identifier, sourcePath);
  }
}

const m1Vocabulary = new Map();
const normalizedM1Symbols = new Map();
for (const sourcePath of paths.filter((item) => item.startsWith("M1/"))) {
  const node = documents.get(sourcePath)?.node;
  const properties = node?.properties ?? {};
  const identifier = properties.identifier;
  if (Object.keys(properties).length !== 1) {
    fail(`${sourcePath}: owning annotation must contain exactly the identifier property`);
  }
  if (typeof identifier !== "string" || !/^[A-Za-z][A-Za-z0-9_]*$/.test(identifier)) {
    fail(`${sourcePath}: expected one canonical string identifier on the owning annotation`);
    continue;
  }
  const stem = posix.basename(sourcePath, ".md");
  if (identifier !== stem) {
    fail(`${sourcePath}: identifier ${identifier} is not identical to its file stem ${stem}`);
  }
  if (node?.labels[0] === "Relationship_Type" && !/^[A-Z][A-Z0-9_]*$/.test(identifier)) {
    fail(`${sourcePath}: Relationship_Type identifier ${identifier} is not UPPERCASE_UNDERSCORE`);
  }
  const normalized = identifier.toLowerCase();
  const duplicate = normalizedM1Symbols.get(normalized);
  if (duplicate) {
    fail(`${sourcePath}: duplicate M1 identifier ${identifier}, first defined by ${duplicate}`);
  } else {
    normalizedM1Symbols.set(normalized, sourcePath);
    m1Vocabulary.set(identifier, sourcePath);
  }
}

const expectedDefinitionKinds = {
  Node_Label: "Node_Label",
  Property_Key: "Node_Label",
  Relationship_Type: "Node_Label",
  identifier: "Property_Key",
  HAS_PROPERTY: "Relationship_Type",
  HAS_RELATIONSHIP: "Relationship_Type",
  HAS_RANGE: "Relationship_Type"
};

const actualDefinitionNames = [...vocabulary.keys()].sort();
const expectedDefinitionNames = Object.keys(expectedDefinitionKinds).sort();
if (JSON.stringify(actualDefinitionNames) !== JSON.stringify(expectedDefinitionNames)) {
  fail(`M2*: expected exactly ${JSON.stringify(expectedDefinitionNames)}, found ${JSON.stringify(actualDefinitionNames)}`);
}

for (const [identifier, expectedKind] of Object.entries(expectedDefinitionKinds)) {
  const definitionPath = vocabulary.get(identifier);
  if (!definitionPath) {
    fail(`M2*: missing required definition ${identifier}`);
    continue;
  }
  const actualKind = documents.get(definitionPath)?.node?.labels[0];
  if (actualKind !== expectedKind) {
    fail(`${definitionPath}: expected direct type ${expectedKind}, found ${actualKind ?? "<missing>"}`);
  }
}

function definitionVocabularyFor(sourcePath) {
  return sourcePath.startsWith("M0/") ? m1Vocabulary : vocabulary;
}

function definitionLevelFor(sourcePath) {
  return sourcePath.startsWith("M0/") ? "M1" : "M2*";
}

function definitionFor(token, sourcePath, role) {
  const definition = definitionVocabularyFor(sourcePath).get(token);
  if (!definition) {
    fail(`${sourcePath}: ${role} ${token} has no definition in ${definitionLevelFor(sourcePath)}`);
    return null;
  }
  return definition;
}

for (const [sourcePath, document] of documents) {
  for (const annotation of document.annotations) {
    for (const label of annotation.labels) {
      const definition = definitionFor(
        label,
        sourcePath,
        annotation.kind === "node" ? "node label" : "relationship type"
      );
      if (!definition) continue;
      const definitionKind = documents.get(definition)?.node?.labels[0];
      const expectedKind = annotation.kind === "node" ? "Node_Label" : "Relationship_Type";
      if (definitionKind !== expectedKind) {
        fail(`${sourcePath}: ${label} resolves to ${definition}, whose direct type is not ${expectedKind}`);
      }
    }
    for (const key of Object.keys(annotation.properties)) {
      const definition = definitionFor(key, sourcePath, "property key");
      if (definition && documents.get(definition)?.node?.labels[0] !== "Property_Key") {
        fail(`${sourcePath}: ${key} resolves to ${definition}, whose direct type is not Property_Key`);
      }
    }
  }
}

function directType(sourcePath) {
  const label = documents.get(sourcePath)?.node?.labels[0];
  return label ? definitionVocabularyFor(sourcePath).get(label) ?? null : null;
}

function outgoing(sourcePath, relationshipType) {
  return (documents.get(sourcePath)?.annotations ?? []).filter(({ kind, labels }) => {
    return kind === "relationship" && labels[0] === relationshipType;
  });
}

for (const sourcePath of paths) {
  const classifier = directType(sourcePath);
  if (!classifier) continue;
  const allowedProperties = new Set(
    outgoing(classifier, "HAS_PROPERTY").map(({ destination }) => destination)
  );
  const allowedRelationships = new Set(
    outgoing(classifier, "HAS_RELATIONSHIP").map(({ destination }) => destination)
  );
  const node = documents.get(sourcePath)?.node;
  for (const key of Object.keys(node?.properties ?? {})) {
    const definition = definitionVocabularyFor(sourcePath).get(key);
    if (definition && !allowedProperties.has(definition)) {
      fail(`${sourcePath}: ${classifier} does not declare property key ${key}`);
    }
  }
  for (const annotation of (documents.get(sourcePath)?.annotations ?? [])
    .filter(({ kind }) => kind === "relationship")) {
    const definition = definitionVocabularyFor(sourcePath).get(annotation.labels[0]);
    if (definition && !allowedRelationships.has(definition)) {
      fail(`${sourcePath}: ${classifier} does not declare relationship type ${annotation.labels[0]}`);
    }
  }
  for (const annotation of (documents.get(sourcePath)?.annotations ?? [])
    .filter(({ kind }) => kind === "relationship")) {
    const relationshipDefinition = definitionVocabularyFor(sourcePath).get(annotation.labels[0]);
    if (!relationshipDefinition) continue;
    const allowedRelationshipProperties = new Set(
      outgoing(relationshipDefinition, "HAS_PROPERTY").map(({ destination }) => destination)
    );
    for (const key of Object.keys(annotation.properties)) {
      const definition = definitionVocabularyFor(sourcePath).get(key);
      if (definition && !allowedRelationshipProperties.has(definition)) {
        fail(`${sourcePath}: ${relationshipDefinition} does not declare relationship property key ${key}`);
      }
    }
  }
}

for (const sourcePath of paths.filter((item) => {
  return documents.get(item)?.node?.labels[0] === "Relationship_Type";
})) {
  const ranges = outgoing(sourcePath, "HAS_RANGE");
  if (ranges.length !== 1) {
    fail(`${sourcePath}: Relationship_Type definition requires exactly one HAS_RANGE`);
  }
}

for (const [sourcePath, document] of documents) {
  for (const annotation of document.annotations.filter(({ kind }) => kind === "relationship")) {
    const relationshipDefinition = definitionVocabularyFor(sourcePath).get(annotation.labels[0]);
    if (!relationshipDefinition) continue;
    const declaredRange = outgoing(relationshipDefinition, "HAS_RANGE")[0]?.destination;
    if (!declaredRange || !pathSet.has(annotation.destination)) continue;
    const targetType = directType(annotation.destination);
    if (targetType !== declaredRange) {
      fail(`${sourcePath}: target ${annotation.destination} has type ${targetType ?? "<missing>"}, expected ${declaredRange}`);
    }
  }
}

const semanticRelationships = new Set();
for (const [sourcePath, document] of documents) {
  for (const annotation of document.annotations.filter(({ kind }) => kind === "relationship")) {
    const key = JSON.stringify([
      sourcePath,
      annotation.labels[0],
      annotation.destination,
      canonical(annotation.properties)
    ]);
    if (semanticRelationships.has(key)) {
      fail(`${sourcePath}: duplicate semantic relationship ${annotation.labels[0]} -> ${annotation.destination}`);
    }
    semanticRelationships.add(key);
  }
}

const expectedM0Example = {
  "M0/Ada_Lovelace.md": {
    labels: ["Person"],
    properties: { name: "Ada Lovelace" },
    relationships: [{
      type: "BORN_IN",
      destination: "M0/London.md",
      properties: { year: 1815 }
    }]
  },
  "M0/London.md": {
    labels: ["Place"],
    properties: { name: "London" },
    relationships: []
  }
};
for (const [sourcePath, expected] of Object.entries(expectedM0Example)) {
  const document = documents.get(sourcePath);
  if (!document) {
    fail(`${sourcePath}: required M0 example node is missing`);
    continue;
  }
  const actualNode = {
    labels: document.node?.labels ?? [],
    properties: document.node?.properties ?? {}
  };
  const expectedNode = {
    labels: expected.labels,
    properties: expected.properties
  };
  if (JSON.stringify(canonical(actualNode)) !== JSON.stringify(canonical(expectedNode))) {
    fail(`${sourcePath}: unexpected M0 node instance ${JSON.stringify(actualNode)}`);
  }
  const actualRelationships = document.annotations
    .filter(({ kind }) => kind === "relationship")
    .map((annotation) => ({
      type: annotation.labels[0],
      destination: annotation.destination,
      properties: annotation.properties
    }));
  if (
    JSON.stringify(canonical(actualRelationships))
    !== JSON.stringify(canonical(expected.relationships))
  ) {
    fail(`${sourcePath}: unexpected M0 relationships ${JSON.stringify(actualRelationships)}`);
  }
}

const expectedFeatures = {
  "M2*/Node_Label.md": {
    properties: ["M2*/identifier.md"],
    relationships: ["M2*/HAS_PROPERTY.md", "M2*/HAS_RELATIONSHIP.md"]
  },
  "M2*/Property_Key.md": {
    properties: ["M2*/identifier.md"],
    relationships: []
  },
  "M2*/Relationship_Type.md": {
    properties: ["M2*/identifier.md"],
    relationships: ["M2*/HAS_PROPERTY.md", "M2*/HAS_RANGE.md"]
  }
};
for (const [classifier, expected] of Object.entries(expectedFeatures)) {
  const properties = outgoing(classifier, "HAS_PROPERTY")
    .map(({ destination }) => destination).sort();
  const relationships = outgoing(classifier, "HAS_RELATIONSHIP")
    .map(({ destination }) => destination).sort();
  if (JSON.stringify(properties) !== JSON.stringify([...expected.properties].sort())) {
    fail(`${classifier}: unexpected HAS_PROPERTY feature set ${JSON.stringify(properties)}`);
  }
  if (JSON.stringify(relationships) !== JSON.stringify([...expected.relationships].sort())) {
    fail(`${classifier}: unexpected HAS_RELATIONSHIP feature set ${JSON.stringify(relationships)}`);
  }
}

const expectedRanges = {
  "M2*/HAS_PROPERTY.md": "M2*/Property_Key.md",
  "M2*/HAS_RELATIONSHIP.md": "M2*/Relationship_Type.md",
  "M2*/HAS_RANGE.md": "M2*/Node_Label.md"
};
for (const [relationshipType, expectedRange] of Object.entries(expectedRanges)) {
  const actual = outgoing(relationshipType, "HAS_RANGE").map(({ destination }) => destination);
  if (actual.length !== 1 || actual[0] !== expectedRange) {
    fail(`${relationshipType}: expected HAS_RANGE ${expectedRange}, found ${JSON.stringify(actual)}`);
  }
}

const fixedPointPath = "M2*/Node_Label.md";
for (const sourcePath of paths) {
  let current = sourcePath;
  const visited = new Set();
  for (;;) {
    if (visited.has(current)) {
      fail(`${sourcePath}: type chain cycles before reaching the Node_Label fixed point`);
      break;
    }
    visited.add(current);
    const next = directType(current);
    if (!next) {
      fail(`${sourcePath}: direct type is not closed inside M2*`);
      break;
    }
    if (next === current) {
      if (current !== fixedPointPath) {
        fail(`${sourcePath}: type chain closes at ${current}, not at ${fixedPointPath}`);
      }
      break;
    }
    current = next;
  }
}

for (const sourcePath of paths.filter((item) => item.startsWith("M1/")
  && documents.get(item)?.node?.labels[0] === "Relationship_Type")) {
  const owners = paths.filter((candidate) => candidate.startsWith("M1/")).filter((candidate) => {
    return outgoing(candidate, "HAS_RELATIONSHIP")
      .some(({ destination }) => destination === sourcePath);
  });
  if (owners.length !== 1) {
    fail(`${sourcePath}: M1 Relationship_Type requires exactly one HAS_RELATIONSHIP owner, found ${owners.length}`);
  } else if (directType(owners[0]) !== vocabulary.get("Node_Label")) {
    fail(`${sourcePath}: M1 relationship owner ${owners[0]} is not directly typed by Node_Label`);
  }
}

if (errors.length > 0) {
  console.error(`pgm-schema M0 → M1 → M2* validation failed with ${errors.length} error(s):`);
  for (const error of errors) console.error(`- ${error}`);
  process.exitCode = 1;
} else {
  const relationshipCount = [...documents.values()].reduce((count, document) => {
    return count + document.annotations.filter(({ kind }) => kind === "relationship").length;
  }, 0);
  console.log("pgm-schema canonical M0 → M1 → M2* stack is valid.");
  console.log(`Markdown nodes: ${paths.length} (M0: ${paths.filter((path) => path.startsWith("M0/")).length}, M1: ${paths.filter((path) => path.startsWith("M1/")).length}, M2*: ${paths.filter((path) => path.startsWith("M2*/")).length})`);
  console.log(`Directed PGM relationships: ${relationshipCount}`);
  console.log("M2* fixed point: type(M2*/Node_Label.md) = M2*/Node_Label.md");
  console.log("Concrete value datatypes: external YAML scalar/list semantics");
}
