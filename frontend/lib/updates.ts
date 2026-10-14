// Desktop app updates: one shared state for the update banner (components/UpdateNotice.tsx) and Settings → About.
// The app checks GitHub Releases when it starts and every few hours (unless turned off), or when asked.
"use client";

import { useSyncExternalStore } from "react";
import { appVersion, checkUpdate, installUpdate, type AppUpdate } from "./api";

export type UpdateStatus = "idle" | "checking" | "latest" | "available" | "downloading" | "installing" | "error";

export interface UpdateState {
  desktop: boolean; // false in the browser: nothing to update
  version: string; // this app's version
  status: UpdateStatus;
  update: AppUpdate | null;
  progress: { downloaded: number; total: number | null } | null;
  error: string;
  installFailed: boolean; // the last install attempt failed (the banner offers to try again)
  checkedAt: number; // ms, 0 = not yet
}

const AUTO_KEY = "shorts-studio.update-auto";
const DISMISSED_KEY = "shorts-studio.update-dismissed";
const EVERY_MS = 6 * 60 * 60 * 1000;
const FIRST_CHECK_MS = 8000; // after start-up, once the engine and the page have settled

let state: UpdateState = { desktop: false, version: "", status: "idle", update: null, progress: null, error: "", installFailed: false, checkedAt: 0 };
const listeners = new Set<() => void>();
const SERVER: UpdateState = state;

function set(changes: Partial<UpdateState>) {
  state = { ...state, ...changes };
  listeners.forEach((l) => l());
}

function pref(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function setPref(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* lasts until the window closes */
  }
  listeners.forEach((l) => l());
}

export function autoCheck(): boolean {
  return pref(AUTO_KEY) !== "off";
}

export function setAutoCheck(on: boolean) {
  setPref(AUTO_KEY, on ? "on" : "off");
}

/** The banner stays hidden for a version you closed it for (Settings still shows it). */
export function dismissed(version: string): boolean {
  return pref(DISMISSED_KEY) === version;
}

export function dismiss(version: string) {
  setPref(DISMISSED_KEY, version);
}

export async function checkNow(): Promise<void> {
  if (!state.desktop || state.status === "checking" || state.status === "downloading" || state.status === "installing") return;
  set({ status: "checking", error: "" });
  try {
    const update = await checkUpdate();
    set({ status: update ? "available" : "latest", update: update ?? null, checkedAt: Date.now() });
  } catch (e) {
    set({ status: "error", error: friendly(String((e as Error)?.message ?? e)), checkedAt: Date.now() });
  }
}

export async function install(): Promise<void> {
  if (!state.update || ["checking", "downloading", "installing"].includes(state.status)) return;
  if (state.status !== "available") {
    await checkNow(); // after a failed attempt: the app needs the update found again
    if ((state.status as UpdateStatus) !== "available") return; // checkNow changed it
  }
  set({ status: "downloading", progress: { downloaded: 0, total: null }, error: "", installFailed: false });
  const onProgress = (e: Event) => {
    const d = (e as CustomEvent<{ downloaded: number; total: number | null }>).detail;
    set({ progress: d, status: d.total && d.downloaded >= d.total ? "installing" : "downloading" });
  };
  window.addEventListener("desktop-update", onProgress);
  try {
    await installUpdate(); // the app restarts (Windows: the installer takes over) when this succeeds
    set({ status: "installing" });
  } catch (e) {
    set({ status: "error", error: friendly(String((e as Error)?.message ?? e)), progress: null, installFailed: true });
  } finally {
    window.removeEventListener("desktop-update", onProgress);
  }
}

/** Updater errors in plain words (offline is the usual one). */
function friendly(message: string): string {
  if (/error sending request|dns|network|connect|timed out/i.test(message)) return "Couldn't reach GitHub. Check the internet connection and try again.";
  if (/404|not found|could not fetch a valid release json/i.test(message)) return "No release has been published on GitHub yet.";
  if (/signature/i.test(message)) return "The update's signature didn't match, so it wasn't installed.";
  return message;
}

let started = false;

/** Once per window: learn the version, then check on start-up and every few hours while automatic checks are on. */
export function startUpdates() {
  if (started || typeof window === "undefined" || !window.__TAURI_INTERNALS__) return;
  started = true;
  set({ desktop: true });
  appVersion()
    .then((version) => set({ version: version ?? "" }))
    .catch(() => {});
  const tick = () => autoCheck() && void checkNow();
  window.setTimeout(tick, FIRST_CHECK_MS);
  window.setInterval(tick, EVERY_MS);
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useUpdates(): UpdateState {
  return useSyncExternalStore(subscribe, () => state, () => SERVER);
}

/** The automatic-check preference as React state. */
export function useAutoCheck(): boolean {
  return useSyncExternalStore(subscribe, autoCheck, () => true);
}
