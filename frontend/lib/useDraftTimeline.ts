"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { DraftScene } from "@/components/SceneCard";
import { api, type SceneVoice } from "./api";
import { TimelinePlayer } from "./timelinePlayer";

/** A scene's voiceover and what it was made from (it's stale once the narration, voice or speed changes). */
export type Voiced = SceneVoice & { narration: string; sig: string };

/** One scene on the video's timeline. `voice` is null for silent scenes and while the voiceover is being made. */
export interface Segment {
  index: number;
  scene: DraftScene;
  start: number; // seconds into the video
  length: number; // 0 = not in the video (no voiceover yet, or nothing to say)
  voice: Voiced | null;
  cuts: [number, number][]; // seconds of `voice` that the render cuts out
  footage: string | null; // the scene's own media, else the clip the render picks automatically (null = none found)
  footage2: string | null; // split layout: the clip below, chosen or picked automatically
}

export const cutBefore = (cuts: [number, number][], t: number) => cuts.reduce((sum, [a, b]) => sum + Math.min(Math.max(t - a, 0), b - a), 0);

/** Seconds into a scene's voiceover for `offset` seconds of the scene on the video (cut stretches are skipped). */
function audioTime(seg: Segment, offset: number) {
  let t = offset;
  for (const [a, b] of [...seg.cuts].sort((x, y) => x[0] - y[0])) if (t >= a) t += b - a;
  return seg.voice ? Math.min(t, seg.voice.duration) : t;
}

/** Scenes the render keeps: those with a voiceover or a silent beat's length. */
const rendered = (s: DraftScene) => !!s.narration.trim() || !!s.seconds;

/**
 * The open draft as a playable timeline, shared by the transcript editor and the live preview: each scene's
 * voiceover (made by the engine and cached, the render reuses it), the footage the render will show, and one player
 * with its playhead. Nothing is fetched until activate() (opening the transcript, or pressing play in the preview).
 */
