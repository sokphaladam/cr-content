"use client";

import { Check, Copy, Gauge } from "lucide-react";
import { useState } from "react";
import { api, type PackagingReview as Review, type VideoDetail } from "@/lib/api";
import { Button, useToast } from "./ui";

function Score({ label, score, verdict }: { label: string; score: number; verdict: string }) {
  const tone = score >= 8 ? "text-ok" : score >= 5 ? "text-ink" : "text-danger";
  return (
    <div className="grid grid-cols-[auto_1fr] items-baseline gap-x-2.5">
      <span className={`font-display text-xl font-bold tabular-nums ${tone}`} aria-label={`${label}: ${score} out of 10`}>
        {score}
        <span className="text-sm font-semibold text-ink-soft">/10</span>
      </span>
      <span className="text-2xs font-semibold tracking-wide text-ink-soft uppercase">{label}</span>
      <span />
      <span className="text-sm leading-snug text-ink-soft">{verdict}</span>
    </div>
  );
}

/** "Review packaging": the title, thumbnail and opening judged together the way a viewer meets them, with stronger
 * versions to use. A new title replaces the post's title line right away (`onPost`). */
export function PackagingReview({ detail, onPost }: { detail: VideoDetail; onPost: (post: string) => void }) {
  const toast = useToast();
  const [review, setReview] = useState<Review | null>(null);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState("");

  async function run() {
    setBusy(true);
    try {
      setReview(await api.reviewPackaging(detail.name));
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function applyTitle(title: string) {
    setSaving(title);
    try {
      onPost((await api.setPostTitle(detail.name, title)).post);
      setReview((r) => (r ? { ...r, current_title: title } : r));
      toast("Title updated", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setSaving("");
    }
  }

  async function copy(text: string, what: string) {
    await navigator.clipboard.writeText(text);
    toast(`${what} copied`, "success");
  }

  return (
    <div className="grid gap-2 border-t border-line p-3.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm text-ink-soft">Title, thumbnail and first line, judged together.</span>
        <Button size="sm" variant={review ? "ghost" : "secondary"} icon={<Gauge className="size-3.5" />} loading={busy} onClick={run}>
          {review ? "Review again" : "Review packaging"}
        </Button>
      </div>
      {busy && <p className="m-0 text-sm text-ink-soft">Gemini is looking at the thumbnail, title and opening…</p>}
      {review && (
        <div className={`grid gap-3 ${busy ? "opacity-50" : ""}`}>
          <Score label="Title" {...review.title} />
          <Score label="Thumbnail" {...review.thumbnail} />
          <Score label="Opening" {...review.opening} />
          {review.fluff.length > 0 && (
            <p className="m-0 rounded-lg bg-danger/10 px-2.5 py-2 text-sm leading-snug text-danger">
              The opening has {review.fluff.join(" and ")}. Viewers leave in the first seconds: start with the payoff.
            </p>
          )}
          {review.fixes.length > 0 && (
            <div className="grid gap-1">
              <span className="text-2xs font-semibold tracking-wide text-ink-soft uppercase">Fix first</span>
              <ol className="m-0 grid gap-0.5 pl-4 text-sm leading-snug">
                {review.fixes.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ol>
            </div>
          )}
          <div className="grid gap-1.5">
            <span className="text-2xs font-semibold tracking-wide text-ink-soft uppercase">Stronger titles</span>
            {review.titles.map((t) => {
              const current = t === review.current_title;
              return (
                <div key={t} className={`flex items-center gap-1 rounded-lg border p-2 ${current ? "border-cobalt" : "border-line"}`}>
                  <p lang={detail.lang} className="m-0 flex-1 text-base leading-snug font-semibold">{t}</p>
                  <Button size="sm" variant="ghost" icon={<Check className="size-3.5" />} loading={saving === t} disabled={!!saving || current} onClick={() => applyTitle(t)}>
                    {current ? "In use" : "Use"}
                  </Button>
                </div>
              );
            })}
          </div>
          {review.thumbnail_texts.length > 0 && (
            <div className="grid gap-1.5">
              <span className="text-2xs font-semibold tracking-wide text-ink-soft uppercase">Thumbnail words</span>
              {review.thumbnail_texts.map((t) => (
                <div key={t.text} className="flex items-center gap-1 rounded-lg border border-line p-2">
                  <p lang={detail.lang} className="m-0 flex-1 text-base leading-snug font-bold uppercase">{t.text}</p>
                  <Button size="sm" variant="ghost" icon={<Copy className="size-3.5" />} onClick={() => copy(t.text, "Thumbnail words")}>
                    Copy
                  </Button>
                </div>
              ))}
              <span className="text-sm text-ink-soft">Paste them as the headline in the Thumbnail card above.</span>
            </div>
          )}
          {review.opening_line && (
            <div className="grid gap-1.5">
              <span className="text-2xs font-semibold tracking-wide text-ink-soft uppercase">Sharper first line</span>
              <div className="flex items-center gap-1 rounded-lg border border-line p-2">
                <p lang={detail.lang} className="m-0 flex-1 text-base leading-snug">“{review.opening_line}”</p>
                <Button size="sm" variant="ghost" icon={<Copy className="size-3.5" />} onClick={() => copy(review.opening_line, "First line")}>
                  Copy
                </Button>
              </div>
              <span className="text-sm text-ink-soft">Put it in scene 1 of the draft and render again.</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
