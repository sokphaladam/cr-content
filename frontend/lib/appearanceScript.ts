// Applies the saved appearance (lib/appearance.ts) before the first paint. Plain module: layout.tsx (a server
// component) inlines it, so it must not import React hooks.

export const THEME_KEY = "shorts-studio.theme";
export const SIZE_KEY = "shorts-studio.size";

/** Inline script for <head>: resolves the saved theme ("system" by the OS) and size onto <html> before paint. */
export const APPEARANCE_SCRIPT = `(function(){try{
var d=document.documentElement,s=localStorage.getItem("${SIZE_KEY}")||"default";
var m=window.matchMedia("(prefers-color-scheme: dark)");
function apply(){var x=localStorage.getItem("${THEME_KEY}")||"system";d.dataset.theme=x==="system"?(m.matches?"dark":"light"):x;}
apply();d.dataset.size=s;m.addEventListener("change",apply);
}catch(e){}})();`;
