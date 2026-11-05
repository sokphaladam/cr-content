// Renders a batch of graphics as transparent WebM clips: node render.mjs <jobs.json>
// jobs.json: {"clips": [{"id": "Fact", "props": {...}, "out": "<file.webm>"}]}
// Uses the prebuilt bundle next to this file when there is one (the desktop app: scripts/build_remotion.py), else
// bundles src/ once for the batch (development). Prints one line per finished clip.
import { renderMedia, selectComposition } from "@remotion/renderer";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const jobs = JSON.parse(readFileSync(process.argv[2], "utf8"));
const port = Number(process.env.REMOTION_PORT || 3457);  // 3000 is the app's Next.js dev server
const prebuilt = path.join(here, "bundle");
const serveUrl = existsSync(path.join(prebuilt, "index.html"))
  ? prebuilt
  : await (await import("@remotion/bundler")).bundle({ entryPoint: path.join(here, "src", "index.ts") });
for (const clip of jobs.clips) {
  const composition = await selectComposition({ serveUrl, port, id: clip.id, inputProps: clip.props });
  await renderMedia({
    serveUrl, port, composition, inputProps: clip.props, outputLocation: clip.out,
    codec: "vp8", imageFormat: "png", pixelFormat: "yuva420p",  // keeps the alpha channel
    chromiumOptions: { gl: "angle" },
  });
  console.log(`rendered ${clip.out}`);
}
