"use client";

import { Clapperboard, Maximize2, Minimize2, MonitorPlay } from "lucide-react";
import { Fragment, useEffect, useRef, useState } from "react";
import { fileUrl, outputUrl, type Aspect, type Lang, type LyricStyle, type MusicVideoSettings, type SongArtSlot, type VideoSummary } from "@/lib/api";
import { fmt, lineEnd, lineStart, type PictureClip, type Row } from "@/lib/lyricTiming";
import { fontFor, fromPreset, LOOK_CSS, SCENE_BG, SIZE_PX, textCss, useStyleCatalog } from "./MusicVideoOptions";

type Mode = "preview" | "render";

/** The lyric line drawn the way the render draws it: style, colours, effect, position and size. */
function Caption({ line, now, style, font, lang, aspect }: { line: Row; now: number; style: LyricStyle; font: string; lang: Lang; aspect: Aspect }) {
  const top = { low: aspect === "16:9" ? "80%" : "64%", middle: "50%", high: aspect === "16:9" ? "20%" : "24%" }[style.position];
  const display = (w: string) => (lang === "km" ? w : style.case === "upper" ? w.toUpperCase() : style.case === "lower" ? w.toLowerCase() : w);
  const s = lineStart(line);
  const e = lineEnd(line);
  const fadeIn = Math.min(1, Math.max(0, (now - (s - 0.25)) / 0.25));
  const fadeOut = Math.min(1, Math.max(0, (e + 0.3 - now) / 0.3));
  return (
    <p
      lang={lang}
      className="absolute inset-x-[6%] m-0 -translate-y-1/2 text-center leading-tight"
      style={{ top, fontSize: `${(aspect === "16:9" ? 4.6 : 7.4) * SIZE_PX[style.size]}cqw` }}
    >
      <span
        className={style.outline === "box" ? "rounded-[0.15em] bg-black/40 box-decoration-clone px-[0.25em] py-[0.05em]" : ""}
        style={{ opacity: style.effect === "fade" ? Math.min(fadeIn, fadeOut) : 1 }}
      >
        {line.words.map((w, i) => {
          const sung = style.effect !== "fade" && w.start <= now;
          const hidden = style.effect === "pop" && w.start > now;
          return (
            <Fragment key={i}>
            <span
              style={{
                ...textCss(style, font, sung),
                opacity: hidden ? 0 : 1,
                display: "inline-block",
                scale: style.effect === "pop" && !hidden && now - w.start < 0.09 ? 0.85 + ((now - w.start) / 0.09) * 0.15 : undefined,
                transition: style.effect === "fill" ? "color 0.3s" : undefined,
              }}
            >
              {display(w.text)}
            </span>
            {i < line.words.length - 1 ? " " : ""}
            </Fragment>
          );
        })}
      </span>
    </p>
  );
}

/** The program monitor: a live preview of the music video at the playhead (the song's pictures, colour look and lyric
 *  style), or the last rendered music video played in sync with the song. */
