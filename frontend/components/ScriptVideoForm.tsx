"use client";

import { Clapperboard } from "lucide-react";
import { useState } from "react";
import { api, type Lang, type Options, type VisualStyle } from "@/lib/api";
import { USE_LABEL, useMonetizableOnly, type MusicUse } from "@/lib/musicLicence";
import { groupVoices, RATES, REGION, trackName, voiceName } from "./Storyboard";
import { Button, DropZone, Field, Message, Segmented } from "./ui";

const STYLES: { value: VisualStyle; label: string }[] = [
  { value: "cinematic_documentary", label: "Cinematic documentary" },
  { value: "cinematic_wildlife", label: "Wildlife documentary" },
  { value: "educational", label: "Educational" },
  { value: "storytelling", label: "Storytelling" },
];
const KHMER = /[ក-៿]/g;
const OFF_BY = 0.25; // the estimate this far from the target gets a note

/** Rough voiceover length (s), the same rule as the engine's director_plan.spoken_seconds. */
function spokenSeconds(text: string) {
  const km = text.match(KHMER)?.length ?? 0;
  return km ? km / 12 : text.split(/\s+/).filter(Boolean).length / 2.6;
}

const clock = (s: number) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;

/** "1:30", "90" or "1.5m" -> seconds; 0 when empty or unreadable. */
function parseLength(v: string) {
  const t = v.trim();
  if (!t) return 0;
  const mmss = t.match(/^(\d+):(\d{1,2})$/);
  if (mmss) return Number(mmss[1]) * 60 + Number(mmss[2]);
  const n = t.match(/^(\d+(?:\.\d+)?)\s*(m|min|s|sec)?$/i);
  if (!n) return 0;
  return Number(n[1]) * (n[2]?.toLowerCase().startsWith("m") ? 60 : 1);
}

