// Starts the Python video engine (../app.py) with the project's virtualenv, on any OS/shell.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const candidates = [join(root, ".venv", "Scripts", "python.exe"), join(root, ".venv", "bin", "python")];
const python = candidates.find(existsSync);
if (!python) {
  console.error("Python virtualenv not found. In the project root run:\n  python -m venv .venv\n  .venv/bin/pip install -r requirements.txt   (Windows: .venv\\Scripts\\pip)");
  process.exit(1);
}
const child = spawn(python, ["app.py", "--no-browser", "--reload"], { cwd: root, stdio: "inherit" });
child.on("exit", (code) => process.exit(code ?? 0));
for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => child.kill(sig));
