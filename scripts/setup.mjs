// One-time setup: backend venv + deps + demo data, then frontend deps.
// Forces the native arm64 Python slice on Apple Silicon (npm may run us under
// an x86_64 / Rosetta node, which would otherwise install/run the wrong arch).
import { spawnSync } from "node:child_process";
import { existsSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const backend = join(root, "backend");
const frontend = join(root, "frontend");
const isWin = process.platform === "win32";
const venvBin = join(backend, isWin ? "venv/Scripts" : "venv/bin");

const arm64 =
  process.platform === "darwin" && spawnSync("arch", ["-arm64", "true"]).status === 0;
const wrap = (cmd, args) => (arm64 ? ["arch", ["-arm64", cmd, ...args]] : [cmd, args]);

function run(cmd, args, opts = {}) {
  const [c, a] = Array.isArray(args) ? [cmd, args] : [cmd, []];
  const r = spawnSync(c, a, { stdio: "inherit", ...opts });
  if (r.status !== 0) {
    console.error(`\n✗ failed: ${c} ${a.join(" ")}`);
    process.exit(r.status ?? 1);
  }
}

// fresh venv so a previously wrong-arch install can't linger
if (existsSync(join(backend, "venv"))) rmSync(join(backend, "venv"), { recursive: true, force: true });

const [pyCmd, pyArgs] = wrap("python3", ["-m", "venv", "venv"]);
run(pyCmd, pyArgs, { cwd: backend });

const pip = join(venvBin, "pip");
const py = join(venvBin, "python");
run(...wrap(pip, ["install", "--upgrade", "pip"]));
run(...wrap(pip, ["install", "-r", "requirements.txt"]), { cwd: backend });
run(...wrap(py, ["generate_demo_data.py"]), { cwd: backend });

run("npm", ["install"], { cwd: frontend });

console.log("\n✓ setup complete — run:  npm run dev");
