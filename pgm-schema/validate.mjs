import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
// Match the interpreter used by the documented `python -m pip install` step.
// Callers can still select an explicit environment with PYTHON.
const python = process.env.PYTHON || "python";
const result = spawnSync(
  python,
  [join(root, "validate.py"), ...process.argv.slice(2)],
  { stdio: "inherit" }
);

if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
