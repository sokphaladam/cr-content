import { useCallback, useSyncExternalStore } from "react";

/** What a track's licence allows in a video you earn from (crcontent/music.py licence_use). */
export type MusicUse = "ok" | "nc" | "nd" | "unknown";

export const USE_LABEL: Record<Exclude<MusicUse, "ok">, string> = {
  nc: "Non-commercial",
  nd: "No derivatives",
  unknown: "Licence unknown",
};

export const USE_HINT: Record<Exclude<MusicUse, "ok">, string> = {
  nc: "Non-commercial licence: not for monetized videos.",
  nd: "No-derivatives licence: putting music to video counts as an adaptation, so it can't be used in videos.",
  unknown: "No licence saved with this track: check it before using it in a monetized video.",
};

// "Only music I can use in monetized videos": one setting for the music menu and the music search, kept per browser
const KEY = "music-monetizable-only";
const EVENT = "music-monetizable-only";

function read(): boolean {
  try {
    return localStorage.getItem(KEY) !== "0"; // on unless turned off
  } catch {
    return true;
  }
}

function subscribe(listener: () => void) {
  window.addEventListener(EVENT, listener);
  window.addEventListener("storage", listener);
  return () => {
    window.removeEventListener(EVENT, listener);
    window.removeEventListener("storage", listener);
  };
}

export function useMonetizableOnly(): [boolean, (on: boolean) => void] {
  const on = useSyncExternalStore(subscribe, read, () => true);
  const set = useCallback((next: boolean) => {
    try {
      localStorage.setItem(KEY, next ? "1" : "0");
    } catch {
      // private window: the setting just isn't remembered
    }
    window.dispatchEvent(new Event(EVENT));
  }, []);
  return [on, set];
}
