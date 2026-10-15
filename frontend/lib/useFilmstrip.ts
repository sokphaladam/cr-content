import { useEffect, useRef, useState } from "react";

/**
 * Still frames of a video at the given times, for a filmstrip. Frames are grabbed one at a time from a hidden video
 * (seek, draw to a small canvas) and kept for the life of the component, so scrolling back is instant.
 */
export function useFilmstrip(src: string | null, times: number[], height = 72): Record<number, string> {
  const [store, setStore] = useState<{ src: string | null; frames: Record<number, string> }>({ src: null, frames: {} });
  const done = useRef(new Set<number>());
  const want = useRef<number[]>([]);
  const kick = useRef<() => void>(() => {});

  useEffect(() => {
    done.current = new Set();
    if (!src) return;
    const video = document.createElement("video");
    video.crossOrigin = "anonymous"; // the engine sends CORS headers, so the canvas stays readable
    video.muted = true;
    video.preload = "auto";
    video.src = src;
    const canvas = document.createElement("canvas");
    let busy = false;
    let ready = false;
    let current = -1;
    let dead = false;

    const next = () => {
      if (dead || busy || !ready) return;
      const t = want.current.find((x) => !done.current.has(x) && x <= video.duration);
      if (t === undefined) return;
      busy = true;
      current = t;
      video.currentTime = Math.min(t + 0.05, Math.max(0, video.duration - 0.05));
    };
    const onSeeked = () => {
      if (dead) return;
      const w = Math.round((height * video.videoWidth) / Math.max(1, video.videoHeight));
      canvas.width = w;
      canvas.height = height;
      const g = canvas.getContext("2d");
      done.current.add(current);
      if (g && w > 0) {
        try {
          g.drawImage(video, 0, 0, w, height);
          const url = canvas.toDataURL("image/jpeg", 0.6);
          const t = current;
          setStore((s) => (s.src === src ? { src, frames: { ...s.frames, [t]: url } } : { src, frames: { [t]: url } }));
        } catch {
          // a tainted canvas (no CORS): give up on frames rather than retrying forever
          dead = true;
        }
      }
      busy = false;
      next();
    };
    const onReady = () => {
      ready = true;
      next();
    };
    video.addEventListener("loadeddata", onReady);
    video.addEventListener("seeked", onSeeked);
    kick.current = next;
    return () => {
      dead = true;
      kick.current = () => {};
      video.removeEventListener("loadeddata", onReady);
      video.removeEventListener("seeked", onSeeked);
      video.removeAttribute("src");
      video.load();
    };
  }, [src, height]);

  const key = times.join(",");
  useEffect(() => {
    want.current = times;
    kick.current();
    // `key` stands for `times`, which is a new array on every render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return store.src === src ? store.frames : {};
}
