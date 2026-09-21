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

function assertInvalid(result, expectedCode, expectedDiagnostic, context) {
  const output = `${result.stdout}${result.stderr}`;
  if (
    result.status !== 1 ||
    !output.includes(`error [${expectedCode}]`) ||
    !output.includes(expectedDiagnostic)
  ) {
    throw new Error(
      `${context} should exit 1 with ${expectedCode} and ` +
      `${JSON.stringify(expectedDiagnostic)}:\n${output}`
    );
  }
}

function assertInvocationError(result, context) {
  if (result.status !== 2) {
    throw new Error(
      `${context} should exit 2 for invalid invocation:\n${result.stdout}${result.stderr}`
    );
  }
}

const bundled = run();
assertValid(bundled, "bundled prototype schema and instance graph");
process.stdout.write(bundled.stdout);

const version = run("--version");
assertValid(version, "version query");
if (
  !version.stdout.includes("PGM Schema 0.4.1 Public Draft; PGM 0.4.0 Public Draft;") ||
  !version.stdout.includes("3fcbb9f828c2f23d109c855ee403c3a4c81f3a96") ||
  !version.stdout.includes("5a3311d270bebb16d558010e75064f5b75323f284992641732b1c8097511f948")
) {
  throw new Error(`version output does not identify the normative bases:\n${version.stdout}`);
}

const temporaryRoot = await mkdtemp(join(tmpdir(), "pgm-schema-prototype-"));
const schemaRoot = join(temporaryRoot, "schema");
const instanceRoot = join(temporaryRoot, "instances");
const entityPath = join(schemaRoot, "domain", "Entity.md");
const placePath = join(schemaRoot, "domain", "Place.md");
const adaPath = join(instanceRoot, "objects", "Ada.md");
const londonPath = join(instanceRoot, "places", "London.md");
const mdDirectoryPrototypePath = join(schemaRoot, "namespace.md", "Record.md");
const mdDirectoryInstancePath = join(instanceRoot, "nested.md", "record.md");

const validEntity = `---
type: Type
display_name: Example Entity
optional_value: ""
---

# Entity

[Place](Place.md "{type: located_in, since: 0}")

[Untyped relationship prototype](Place.md)
`;
const validPlace = `---
type: Type
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

[London again](../places/London.md "{type: located_in, since: 2021}")

[Untyped relationship instance](../places/London.md)
`;
const validLondon = `---
type: domain/Place
place_name: London
---

# London
`;
const validMdDirectoryPrototype = `---
type: Type
---

# Record
`;
const validMdDirectoryInstance = `---
type: namespace.md/Record
---

# Record instance
`;

try {
  await mkdir(dirname(entityPath), { recursive: true });
  await mkdir(dirname(adaPath), { recursive: true });
  await mkdir(dirname(londonPath), { recursive: true });
  await mkdir(dirname(mdDirectoryPrototypePath), { recursive: true });
  await mkdir(dirname(mdDirectoryInstancePath), { recursive: true });
  await writeFile(entityPath, validEntity);
  await writeFile(placePath, validPlace);
  await writeFile(adaPath, validAda);
  await writeFile(londonPath, validLondon);
  await writeFile(mdDirectoryPrototypePath, validMdDirectoryPrototype);
  await writeFile(mdDirectoryInstancePath, validMdDirectoryInstance);

  assertValid(
    run(schemaRoot, instanceRoot),
    "nested Concept IDs, .md path segments, preserved repeated instance occurrences, typed and untyped Relationships, neutral placeholders, and unconstrained example values"
  );
  assertValid(run(schemaRoot), "schema-only validation");
  assertInvocationError(
    run(schemaRoot, instanceRoot, "unexpected-third-root"),
    "too many positional arguments"
  );

  await writeFile(
    entityPath,
    validEntity.replace("type: Type", "type: Schema")
  );
  assertInvalid(
    run(schemaRoot),
    "PGMS_PROTOTYPE_REQUIRED",
    "expected frontmatter type Type, found Schema",
    "Type marker"
  );
  await writeFile(entityPath, validEntity);

  await writeFile(
    entityPath,
    validEntity.replace("type: Type", "type: Prototype")
  );
  assertInvalid(
    run(schemaRoot),
    "PGMS_PROTOTYPE_REQUIRED",
    "expected frontmatter type Type, found Prototype",
    "legacy 0.4.0 marker is not a 0.4.1 alias"
  );
  await writeFile(entityPath, validEntity);

  await writeFile(
    entityPath,
    validEntity.replace('optional_value: ""', "optional_value: null")
  );
  assertInvalid(
    run(schemaRoot),
    "PGMS_PROTOTYPE_NULL_VALUE",
    "prototype attribute optional_value must not be YAML null",
    "null attribute prototype"
  );
  await writeFile(entityPath, validEntity);

  await writeFile(
    entityPath,
    validEntity.replace("since: 0", "since: ")
  );
  assertInvalid(
    run(schemaRoot),
    "PGMS_PROTOTYPE_NULL_VALUE",
    "property since must not be YAML null",
    "omitted Relationship-property prototype value"
  );
  await writeFile(entityPath, validEntity);

  await writeFile(
    entityPath,
    `${validEntity}\n[Same semantic key](Place.md "{type: located_in, since: 0}")\n`
  );
  assertInvalid(
    run(schemaRoot),
    "PGMS_DUPLICATE_SIGNATURE",
    "duplicate prototype signature domain/Entity -[located_in]-> domain/Place",
    "duplicate Core occurrences with a shared Relationship key"
  );
  await writeFile(entityPath, validEntity);

  await writeFile(
    entityPath,
    `${validEntity}\n[Another example](Place.md "{type: located_in, since: 2024}")\n`
  );
  assertInvalid(
    run(schemaRoot),
    "PGMS_DUPLICATE_SIGNATURE",
    "duplicate prototype signature domain/Entity -[located_in]-> domain/Place",
    "schema duplicate signature despite distinct Core Relationship keys"
  );
  await writeFile(entityPath, validEntity);

  await writeFile(adaPath, validAda.replace("display_name: Ada", "unknown: Ada"));
  assertInvalid(
    run(schemaRoot, instanceRoot),
    "PGMS_INSTANCE_ATTRIBUTE_UNDECLARED",
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
    "PGMS_INSTANCE_SIGNATURE_UNDECLARED",
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
    "PGMS_INSTANCE_PROPERTY_UNDECLARED",
    "relationship property until is not declared",
    "undeclared relationship property"
  );
  await writeFile(adaPath, validAda);

  await writeFile(londonPath, validLondon.replace("domain/Place", "domain/Entity"));
  assertInvalid(
    run(schemaRoot, instanceRoot),
    "PGMS_INSTANCE_SIGNATURE_UNDECLARED",
    "domain/Entity -[located_in]-> domain/Entity has no prototype",
    "prototype Target Type"
  );
} finally {
  await rm(temporaryRoot, { recursive: true, force: true });
}

console.log("PGM Schema prototype conformance tests passed.");
