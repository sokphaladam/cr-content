"use client";

import { ExternalLink, Search, Wand2 } from "lucide-react";
import { useState } from "react";
import { api, type Lang, type Outlier } from "@/lib/api";
import { Button, Segmented } from "./ui";

const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });

function length(seconds: number) {
  const m = Math.floor(seconds / 60);
  return m >= 60 ? `${Math.floor(m / 60)}:${String(m % 60).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}` : `${m}:${String(seconds % 60).padStart(2, "0")}`;
}

/** Proven ideas, weakly packaged: YouTube videos with 5x+ more views than their channel's subscribers, judged by
 * Claude for a weak title, thumbnail or execution. "Make it better" hands the remake plan to the script writer. */
export function OutlierFinder({ query, lang, disabled, onRemake }: { query: string; lang: Lang; disabled: boolean; onRemake: (topic: string) => void }) {
  const [kind, setKind] = useState<"short" | "long">("short");
  const [videos, setVideos] = useState<Outlier[] | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function find() {
    setBusy(true);
    setError("");
    try {
      const r = await api.outliers(query.split("\n")[0].trim(), lang, kind);
      setVideos(r.videos);
      setNote(r.note ?? (r.videos.length ? "" : `No video about this got 5x more views than its channel has subscribers in the last year. Try a broader topic.`));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant="ghost"
          loading={busy}
          disabled={disabled || !query.trim()}
          icon={<Search className="size-3.5" />}
          onClick={find}
          title="Searches YouTube for videos about your topic that got at least 5 views per channel subscriber, then Claude spots the ones with a strong idea but weak packaging."
        >
          Find outliers to remake
        </Button>
        <Segmented
          name="outlier-kind"
          value={kind}
          onChange={setKind}
          options={[
            { value: "short", label: "Shorts" },
            { value: "long", label: "Long videos" },
          ]}
        />
      </div>
      {busy && <p className="m-0 text-sm text-ink-soft">Searching YouTube, then Claude judges each title and thumbnail. This takes about a minute.</p>}
      {error && <p className="m-0 text-sm text-danger">{error}</p>}
      {note && <p className="m-0 text-sm text-ink-soft">{note}</p>}
      {videos && videos.length > 0 && (
        <ul className={`m-0 grid list-none gap-2 p-0 ${busy ? "opacity-50" : ""}`}>
          {videos.map((v) => (
            <li key={v.id} className={`grid gap-2 rounded-lg border p-2.5 sm:grid-cols-[160px_minmax(0,1fr)] ${v.target ? "border-cobalt/60" : "border-line"}`}>
              {v.thumbnail && <img src={v.thumbnail} alt="" className="aspect-video w-full rounded object-cover" loading="lazy" />}
              <div className="grid min-w-0 content-start gap-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="rounded bg-cobalt/10 px-1.5 py-0.5 text-xs font-bold text-cobalt tabular-nums">{v.ratio}x views/subs</span>
                  {v.target && <span className="rounded bg-ok/10 px-1.5 py-0.5 text-xs font-semibold text-ok">Remake target</span>}
                  {v.weak?.map((w) => (
                    <span key={w} className="rounded bg-danger/10 px-1.5 py-0.5 text-xs font-semibold text-danger">weak {w}</span>
                  ))}
                </div>
                <a href={v.url} target="_blank" rel="noreferrer" className="inline-flex items-start gap-1 text-base font-semibold text-ink no-underline hover:text-cobalt">
                  <span className="min-w-0">{v.title}</span>
                  <ExternalLink className="mt-1 size-3 shrink-0" />
                </a>
                <span className="text-sm text-ink-soft">
                  {v.channel} · {compact.format(v.views)} views · {compact.format(v.subs)} subs · {length(v.seconds)} · {v.published}
                </span>
                {v.verdict && <p className="m-0 text-sm leading-snug">{v.verdict}</p>}
                {v.target && v.better_title && (
                  <div className="grid gap-0.5 rounded bg-ink/[0.04] p-2 text-sm leading-snug">
                    <span lang={lang}><b>Better title:</b> {v.better_title}</span>
                    {v.better_thumbnail && <span lang={lang}><b>Thumbnail:</b> {v.better_thumbnail}</span>}
                    {v.hook && <span lang={lang}><b>Open with:</b> “{v.hook}”</span>}
                    {v.plan && <span><b>Do better:</b> {v.plan}</span>}
                  </div>
                )}
                {v.target && v.topic && kind === "short" && (
                  <Button
                    size="sm"
                    variant="secondary"
                    className="justify-self-start"
                    icon={<Wand2 className="size-3.5" />}
                    onClick={() => onRemake(`${v.topic}\nTitle: ${v.better_title}\nOpen with: "${v.hook}"`)}
                  >
                    Make the better version
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
