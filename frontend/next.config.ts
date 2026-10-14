import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Plain static files in out/: the desktop app (src-tauri) bundles them; the engine API is called from the browser.
  output: "export",
  // frontend/ is its own project, even though the project root also has a package.json (the desktop app's)
  turbopack: { root: dirname(fileURLToPath(import.meta.url)) },
  // dev only: keep Next's badge off the navigation rail's Settings button
  devIndicators: { position: "bottom-right" },
};

export default nextConfig;
