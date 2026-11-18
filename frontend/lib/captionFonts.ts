// The caption fonts kept in the app's own fonts folder (Settings → Caption fonts), registered with the browser so the
// live preview draws captions in the same face as the render. Fonts installed in the OS need nothing: the browser has them.
import { API_BASE, api } from "./api";

const loaded = new Set<string>();

/** Register any app fonts not registered yet. Safe to call again (after a download). */
export async function loadCaptionFonts(): Promise<void> {
  if (typeof document === "undefined" || !("fonts" in document)) return;
  let faces: { family: string; url: string }[];
  try {
    faces = await api.fontFaces();
  } catch {
    return; // engine not up yet: the preview falls back to the system font
  }
  await Promise.all(
    faces
      .filter((f) => !loaded.has(f.url))
      .map(async (f) => {
        try {
          // bold: the files are Bold cuts, and the captions ask for bold
          const face = await new FontFace(f.family, `url("${API_BASE}${f.url}")`, { weight: "100 900" }).load();
          document.fonts.add(face);
          loaded.add(f.url);
        } catch {
          /* a bad file: the preview uses the fallback for that family */
        }
      }),
  );
}
