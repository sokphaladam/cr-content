"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

/** One shared audio player: play a text with a voice, click the same button again to stop. */
export function useVoicePreview(onError: (message: string) => void) {
  const audio = useRef<HTMLAudioElement | null>(null);
  const urlRef = useRef<string | null>(null);
  const activeRef = useRef<string | null>(null);
  const [active, setActive] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const stop = useCallback(() => {
    audio.current?.pause();
    activeRef.current = null;
    setActive(null);
    setLoading(false);
  }, []);

  useEffect(() => {
    const a = new Audio();
    a.onended = () => {
      activeRef.current = null;
      setActive(null);
    };
    audio.current = a;
    return () => {
      a.pause();
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    };
  }, []);

  const toggle = useCallback(
    async (id: string, text: string, voice: string, rate: string) => {
      if (activeRef.current === id) return stop();
      stop();
      if (!text.trim()) return onError("Write some narration first, then listen.");
      activeRef.current = id;
      setActive(id);
      setLoading(true);
      try {
        const blob = await api.speak(text, voice, rate);
        if (activeRef.current !== id || !audio.current) return; // another button was clicked meanwhile
        if (urlRef.current) URL.revokeObjectURL(urlRef.current);
        urlRef.current = URL.createObjectURL(blob);
        audio.current.src = urlRef.current;
        setLoading(false);
        await audio.current.play();
      } catch (err) {
        stop();
        onError((err as Error).message);
      }
    },
    [onError, stop],
  );

  return { active, loading, toggle, stop };
}
