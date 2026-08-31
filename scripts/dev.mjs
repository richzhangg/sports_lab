// Runs the Python API and the Next.js dev server together, no extra deps.
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const venv = join(root, "backend", process.platform === "win32" ? "venv/Scripts" : "venv/bin");

if (!existsSync(venv)) {
  console.error("Backend venv not found. Run:  npm run setup");
  process.exit(1);
}

// On Apple Silicon, `node` may be the x86_64 (Rosetta) build; force the native
// arm64 slice of Python so arm64-only wheels (pydantic-core, numpy…) load.
const py = join(venv, "python");
const uviArgs = ["-m", "uvicorn", "main:app", "--port", "8000", "--reload"];
const canArm64 =
  process.platform === "darwin" &&
  spawnSync("arch", ["-arm64", "true"]).status === 0;
const [cmd, args] = canArm64 ? ["arch", ["-arm64", py, ...uviArgs]] : [py, uviArgs];

const backendOnly = process.argv.includes("--backend-only");
const procs = [
  spawn(cmd, args, {
    cwd: join(root, "backend"),
    stdio: "inherit",
    env: { ...process.env, PYTHONPATH: join(root, "backend") },
  }),
  ...(backendOnly ? [] : [spawn("npm", ["run", "dev"], { cwd: join(root, "frontend"), stdio: "inherit" })]),
];

const kill = () => procs.forEach((p) => p.kill("SIGINT"));
process.on("SIGINT", kill);
process.on("SIGTERM", kill);
procs.forEach((p) => p.on("exit", (c) => { kill(); process.exit(c ?? 0); }));