export function LyricMonitor({
  lang,
  aspect,
  lines,
  sections,
  now,
  playing,
  settings,
  slots,
  clips,
  latest,
  big,
  onBig,
}: {
  lang: Lang;
  aspect: Aspect;
  lines: Row[];
  sections: string[];
  now: number;
  playing: boolean;
  settings: MusicVideoSettings;
  slots: SongArtSlot[];
  clips: PictureClip[]; // the planned pictures placed on the song
  latest: VideoSummary | null | undefined; // the last rendered music video (undefined = still loading)
  big: boolean;
  onBig: () => void;
}) {
  const catalog = useStyleCatalog();
  const [mode, setMode] = useState<Mode>("preview");
  const video = useRef<HTMLVideoElement>(null);

  // keep the last render in step with the song (muted: the song plays from the editor's own player)
  useEffect(() => {
    const v = video.current;
    if (!v || mode !== "render") return;
    if (Math.abs(v.currentTime - now) > (playing ? 0.3 : 0.04)) v.currentTime = now;
    if (playing && v.paused) void v.play().catch(() => {});
    if (!playing && !v.paused) v.pause();
  }, [now, playing, mode, latest]);

  const style = catalog ? (settings.lyric_style ?? fromPreset(catalog, "classic")) : null;
  const look = settings.look || "natural";
  const usePictures = settings.art_style !== "";
  const clip = usePictures ? clips.findLast((c) => c.start <= now && slots[c.slot]?.picture) : undefined;
  const pic = clip ? clips.indexOf(clip) : -1;
  const slot = clip ? slots[clip.slot] : null;
  const line = lines.find((l) => lineStart(l) - 0.25 <= now && now <= lineEnd(l) + 0.3) ?? null;
  const singing = lines.find((l) => lineStart(l) <= now && now <= lineEnd(l));
  const next = lines.find((l) => lineStart(l) > now);

  const frame = aspect === "16:9" ? "aspect-video w-full" : `aspect-[9/16] ${big ? "h-[min(62vh,46rem)]" : "h-[min(40vh,22rem)]"}`;
  const tab = (m: Mode, label: string, Icon: typeof MonitorPlay) => (
    <button
      type="button"
      role="tab"
      aria-selected={mode === m}
      onClick={() => setMode(m)}
      className={`inline-flex h-6 cursor-pointer items-center gap-1 rounded px-2 text-2xs font-semibold tracking-wide uppercase transition-colors ${
        mode === m ? "bg-white/15 text-white" : "text-white/50 hover:text-white/80"
      }`}
    >
      <Icon className="size-3" />
      {label}
    </button>
  );

  return (
    <div className="overflow-hidden rounded-lg bg-media text-white shadow-(--shadow-card)">
      <div className="flex items-center gap-1 px-2 pt-2">
        <div role="tablist" aria-label="Monitor" className="flex gap-0.5">
          {tab("preview", "Preview", MonitorPlay)}
          {tab("render", "Last render", Clapperboard)}
        </div>
        <span className="flex-1" />
        <span className="font-mono text-xs text-white/80 tabular-nums">{fmt(now, 2)}</span>
        <button
          type="button"
          aria-label={big ? "Smaller monitor" : "Bigger monitor"}
          title={big ? "Smaller monitor" : "Bigger monitor"}
          onClick={onBig}
          className="grid size-6 cursor-pointer place-items-center rounded text-white/60 hover:bg-white/10 hover:text-white"
        >
          {big ? <Minimize2 className="size-3.5" /> : <Maximize2 className="size-3.5" />}
        </button>
      </div>

      <div className="grid place-items-center p-2">
        <div className={`@container relative overflow-hidden rounded bg-black ${frame}`}>
          {mode === "preview" ? (
            <>
              <div className="absolute inset-0" style={{ filter: LOOK_CSS[look] }}>
                {slot?.picture ? (
                  slot.picture.kind === "video" ? (
                    <video key={pic} src={fileUrl(slot.picture.media)} autoPlay loop muted playsInline className="size-full object-cover" />
                  ) : (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      key={pic}
                      src={fileUrl(slot.picture.media)}
                      alt=""
                      className="size-full animate-[monitor-drift_9s_ease-out_forwards] object-cover"
                      style={{ animationPlayState: playing ? "running" : "paused" }}
                    />
                  )
                ) : (
                  <div className="size-full" style={{ background: SCENE_BG }} />
                )}
              </div>
              {line && style && catalog && <Caption line={line} now={now} style={style} font={fontFor(catalog, style, lang)} lang={lang} aspect={aspect} />}
            </>
          ) : latest ? (
            <video key={latest.name} ref={video} src={outputUrl(latest.name, "video.mp4")} muted playsInline preload="auto" className="size-full object-contain" />
          ) : (
            <div className="grid size-full place-items-center p-4 text-center text-sm text-white/50">
              {latest === undefined ? "Loading…" : "No music video yet. Make one and it plays here, in step with the song."}
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 px-3 pb-2.5 text-xs text-white/50">
        <span className="shrink-0 font-semibold tracking-wide uppercase">{singing ? sections[singing.section] || "Lyrics" : playing ? "Instrumental" : "Paused"}</span>
        <span lang={lang} className="min-w-0 flex-1 truncate text-right">
          {mode === "render"
            ? latest
              ? `Rendered ${new Date(latest.created).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}`
              : ""
            : next
              ? `Next: ${next.text}`
              : ""}
        </span>
      </div>
    </div>
  );
}
