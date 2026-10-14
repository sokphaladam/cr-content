// Appearance preferences (Settings → Appearance): theme and interface size, plus the dragged pane widths, kept in
// this browser / app window. layout.tsx applies theme and size before the first paint (lib/appearanceScript.ts).
"use client";

import { useCallback, useState, useSyncExternalStore } from "react";
import { SIZE_KEY, THEME_KEY } from "./appearanceScript";

export type Theme = "system" | "light" | "dark";
export type UiSize = "compact" | "default" | "large";

const CHANGE = "shorts-studio:pref";

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null; // private window / storage blocked
  }
}

function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* the choice still applies until the page closes */
  }
  window.dispatchEvent(new Event(CHANGE));
}

function subscribe(onChange: () => void) {
  window.addEventListener(CHANGE, onChange);
  window.addEventListener("storage", onChange); // another window of the app changed it
  return () => {
    window.removeEventListener(CHANGE, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** A saved preference as React state (the fallback before the page is in a browser). */
function usePref(key: string, fallback: string) {
  return useSyncExternalStore(subscribe, () => read(key) ?? fallback, () => fallback);
}

export function useAppearance() {
  const theme = usePref(THEME_KEY, "system") as Theme;
  const size = usePref(SIZE_KEY, "default") as UiSize;
  const setTheme = useCallback((t: Theme) => {
    write(THEME_KEY, t);
    const dark = t === "dark" || (t === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }, []);
  const setSize = useCallback((s: UiSize) => {
    write(SIZE_KEY, s);
    document.documentElement.dataset.size = s;
  }, []);
  return { theme, setTheme, size, setSize };
}

/** A pane width the user can drag, remembered between sessions. Mid-drag (done = false) only the live width changes;
 *  letting go saves it. */
export function usePaneWidth(name: string, initial: number, min: number, max: number) {
  const key = `shorts-studio.pane.${name}`;
  const saved = Number(usePref(key, String(initial))) || initial;
  const [dragging, setDragging] = useState<number | null>(null);
  const clamp = useCallback((w: number) => Math.round(Math.min(max, Math.max(min, w))), [min, max]);
  const setWidth = useCallback(
    (w: number, done = false) => {
      if (done) {
        write(key, String(clamp(w)));
        setDragging(null);
      } else setDragging(clamp(w));
    },
    [key, clamp],
  );
  const reset = useCallback(() => write(key, String(initial)), [key, initial]);
  return { width: dragging ?? clamp(saved), setWidth, reset };
}
