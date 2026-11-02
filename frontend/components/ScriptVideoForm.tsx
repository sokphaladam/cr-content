"use client";

import { Clapperboard } from "lucide-react";
import { useState } from "react";
import { api, type Lang, type VisualStyle } from "@/lib/api";
import { Button, DropZone, Field, Message, Segmented } from "./ui";

const STYLES: { value: VisualStyle; label: string }[] = [
  { value: "cinematic_documentary", label: "Cinematic documentary" },
  { value: "cinematic_wildlife", label: "Wildlife documentary" },
  { value: "educational", label: "Educational" },
  { value: "storytelling", label: "Storytelling" },
];

/** The main way in: paste a finished script, pick Short or Long, and the app builds the project from it. */
export function ScriptVideoForm({
  ai,
  onDraft,
  onLongVideo,
}: {
  ai: boolean; // Gemini connected (otherwise the basic script reader splits the scenes)
  onDraft: (id: string, notice: string) => void;
  onLongVideo: (jobId: string, title: string) => void;
}) {
  const [text, setText] = useState("");
  const [format, setFormat] = useState<"short" | "long">("short");
  const [lang, setLang] = useState<Lang | "auto">("auto");
  const [style, setStyle] = useState<VisualStyle>("cinematic_documentary");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ text: string; error?: boolean }>({ text: "" });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg({ text: ai ? "Gemini is reading your script…" : "Reading your script…" });
    try {
      const r = await api.scriptVideo({ text, format, lang, visual_style: style });
      setMsg({ text: "" });
      if (r.format === "long") onLongVideo(r.id, r.title);
      else
        onDraft(
          r.id,
          r.method === "basic"
            ? `Made ${r.scenes} scenes with the basic reader (Gemini wasn't available). Check the footage searches.`
            : `Made ${r.scenes} scenes. Your voiceover is kept word for word.`,
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
            className="field-input resize-y font-mono text-base leading-relaxed"
          />
        </DropZone>
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

      <Field label="Visual style" htmlFor="script-video-style">
        <select
          id="script-video-style"
          className="field-input"
          value={style}
          onChange={(e) => setStyle(e.target.value as VisualStyle)}
        >
          {STYLES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </Field>

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
