// Renders preview frames of graphics as transparent PNGs: node still.mjs <jobs.json>
// jobs.json: {"bundle": "<dir>", "stills": [{"id": "Fact", "props": {...}, "frame": 20, "out": "<file.png>"}]}
// "bundle": a prebuilt bundle (the desktop app's), or a cache dir that src/ is bundled into once when it's empty.
// Prints "ok <out>" or "failed <out> <reason>" per still, so one bad graphic doesn't lose the others.
import { renderStill, selectComposition } from "@remotion/renderer";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const jobs = JSON.parse(readFileSync(process.argv[2], "utf8"));
const port = Number(process.env.REMOTION_PORT || 3458);
const serveUrl = jobs.bundle;
if (!existsSync(path.join(serveUrl, "index.html"))) {
  await (await import("@remotion/bundler")).bundle({ entryPoint: path.join(here, "src", "index.ts"), outDir: serveUrl });
}
for (const s of jobs.stills) {
  try {
    const composition = await selectComposition({ serveUrl, port, id: s.id, inputProps: s.props });
    await renderStill({
      serveUrl, port, composition, inputProps: s.props, output: s.out, imageFormat: "png",
      frame: Math.max(0, Math.min(s.frame, composition.durationInFrames - 1)), chromiumOptions: { gl: "angle" },
    });
    console.log(`ok ${s.out}`);
  } catch (e) {
    console.log(`failed ${s.out} ${String(e?.message ?? e).split("\n")[0]}`);
  }
}
