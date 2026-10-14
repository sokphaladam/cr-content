"use client";

import { ClipboardPaste, Music, PenLine, Sparkles, Upload } from "lucide-react";
import { useState } from "react";
import { api, type Aspect, type Lang, type Options, type SongScript, type VideoScript } from "@/lib/api";
import { ExcelPlanForm } from "./ExcelPlanForm";
import { Button, Field, Message, Segmented, Tabs } from "./ui";

const PLACEHOLDER: Record<Lang, string> = {
  en: "3 weird facts about octopuses",
  km: "ប្រវត្តិប្រាសាទអង្គរវត្ត",
};

const PASTE_EXAMPLE = [
  "Title: 3 Octopus Facts That Sound Fake",
  "",
  "[0–3s] Hook",
  "Visual: Close-up of an octopus eye",
  "On-screen text: This animal is basically an alien",
  "Voiceover: This animal is so weird, scientists still can't explain it.",
  "",
  "[3–10s] Fact 1",
  "…",
].join("\n");

type Mode = "topic" | "paste" | "excel" | "song";

const LYRICS_EXAMPLE = ["[Verse 1]", "I walked along the river in the rain", "The city lights were calling out your name", "", "[Chorus]", "Stay with me tonight", "…"].join("\n");

/** Your own finished song: audio + lyrics in, then lyric timing runs as a job. */
function OwnSongForm({ onImported }: { onImported: (jobId: string, title: string) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [lyrics, setLyrics] = useState("");
  const [lang, setLang] = useState<Lang>("en");
  const [aspect, setAspect] = useState<Aspect>("16:9");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ text: string; error?: boolean }>({ text: "" });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setMsg({ text: "Uploading your song…" });
    try {
      const name = title.trim() || file.name.replace(/\.[^.]+$/, "");
      const { id } = await api.importSong({ file, title: name, lyrics, lang, aspect });
      setMsg({ text: "" });
      onImported(id, name);
    } catch (err) {
      setMsg({ text: (err as Error).message, error: true });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-5 card p-5 sm:p-6">
      <Field label="Song file" hint="mp3, wav, m4a, flac" htmlFor="own-file">
        <input
          id="own-file"
          type="file"
          required
          accept=".mp3,.wav,.m4a,.aac,.flac,.ogg,.opus,audio/*"
          onChange={(e) => {
            const f = e.target.files?.[0] ?? null;
            setFile(f);
            if (f && !title) setTitle(f.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " "));
          }}
          className="field-input h-auto py-2 file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-ink/[0.06] file:px-3 file:py-1.5 file:font-semibold"
        />
      </Field>

      <div className="grid items-end gap-5 sm:grid-cols-[minmax(0,1fr)_auto_auto]">
        <Field label="Title" htmlFor="own-title">
          <input id="own-title" lang={lang} className="field-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Song title" />
        </Field>
        <div className="grid gap-1.5">
          <span className="field-label">Language</span>
          <Segmented
            name="own-lang"
            value={lang}
            onChange={setLang}
            options={[
              { value: "en", label: "English" },
              { value: "km", label: "ខ្មែរ", lang: "km" },
            ]}
          />
        </div>
        <div className="grid gap-1.5">
          <span className="field-label">Video shape</span>
          <Segmented
            name="own-aspect"
            value={aspect}
            onChange={setAspect}
            options={[
              { value: "16:9", label: "16:9 YouTube" },
              { value: "9:16", label: "9:16 vertical" },
            ]}
          />
        </div>
      </div>

      <Field label="Lyrics" hint="one sung line per row; [Verse] / [Chorus] headings optional" htmlFor="own-lyrics">
        <textarea
          id="own-lyrics"
          rows={12}
          required
          lang={lang}
          value={lyrics}
          onChange={(e) => setLyrics(e.target.value)}
          placeholder={LYRICS_EXAMPLE}
          className="field-input resize-y py-2.5 leading-relaxed"
        />
      </Field>
      <p className="m-0 text-base text-ink-soft">
        The app listens to your song and lines each lyric up with the singing, then shows you the timing to check before it makes the video. Footage is
        picked for each part of the song and cut on the beat.
      </p>

      <div className="flex flex-wrap items-center gap-2 border-t border-line pt-5">
        <Button type="submit" variant="primary" loading={busy} disabled={!file || !lyrics.trim()} icon={<Upload className="size-4" />}>
          {busy ? "Uploading…" : "Upload and sync lyrics"}
        </Button>
      </div>
      <Message {...msg} />
    </form>
  );
}