export function useDraftTimeline(scenes: DraftScene[] | null, voice: string, rate: string) {
  const sig = `${voice}|${rate}`;
  const [active, setActive] = useState(false);
  const [voices, setVoices] = useState<Record<string, Voiced>>({});
  const [pad, setPad] = useState(0.25);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const [auto, setAuto] = useState<{ key: string; media: Record<string, string | null> }>({ key: "", media: {} });
  const [pos, setPos] = useState({ i: 0, t: 0 }); // playhead: scene index and seconds into its voiceover
  const [playing, setPlaying] = useState(false);
  const [playWhenReady, setPlayWhenReady] = useState(false);
  const [player] = useState(
    () =>
      new TimelinePlayer(
        api.voiceoverUrl,
        (i, t) => setPos({ i, t }),
        (on) => {
          setPlaying(on);
          if (on) setPlayWhenReady(false);
        },
      ),
  );
  const list = useMemo(() => scenes ?? [], [scenes]);
  const open = scenes !== null;

  // closing the draft stops everything; the next one starts idle
  const [wasOpen, setWasOpen] = useState(open);
  if (wasOpen !== open) {
    setWasOpen(open);
    if (!open) {
      setActive(false);
      setPlayWhenReady(false);
      setPos({ i: 0, t: 0 });
    }
  }
  useEffect(() => {
    if (!open) player.stop();
  }, [open, player]);
  useEffect(() => () => player.stop(), [player]);

  // ---------- voiceover: (re)made for scenes whose narration, voice or speed changed ----------
  const stale = list
    .filter((s) => {
      const v = voices[s.uid];
      return s.narration.trim() && !(v && v.narration === s.narration && v.sig === sig);
    })
    .map((s) => ({ uid: s.uid, narration: s.narration }));
  const staleKey = stale.map((s) => `${s.uid}:${s.narration}`).join("\n");

  useEffect(() => {
    if (!active || !staleKey) return;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {
        const res = await api.voiceover(
          stale.map((s) => s.narration),
          voice,
          rate,
        );
        setPad(res.pad);
        setVoices((all) => {
          const next = { ...all };
          stale.forEach((s, k) => {
            const made = res.scenes[k];
            if (made) next[s.uid] = { ...made, narration: s.narration, sig };
          });
          return next;
        });
        setError(null);
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setLoading(false);
      }
    }, 600);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- staleKey and sig capture everything `stale` depends on
  }, [active, staleKey, sig, retry]);

  // ---------- automatic footage: the clips the render will pick, in its order ----------
  // (every scene's own clip first, then the second clips of split scenes, like crcontent/pipeline.py)
  const kept = list.filter(rendered);
  const autoScenes = [
    ...kept.filter((s) => !s.media).map((s) => ({ key: s.uid, query: s.visual_query })),
    ...kept.filter((s) => s.layout === "split" && !s.media2).map((s) => ({ key: `${s.uid}:2`, query: s.visual_query })),
  ];
  const autoKey = autoScenes.map((s) => `${s.key}:${s.query}`).join("\n");
  const [findingFootage, setFindingFootage] = useState(false);
  useEffect(() => {
    if (!active || !autoKey || auto.key === autoKey) return;
    const todo = autoScenes;
    const timer = window.setTimeout(async () => {
      setFindingFootage(true);
      try {
        const { media } = await api.autoFootage(todo.map((s) => s.query));
        setAuto({ key: autoKey, media: Object.fromEntries(todo.map((s, k) => [s.key, media[k] ?? null])) });
      } catch {
        setAuto({ key: autoKey, media: {} }); // the preview falls back to the gradient; the render still picks
      } finally {
        setFindingFootage(false);
      }
    }, 800);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- autoKey captures everything `autoScenes` depends on
  }, [active, autoKey]);

  // ---------- timeline ----------
  const segments = useMemo(() => {
    const out: Segment[] = [];
    let start = 0;
    for (const [index, scene] of list.entries()) {
      const v = voices[scene.uid];
      const voiceNow = scene.narration.trim() && v && v.narration === scene.narration && v.sig === sig ? v : null;
      const cuts = voiceNow && scene.cuts_key === voiceNow.key ? (scene.cuts ?? []) : [];
      const length = scene.narration.trim() ? (voiceNow ? voiceNow.duration - cutBefore(cuts, voiceNow.duration) + pad : 0) : (scene.seconds ?? 0);
      const footage = scene.media || auto.media[scene.uid] || null;
      const footage2 = scene.layout === "split" ? scene.media2 || auto.media[`${scene.uid}:2`] || null : null;
      out.push({ index, scene, start, length, voice: voiceNow, cuts, footage, footage2 });
      start += length;
    }
    return out;
  }, [list, voices, sig, pad, auto]);
  const total = segments.reduce((sum, s) => sum + s.length, 0);
  const current = segments[pos.i];
  const now = current ? current.start + pos.t - cutBefore(current.cuts, pos.t) : 0;

  useEffect(() => {
    player.update(
      segments.map((s) => ({ length: s.length, key: s.voice?.key ?? null, duration: s.voice?.duration ?? 0, cuts: s.cuts })),
      pad,
    );
  }, [player, segments, pad]);

  // "play" pressed before the voiceover existed: start as soon as the first scene is voiced
  const ready = segments.some((s) => s.length > 0);
  useEffect(() => {
    if (playWhenReady && !loading && ready) player.play(pos.i, pos.t); // playing clears playWhenReady
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only when it becomes ready
  }, [playWhenReady, loading, ready]);

  return {
    active,
    activate: useCallback(() => setActive(true), []),
    segments,
    total,
    now,
    pos,
    playing,
    loading,
    findingFootage,
    error,
    retry: () => setRetry((r) => r + 1),
    pending: playWhenReady,
    toggle() {
      if (playing) return player.stop();
      setActive(true);
      if (ready && !loading) player.play(pos.i, pos.t);
      else setPlayWhenReady((p) => !p);
    },
    stop: () => player.stop(),
    /** Jump to `t` seconds into scene `i`'s voiceover (keeps playing if it was). */
    seek: (i: number, t: number) => player.seek(i, t),
    /** Jump to `sec` seconds into the video. */
    seekTime(sec: number) {
      const seg = segments.find((s) => s.length > 0 && sec < s.start + s.length) ?? segments.findLast((s) => s.length > 0);
      if (seg) player.seek(seg.index, audioTime(seg, Math.max(0, sec - seg.start)));
    },
    /** Jump to the start of a scene. */
    seekScene: (uid: string) => {
      const seg = segments.find((s) => s.scene.uid === uid);
      if (seg) player.seek(seg.index, 0);
    },
  };
}

export type DraftTimeline = ReturnType<typeof useDraftTimeline>;