/** The main way in: paste a finished script, pick Short or Long, and the app builds the project from it. */
export function ScriptVideoForm({
  options,
  onDraft,
  onLongVideo,
}: {
  options: Options | null;
  onDraft: (id: string, notice: string) => void;
  onLongVideo: (jobId: string, title: string) => void;
}) {
  const ai = !!options?.keys.ai; // Gemini connected (otherwise the basic script reader splits the scenes)
  const [text, setText] = useState("");
  const [format, setFormat] = useState<"short" | "long">("short");
  const [lang, setLang] = useState<Lang | "auto">("auto");
  const [style, setStyle] = useState<VisualStyle>("cinematic_documentary");
  const [voice, setVoice] = useState("");
  const [rate, setRate] = useState(""); // "" = the default speed (a Short's +5%, a long video's in Settings)
  const [music, setMusic] = useState("");
  const [target, setTarget] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ text: string; error?: boolean }>({ text: "" });
  const [safeOnly, setSafeOnly] = useMonetizableOnly();

  const voices = options ? (lang === "auto" ? (Object.keys(options.langs) as Lang[]) : [lang]).flatMap((l) => options.langs[l].voices) : [];
  const tracks = options?.music ?? [];
  const licenceOf = (m: string): MusicUse => options?.music_use?.[m] ?? "unknown";
  const listed = safeOnly ? tracks.filter((m) => licenceOf(m) === "ok") : tracks;
  const estimate = text.trim() ? spokenSeconds(text) : 0;
  const targetSec = parseLength(target);
  const off = targetSec && estimate ? (estimate - targetSec) / targetSec : 0;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (target.trim() && !targetSec) return setMsg({ text: "Write the target length as 0:45, 45 or 1.5m.", error: true });
    setBusy(true);
    setMsg({ text: ai ? "Gemini is reading your script…" : "Reading your script…" });
    try {
      const r = await api.scriptVideo({
        text, format, lang, visual_style: style, target_seconds: targetSec,
        voice: voices.includes(voice) ? voice : "", rate, music,
      });
      setMsg({ text: "" });
      if (r.format === "long") onLongVideo(r.id, r.title);
      else
        onDraft(
          r.id,
          (r.method === "basic"
            ? `Made ${r.scenes} scenes with the basic reader (Gemini wasn't available). Check the footage searches.`
            : `Made ${r.scenes} scenes. Your voiceover is kept word for word.`) +
            (r.planned_by === "ai" ? " The AI Director's shot plan is under Director." : r.director_note ? ` ${r.director_note}` : "") +
            (r.footage_job ? " Footage for every shot is being found and checked now." : "") +
            (r.voice_note ? ` ${r.voice_note}` : ""),
        );
    } catch (err) {
      setMsg({ text: (err as Error).message, error: true });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-5 card p-5 sm:p-6">
      <Field label="Finished script" htmlFor="script-video-text">
        <DropZone
          accept=".txt,.md,.markdown,text/plain,text/markdown"
          label="Drop to paste its text"
          onFiles={async (f) => setText((await f[0].text()).replace(/\r\n/g, "\n"))}
          onReject={(t) => setMsg({ text: t, error: true })}
          className="grid"
        >
          <textarea
            id="script-video-text"
            rows={14}
            required
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste the whole script. No need to split it into scenes."
            aria-describedby="script-video-estimate"
            className="field-input resize-y font-mono text-base leading-relaxed"
          />
        </DropZone>
        <p id="script-video-estimate" role="status" className={`m-0 text-sm ${Math.abs(off) > OFF_BY ? "text-warn" : "text-ink-soft"}`}>
          {estimate > 0 && `About ${clock(estimate)} of voiceover.`}
          {estimate > 0 && targetSec > 0 && Math.abs(off) > OFF_BY &&
            ` Your target is ${clock(targetSec)}: ${off > 0 ? "cut" : "add"} about ${Math.round(Math.abs(estimate - targetSec) * 2.6)} words to get close.`}
        </p>
      </Field>

      <div className="grid items-end gap-5 sm:grid-cols-2">
        <div className="grid gap-1.5">
          <span className="field-label">Format</span>
          <Segmented
            name="script-video-format"
            value={format}
            onChange={setFormat}
            options={[
              { value: "short", label: "YouTube Short 9:16" },
              { value: "long", label: "Long video 16:9" },
            ]}
          />
        </div>
        <div className="grid gap-1.5">
          <span className="field-label">Language</span>
          <Segmented
            name="script-video-lang"
            value={lang}
            onChange={setLang}
            options={[
              { value: "auto", label: "Auto" },
              { value: "en", label: "English" },
              { value: "km", label: "ខ្មែរ", lang: "km" },
            ]}
          />
        </div>
      </div>

      <div className="grid items-start gap-5 sm:grid-cols-2">
          <Field label="Narration voice" htmlFor="script-video-voice">
            <select id="script-video-voice" className="field-input" value={voices.includes(voice) ? voice : ""} onChange={(e) => setVoice(e.target.value)}>
              <option value="">{format === "short" ? "Language default" : "As in Settings → Script Video"}</option>
              {groupVoices(voices).map(([region, list]) => (
                <optgroup key={region} label={REGION[region] ?? region}>
                  {list.map((v) => (
                    <option key={v} value={v}>
                      {voiceName(v)}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </Field>
          <div className="grid gap-1.5">
            <label className="field-label" htmlFor="script-video-music">
              Music
            </label>
            <select id="script-video-music" className="field-input" value={music} onChange={(e) => setMusic(e.target.value)}>
              {format === "long" ? <option value="">Your tracks (Settings)</option> : tracks.length > 0 && <option value="">Matches the mood</option>}
              <option value="none">No music</option>
              {music && music !== "none" && !listed.includes(music) && <option value={music}>{trackName(music)}</option>}
              {listed.map((m) => (
                <option key={m} value={m}>
                  {trackName(m)}
                  {licenceOf(m) !== "ok" ? ` (${USE_LABEL[licenceOf(m) as Exclude<MusicUse, "ok">]})` : ""}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-1.5 text-xs text-ink-soft" title="Hide tracks whose licence doesn't allow monetized videos (non-commercial or no-derivatives)">
              <input type="checkbox" className="size-3.5" checked={safeOnly} onChange={(e) => setSafeOnly(e.target.checked)} />
              Monetizable only{safeOnly && tracks.length > listed.length ? ` (${tracks.length - listed.length} hidden)` : ""}
            </label>
          </div>
        </div>

      <details className="grid gap-5">
        <summary className="cursor-pointer text-base font-semibold text-ink-soft">Advanced options</summary>
        <div className="mt-4 grid items-start gap-5 sm:grid-cols-2">
          <Field label="Visual style" htmlFor="script-video-style">
            <select id="script-video-style" className="field-input" value={style} onChange={(e) => setStyle(e.target.value as VisualStyle)}>
              {STYLES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Target length" htmlFor="script-video-target" hint="Optional, like 0:45. Your script isn't cut: the AI Director paces the shots for it.">
            <input
              id="script-video-target"
              className="field-input"
              inputMode="decimal"
              placeholder="0:45"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            />
          </Field>
          <div className="grid gap-1.5">
            <span className="field-label">Speed</span>
            <Segmented name="script-video-rate" value={rate || (format === "short" ? "+5%" : "+0%")} onChange={setRate} options={RATES} />
          </div>
        </div>
      </details>

      <p className="m-0 text-base text-ink-soft">
        Your voiceover is kept word for word. A Short opens as a draft you can edit. A long video records the
        voiceover, times every scene and picks footage, then stops at the storyboard so you can check it before it
        renders. A script already written as a Time | Visual | On-screen Text | Voiceover table is used as it is.
      </p>

      <div className="flex flex-wrap items-center gap-2 border-t border-line pt-5">
        <Button type="submit" variant="primary" loading={busy} disabled={!text.trim()} icon={<Clapperboard className="size-4" />}>
          {busy ? "Creating…" : "Create video"}
        </Button>
      </div>
      <Message {...msg} />
    </form>
  );
}