export function CreateForm({
  options,
  onScript,
  onSong,
  onImportSong,
  onExcelDrafts,
  onExcelRender,
}: {
  options: Options | null;
  onScript: (script: VideoScript, lang: Lang, topic: string, notice?: string) => void;
  onSong: (song: SongScript, lang: Lang, topic: string) => void;
  onImportSong: (jobId: string, title: string) => void;
  onExcelDrafts: (drafts: { ep: number; id: string; title: string }[]) => void;
  onExcelRender: (jobId: string, title: string) => void;
}) {
  const [mode, setMode] = useState<Mode>("topic");
  const [songSource, setSongSource] = useState<"own" | "ai">("own");
  const [topic, setTopic] = useState("");
  const [lang, setLang] = useState<Lang>("en");
  const [seconds, setSeconds] = useState(45);
  const [scenes, setScenes] = useState(6);
  const [style, setStyle] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ text: string; error?: boolean }>({ text: "" });
  const [pasted, setPasted] = useState("");
  const [importing, setImporting] = useState(false);
  const [importMsg, setImportMsg] = useState<{ text: string; error?: boolean }>({ text: "" });

  const [vocal, setVocal] = useState("");

  const claudeMissing = options !== null && !options.keys.anthropic;

  async function writeSong(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg({ text: "Claude is writing your song. This usually takes 15–40 seconds." });
    try {
      const song = await api.writeSong({ topic: topic.trim(), lang, seconds, style, vocal });
      onSong(song, lang, topic.trim());
    } catch (err) {
      setMsg({ text: (err as Error).message, error: true });
    } finally {
      setBusy(false);
    }
  }

  async function write(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg({ text: "Claude is writing your script. This usually takes 15–40 seconds." });
    try {
      const script = await api.writeScript({ topic: topic.trim(), lang, scenes, seconds, style });
      onScript(script, lang, topic.trim(), "Script written and saved as a draft. Check each scene, then render.");
    } catch (err) {
      setMsg({ text: (err as Error).message, error: true });
    } finally {
      setBusy(false);
    }
  }

  async function importPasted(e: React.FormEvent) {
    e.preventDefault();
    setImporting(true);
    setImportMsg({ text: options?.keys.anthropic ? "Claude is reading your script…" : "Reading your script…" });
    try {
      const res = await api.importScript(pasted);
      const n = res.script.scenes.length;
      onScript(
        res.script,
        res.lang,
        res.script.title,
        res.method === "claude"
          ? `Imported ${n} scenes. Voiceover kept word for word; footage searches come from your visual notes.`
          : `Imported ${n} scenes with the basic reader (Claude wasn't available). Check the footage searches.`,
      );
    } catch (err) {
      setImportMsg({ text: (err as Error).message, error: true });
    } finally {
      setImporting(false);
    }
  }

  function blank() {
    onScript(
      {
        title: topic.trim(),
        scenes: Array.from({ length: scenes }, () => ({ narration: "", visual_query: "", on_screen_text: "", media: "" })),
        caption: "",
        hashtags: [],
      },
      lang,
      topic.trim(),
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto grid max-w-[720px] gap-6 px-4 py-8 sm:px-8 sm:py-14">
        <div className="grid gap-2">
          <h1 className="page-title m-0">Make a new video</h1>
          <p className="page-intro m-0">
            Start from an idea and let Claude write the script, paste a script you already have, or upload a content plan in Excel. Every script becomes a draft you can edit.
          </p>
        </div>

        <Tabs
          label="How to start"
          value={mode}
          onChange={(m) => {
            setMode(m);
            setMsg({ text: "" });
          }}
          items={[
            { value: "topic", label: "Start from a topic" },
            { value: "paste", label: "Paste a script" },
            { value: "excel", label: "Excel plan" },
            { value: "song", label: "Music video" },
          ]}
        />

        {mode === "song" && (
          <Segmented
            name="song-source"
            value={songSource}
            onChange={setSongSource}
            options={[
              { value: "own", label: "Use my song (mp3 + lyrics)" },
              { value: "ai", label: "Compose with AI" },
            ]}
          />
        )}

        {mode === "song" && songSource === "own" && <OwnSongForm onImported={onImportSong} />}

        {mode === "song" && songSource === "ai" && (
          <form onSubmit={writeSong} className="grid gap-5 card p-5 sm:p-6">
            <Field label="What the song is about" htmlFor="song-topic">
              <textarea
                id="song-topic"
                rows={2}
                required
                lang={lang}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Summer love on the Phnom Penh riverside"
                className="field-input resize-y py-3 text-xl leading-snug font-medium"
              />
            </Field>

            <div className="grid items-end gap-5 sm:grid-cols-[auto_1fr]">
              <div className="grid gap-1.5">
                <span className="field-label">Language</span>
                <Segmented
                  name="song-lang"
                  value={lang}
                  onChange={setLang}
                  options={[
                    { value: "en", label: "English" },
                    { value: "km", label: "ខ្មែរ", lang: "km" },
                  ]}
                />
              </div>
              <Field label={<>Length <output className="ml-1 font-semibold text-ink">{seconds} s</output></>} htmlFor="song-seconds">
                <input id="song-seconds" type="range" min={15} max={120} step={5} value={seconds} onChange={(e) => setSeconds(+e.target.value)} className="h-10 w-full accent-cobalt" />
              </Field>
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Genre and sound" hint="optional" htmlFor="song-style">
                <input id="song-style" className="field-input" value={style} onChange={(e) => setStyle(e.target.value)} placeholder="Dreamy synth-pop, 80s drums" />
              </Field>
              <Field label="Singer voice" hint="optional" htmlFor="song-vocal">
                <input id="song-vocal" className="field-input" value={vocal} onChange={(e) => setVocal(e.target.value)} placeholder="Breathy female pop vocal" />
              </Field>
            </div>
            <p className="m-0 text-base text-ink-soft">
              Describe a sound, not a real singer. Names of real artists get turned into a description of their style, because ElevenLabs won&apos;t imitate real voices.
            </p>

            <div className="flex flex-wrap items-center gap-2 border-t border-line pt-5">
              <Button type="submit" variant="primary" loading={busy} disabled={claudeMissing} icon={<Music className="size-4" />}>
                {busy ? "Writing…" : "Write lyrics with Claude"}
              </Button>
            </div>
            <Message
              text={msg.text || (claudeMissing ? "Claude isn't connected, so it can't write lyrics yet. Add your key to .env and restart the engine." : "")}
              error={msg.error}
            />
          </form>
        )}

        {mode === "topic" && (
          <form onSubmit={write} className="grid gap-5 card p-5 sm:p-6">
            <Field label="Topic" htmlFor="topic">
              <textarea
                id="topic"
                rows={2}
                required
                lang={lang}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder={PLACEHOLDER[lang]}
                className="field-input resize-y py-3 text-xl leading-snug font-medium"
              />
            </Field>

            <div className="grid items-end gap-5 sm:grid-cols-[auto_1fr_1fr]">
              <div className="grid gap-1.5">
                <span className="field-label">Language</span>
                <Segmented
                  name="lang"
                  value={lang}
                  onChange={setLang}
                  options={[
                    { value: "en", label: "English" },
                    { value: "km", label: "ខ្មែរ", lang: "km" },
                  ]}
                />
              </div>
              <Field label={<>Length <output className="ml-1 font-semibold text-ink">{seconds} s</output></>} htmlFor="seconds">
                <input id="seconds" type="range" min={15} max={90} step={5} value={seconds} onChange={(e) => setSeconds(+e.target.value)} className="h-10 w-full accent-cobalt" />
              </Field>
              <Field label={<>Scenes <output className="ml-1 font-semibold text-ink">{scenes}</output></>} htmlFor="scenes">
                <input id="scenes" type="range" min={3} max={10} value={scenes} onChange={(e) => setScenes(+e.target.value)} className="h-10 w-full accent-cobalt" />
              </Field>
            </div>

            <Field label="Tone or audience" hint="optional" htmlFor="style">
              <input id="style" className="field-input" value={style} onChange={(e) => setStyle(e.target.value)} placeholder="Funny, for teenagers. Mention a local example." />
            </Field>

            <div className="flex flex-wrap items-center gap-2 border-t border-line pt-5">
              <Button type="submit" variant="primary" loading={busy} disabled={claudeMissing} icon={<Sparkles className="size-4" />}>
                {busy ? "Writing…" : "Write script with Claude"}
              </Button>
              <Button variant="ghost" onClick={blank} icon={<PenLine className="size-4" />}>
                Write it myself
              </Button>
            </div>
            <Message
              text={
                msg.text ||
                (claudeMissing ? "Claude isn't connected, so it can't write scripts yet. Use “Write it myself”, or add your key to .env and restart the engine." : "")
              }
              error={msg.error}
            />
          </form>
        )}

        {mode === "excel" && <ExcelPlanForm claude={!!options?.keys.anthropic} onDrafts={onExcelDrafts} onRender={onExcelRender} />}

        {mode === "paste" && (
          <form onSubmit={importPasted} className="grid gap-4 card p-5 sm:p-6">
            <Field label="Script" htmlFor="pasted">
              <textarea
                id="pasted"
                rows={14}
                required
                value={pasted}
                onChange={(e) => setPasted(e.target.value)}
                placeholder={PASTE_EXAMPLE}
                className="field-input resize-y font-mono text-base leading-relaxed"
              />
            </Field>
            <p className="m-0 text-base text-ink-soft">
              English or ខ្មែរ, any layout. Voiceover is kept word for word, visual notes become footage searches, and extra notes like production tips are ignored. Emojis are removed
              from on-screen text.
            </p>
            <div className="flex flex-wrap items-center gap-2 border-t border-line pt-5">
              <Button type="submit" variant="primary" loading={importing} icon={<ClipboardPaste className="size-4" />}>
                {importing ? "Importing…" : "Import script"}
              </Button>
            </div>
            <Message {...importMsg} />
          </form>
        )}
      </div>
    </div>
  );
}
