import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const validator = join(root, "validate.mjs");

function run(...paths) {
  return spawnSync(process.execPath, [validator, ...paths], {
    cwd: root,
    encoding: "utf8"
  });
}

function assertValid(result, context) {
  if (result.status !== 0) {
    throw new Error(`${context} should be valid:\n${result.stdout}${result.stderr}`);
  }
}

function assertInvalid(result, expectedDiagnostic, context) {
  const output = `${result.stdout}${result.stderr}`;
  if (result.status === 0 || !output.includes(expectedDiagnostic)) {
    throw new Error(
      `${context} should fail with ${JSON.stringify(expectedDiagnostic)}:\n${output}`
    );
  }
}

const bundled = run();
assertValid(bundled, "bundled prototype schema and instance graph");
process.stdout.write(bundled.stdout);

const temporaryRoot = await mkdtemp(join(tmpdir(), "pgm-schema-prototype-"));
const schemaRoot = join(temporaryRoot, "schema");
const instanceRoot = join(temporaryRoot, "instances");
const entityPath = join(schemaRoot, "domain", "Entity.md");
const placePath = join(schemaRoot, "domain", "Place.md");
const adaPath = join(instanceRoot, "objects", "Ada.md");
const londonPath = join(instanceRoot, "places", "London.md");

const validEntity = `---
type: Prototype
display_name: Example Entity
optional_value: null
---

# Entity

[Place](Place.md "{type: located_in, since: null}")

[Untyped relationship prototype](Place.md)
`;
const validPlace = `---
type: Prototype
place_name: Example Place
---

# Place
`;
const validAda = `---
type: domain/Entity
display_name: Ada
optional_value: {nested: [values, are, examples]}
---

# Ada

[London](../places/London.md "{type: located_in, since: 2020}")

[Untyped relationship instance](../places/London.md)
`;
const validLondon = `---
type: domain/Place
place_name: London
---

# London
`;

try {
  await mkdir(dirname(entityPath), { recursive: true });
  await mkdir(dirname(adaPath), { recursive: true });
  await mkdir(dirname(londonPath), { recursive: true });
  await writeFile(entityPath, validEntity);
  await writeFile(placePath, validPlace);
  await writeFile(adaPath, validAda);
  await writeFile(londonPath, validLondon);

  assertValid(
    run(schemaRoot, instanceRoot),
    "nested Concept IDs, typed and untyped Relationships, null declarations, and unconstrained example values"
  );
  assertValid(run(schemaRoot), "schema-only validation");

  await writeFile(
    entityPath,
    validEntity.replace("type: Prototype", "type: Schema")
  );
  assertInvalid(
    run(schemaRoot),
    "expected frontmatter type Prototype, found Schema",
    "Prototype marker"
  );
  await writeFile(entityPath, validEntity);

  await writeFile(
    entityPath,
    `${validEntity}\n[Another example](Place.md "{type: located_in, since: 2024}")\n`
  );
  assertInvalid(
    run(schemaRoot),
    "duplicate prototype signature domain/Entity -[located_in]-> domain/Place",
    "one prototype per relationship signature"
  );
  await writeFile(entityPath, validEntity);

  await writeFile(adaPath, validAda.replace("display_name: Ada", "unknown: Ada"));
  assertInvalid(
    run(schemaRoot, instanceRoot),
    "attribute unknown is not declared by Type domain/Entity",
    "undeclared instance attribute"
  );
  await writeFile(adaPath, validAda);

  await writeFile(
    adaPath,
    validAda.replace(
      "[Untyped relationship instance](../places/London.md)",
      "[Untyped relationship instance](../objects/Ada.md)"
    )
  );
  assertInvalid(
    run(schemaRoot, instanceRoot),
    "domain/Entity -[<untyped>]-> domain/Entity has no prototype",
    "ordinary Concept Link as untyped Relationship"
  );
  await writeFile(adaPath, validAda);

  await writeFile(
    adaPath,
    validAda.replace(
      "{type: located_in, since: 2020}",
      "{type: located_in, since: 2020, until: 2021}"
    )
  );
  assertInvalid(
    run(schemaRoot, instanceRoot),
    "relationship property until is not declared",
    "undeclared relationship property"
  );
  await writeFile(adaPath, validAda);

  await writeFile(londonPath, validLondon.replace("domain/Place", "domain/Entity"));
  assertInvalid(
    run(schemaRoot, instanceRoot),
    "domain/Entity -[located_in]-> domain/Entity has no prototype",
    "prototype Target Type"
  );
} finally {
  await rm(temporaryRoot, { recursive: true, force: true });
}

console.log("PGM Schema prototype conformance tests passed.");
