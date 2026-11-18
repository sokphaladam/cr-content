// npm run dev: the desktop app with hot reload, on the first free port from 3000 (another project may be using 3000).
// The Next.js dev server, the window's URL and the engine's CORS (CRCONTENT_UI_PORT) all get that port.
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const free = (port) =>
  new Promise((ok) => {
    const s = createServer()
      .once("error", () => ok(false))
      .listen(port, () => s.close(() => ok(true)));
  });

let port = 3000;
while (!(await free(port))) port++;
if (port !== 3000) console.log(`Port 3000 is busy: using ${port}.`);

// a config file rather than inline JSON: no shell quoting differences between Windows and macOS
const config = join(tmpdir(), `shorts-studio-dev-${port}.json`);
writeFileSync(config, JSON.stringify({
  build: {
    devUrl: `http://localhost:${port}`,
    beforeDevCommand: { script: `npm run dev:web -- -p ${port}`, cwd: "../frontend" },
  },
}));

const child = spawn("npx", ["tauri", "dev", "--config", config, ...process.argv.slice(2)], {
  cwd: root,
  stdio: "inherit",
  shell: process.platform === "win32", // npx is npx.cmd on Windows
  env: { ...process.env, CRCONTENT_UI_PORT: String(port) },
});
child.on("exit", (code) => process.exit(code ?? 0));
for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => child.kill(sig));
