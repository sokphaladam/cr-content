// Prebuilds the graphics for the desktop app: node bundle.mjs <out dir> (scripts/build_remotion.py runs it)
import { bundle } from "@remotion/bundler";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
await bundle({ entryPoint: path.join(here, "src", "index.ts"), outDir: path.resolve(process.argv[2]) });
console.log(`bundled into ${process.argv[2]}`);
