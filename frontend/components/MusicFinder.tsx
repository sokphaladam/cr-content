"use client";

import { Pause, Play, Plus, Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, type MusicResult } from "@/lib/api";
import { USE_HINT, USE_LABEL, useMonetizableOnly, type MusicUse } from "@/lib/musicLicence";
import { Button, IconButton, Spinner } from "./ui";

const length = (sec: number) => `${Math.floor(sec / 60)}:${String(Math.round(sec % 60)).padStart(2, "0")}`;

/**
 * Search free instrumental music on Jamendo, listen to a track, and add it to the music library (assets/music) and to
 * this draft. The track's credit is put in the video's description automatically.
 */
export function MusicFinder({
  initialQuery,
  ready,
  onPicked,
  onClose,
}: {
  initialQuery: string;
  ready: boolean; // a Jamendo client ID is set
  onPicked: (file: string) => void;
  onClose: () => void;
}) {
  const [q, setQ] = useState(initialQuery);
  const [results, setResults] = useState<MusicResult[] | null>(null);
  const [status, setStatus] = useState<{ text: string; error?: boolean }>({ text: "" });
  const [playing, setPlaying] = useState<string | null>(null);
  const [adding, setAdding] = useState<string | null>(null);
  const audio = useRef<HTMLAudioElement | null>(null);
  const [safeOnly, setSafeOnly] = useMonetizableOnly();
  // an older engine sends only `commercial`
  const licenceOf = (t: MusicResult): MusicUse => t.use ?? (t.commercial ? "ok" : "nc");
  const shown = results && safeOnly ? results.filter((t) => licenceOf(t) === "ok") : results;
  const hidden = (results?.length ?? 0) - (shown?.length ?? 0);

  useEffect(() => () => audio.current?.pause(), []);

  async function search(query = q) {
    if (!query.trim()) return;
    setResults(null);
    setStatus({ text: "Searching Jamendo…" });
    try {
      const { results } = await api.musicSearch(query.trim());
      setResults(results);
      setStatus({ text: results.length ? "" : "Nothing found. Try other words, like calm piano or upbeat drums." });
    } catch (e) {
      setResults([]);
      setStatus({ text: (e as Error).message, error: true });
    }
  }

  function listen(t: MusicResult) {
    audio.current?.pause();
    if (playing === t.id) return setPlaying(null);
    const el = new Audio(t.preview);
    el.onended = () => setPlaying(null);
    el.play().catch(() => setStatus({ text: "Couldn't play this preview.", error: true }));
    audio.current = el;
    setPlaying(t.id);
  }

  async function add(t: MusicResult) {
    setAdding(t.id);
    setStatus({ text: `Downloading “${t.name}”…` });
    try {
      const { file } = await api.musicPick(t.id);
      audio.current?.pause();
      setPlaying(null);
      onPicked(file);
      setStatus({ text: `“${t.name}” added to your music and set for this video. Its credit goes in the description.` });
    } catch (e) {
      setStatus({ text: (e as Error).message, error: true });
    } finally {
      setAdding(null);
    }
  }

  return (
    <section aria-label="Find music" className="grid gap-2.5 well p-3">
      <div className="flex items-center gap-2">
        <form
          className="flex min-w-0 flex-1 items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void search();
          }}
        >
          <div className="relative min-w-0 flex-1">
            <Search aria-hidden className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-ink-soft" />
            <input
              aria-label="Search free music"
              className="field-input h-8 py-0 pl-8 text-base"
              value={q}
              disabled={!ready}
              placeholder="Mood or style, e.g. playful pizzicato"
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <Button size="sm" type="submit" disabled={!ready}>
            Search
          </Button>
        </form>
        <IconButton label="Close music search" onClick={onClose}>
          <X className="size-4" />
        </IconButton>
      </div>

      {!ready ? (
        <p className="m-0 text-sm leading-snug text-ink-soft">
          Free music search uses Jamendo. Create a free app at <b>devportal.jamendo.com</b>, then paste its client ID in <b>Settings → Jamendo</b>.
        </p>
      ) : (
        <>
          {results === null && status.text && (
            <div className="grid h-16 place-items-center text-ink-soft">
              <Spinner />
            </div>
          )}
          {results && results.length > 0 && (
            <label className="flex items-center gap-1.5 text-sm text-ink-soft">
              <input type="checkbox" className="size-3.5" checked={safeOnly} onChange={(e) => setSafeOnly(e.target.checked)} />
              Only music I can use in monetized videos{safeOnly && hidden > 0 ? ` (${hidden} hidden)` : ""}
            </label>
          )}
          {results && results.length > 0 && shown?.length === 0 && (
            <p className="m-0 text-sm text-ink-soft">All of these are non-commercial or no-derivatives. Try other words, or untick the filter to see them.</p>
          )}
          {shown && shown.length > 0 && (
            <ul className="m-0 grid max-h-64 list-none gap-1 overflow-y-auto p-0">
              {shown.map((t) => (
                <li key={t.id} className="flex items-center gap-2 rounded-lg bg-panel px-2 py-1.5">
                  <IconButton label={playing === t.id ? `Stop ${t.name}` : `Listen to ${t.name}`} onClick={() => listen(t)}>
                    {playing === t.id ? <Pause className="size-4 fill-current" /> : <Play className="size-4 fill-current" />}
                  </IconButton>
                  <span className="grid min-w-0 flex-1 leading-tight">
                    <span className="flex min-w-0 items-center gap-1.5">
                      <span className="truncate text-base font-semibold">{t.name}</span>
                      {licenceOf(t) !== "ok" && (
                        <span title={USE_HINT[licenceOf(t) as Exclude<MusicUse, "ok">]} className="shrink-0 rounded bg-warn/15 px-1 text-2xs font-semibold text-warn">
                          {USE_LABEL[licenceOf(t) as Exclude<MusicUse, "ok">]}
                        </span>
                      )}
                    </span>
                    <span className="truncate text-xs text-ink-soft">
                      {t.artist} · {length(t.duration)}
                      {t.tags.length > 0 && ` · ${t.tags.join(", ")}`}
                    </span>
                  </span>
                  <Button size="sm" variant="secondary" icon={<Plus className="size-3.5" />} loading={adding === t.id} disabled={adding !== null} onClick={() => add(t)}>
                    Use
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      {status.text && (
        <p role="status" className={`m-0 text-sm ${status.error ? "text-danger" : "text-ink-soft"}`}>
          {status.text}
        </p>
      )}
    </section>
  );
}
