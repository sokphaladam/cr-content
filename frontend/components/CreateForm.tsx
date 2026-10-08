"use client";

import { ClipboardPaste, Music, PenLine, Sparkles } from "lucide-react";
import { useState } from "react";
import { api, type Lang, type Options, type SongScript, type VideoScript } from "@/lib/api";
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

type Mode = "topic" | "paste" | "song";

export function CreateForm({
  options,
  onScript,
  onSong,
}: {
  options: Options | null;
  onScript: (script: VideoScript, lang: Lang, topic: string, notice?: string) => void;
  onSong: (song: SongScript, lang: Lang, topic: string) => void;
}) {
  const [mode, setMode] = useState<Mode>("topic");
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
          <h1 className="m-0 font-display text-[clamp(30px,3.6vw,44px)] leading-[1.05] font-extrabold tracking-[-0.025em]">Make a new video</h1>
          <p className="m-0 max-w-[56ch] text-[15px] text-ink-soft">
            Start from an idea and let Claude write the script, or paste a script you already have. Either way it becomes a draft you can edit.
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
            { value: "song", label: "Make a song" },
          ]}
        />

        {mode === "song" && (
          <form onSubmit={writeSong} className="grid gap-5 rounded-xl border border-line bg-panel p-5 sm:p-6">
            <Field label="What the song is about" htmlFor="song-topic">
              <textarea
                id="song-topic"
                rows={2}
                required
                lang={lang}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Summer love on the Phnom Penh riverside"
                className="field-input resize-y py-3 text-lg leading-snug font-medium"
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
            <p className="m-0 text-[13px] text-ink-soft">
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
          <form onSubmit={write} className="grid gap-5 rounded-xl border border-line bg-panel p-5 sm:p-6">
            <Field label="Topic" htmlFor="topic">
              <textarea
                id="topic"
                rows={2}
                required
                lang={lang}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder={PLACEHOLDER[lang]}
                className="field-input resize-y py-3 text-lg leading-snug font-medium"
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

        {mode === "paste" && (
          <form onSubmit={importPasted} className="grid gap-4 rounded-xl border border-line bg-panel p-5 sm:p-6">
            <Field label="Script" htmlFor="pasted">
              <textarea
                id="pasted"
                rows={14}
                required
                value={pasted}
                onChange={(e) => setPasted(e.target.value)}
                placeholder={PASTE_EXAMPLE}
                className="field-input resize-y font-mono text-[13px] leading-relaxed"
              />
            </Field>
            <p className="m-0 text-[13px] text-ink-soft">
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
