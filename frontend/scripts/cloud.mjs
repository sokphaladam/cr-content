// Starts the cloud sync server (../server) on port 8080 when server/.env exists.
// It never exits on its own: `concurrently -k` would stop the engine and web too, and the cloud is optional.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const python = [join(root, ".venv", "Scripts", "python.exe"), join(root, ".venv", "bin", "python")].find(existsSync);
const idle = (msg) => { console.log(msg); setInterval(() => {}, 1 << 30); };

if (!python) idle("Cloud server skipped: no .venv.");
else if (!existsSync(join(root, "server", ".env"))) idle("Cloud server skipped: no server/.env (see server/README.md).");
else {
  const child = spawn(python, ["-m", "uvicorn", "server.main:app", "--port", "8080", "--reload", "--reload-dir", "server"],
    { cwd: root, stdio: "inherit" });
  child.on("exit", (code) => idle(`Cloud server stopped (code ${code}); engine and web keep running.`));
  for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => { child.kill(sig); process.exit(0); });
}
