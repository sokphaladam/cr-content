import { loadFont } from "@remotion/fonts";
import { useEffect, useState } from "react";
import { cancelRender, continueRender, delayRender, staticFile } from "remotion";

/** The Short's caption face (a data: URL, or a file in the public dir); "" = a system sans. Rendering waits for it. */
export function useFont(file: string): string {
  const [handle] = useState(() => (file ? delayRender("font") : null));
  useEffect(() => {
    if (handle === null) return;
    loadFont({
      family: "ShortHeavy", url: file.startsWith("data:") ? file : staticFile(file),
      format: /^data:font\/otf|\.otf$/i.test(file) ? "opentype" : "truetype",  // a data: URL has no extension to go by
    }).then(() => continueRender(handle), cancelRender);
  }, [file, handle]);
  return file ? "ShortHeavy" : "Arial Black, system-ui, sans-serif";
}
