"use client";

import { Clapperboard } from "lucide-react";
import { useState } from "react";
import { api, type Options } from "@/lib/api";
import { ScriptVideoForm } from "./ScriptVideoForm";
import { ShortsForm } from "./ShortsForm";
import { Button, Field, FileInput, Message, Tabs } from "./ui";

/** A long 16:9 YouTube video from your script .md: the app builds the storyboard (voiceover, timing, footage) to check. */
function LongVideoForm({
  onStarted,
}: {
  onStarted: (jobId: string, title: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ text: string; error?: boolean }>({
    text: "",
  });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setMsg({ text: "Reading your script…" });
    try {
      const r = await api.longVideo(file);
      setMsg({ text: "" });
      onStarted(r.id, r.title);
    } catch (err) {
      setMsg({ text: (err as Error).message, error: true });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-5 card p-5 sm:p-6">
      <Field
        label="Script (.md)"
        hint="a table with Time | Visual | On-screen Text | Voiceover"
        htmlFor="long-file"
      >
        <FileInput
          id="long-file"
          accept=".md,.markdown,.txt,text/markdown,text/plain"
          file={file?.name ?? ""}
          disabled={busy}
          onReject={(text) => setMsg({ text, error: true })}
          onFile={(f) => {
            setFile(f);
            setMsg({ text: "" });
          }}
        />
      </Field>
      <div className="grid gap-1.5 text-base text-ink-soft">
        <p className="m-0">
          The title goes on the first <code># </code> line. Each table row is a
          scene; a line like <code>#10 GREEN HERON</code> in On-screen Text
          makes it a title card. Optional sections: <b>Thumbnail:</b>,{" "}
          <b>Title options</b>, <b>Description</b> (with a{" "}
          <code>Chapters:</code> line) and <b>Shorts</b>.
        </p>
        <p className="m-0">
          The app records the voiceover, times every scene and picks stock
          footage or photos for each one, then stops at the storyboard so you
          can swap anything wrong before it renders. To use your own clip for a
          scene, name it <code>scene-05.mp4</code> (or .jpg) in the
          script&apos;s media folder.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2 border-t border-line pt-5">
        <Button
          type="submit"
          variant="primary"
          loading={busy}
          disabled={!file}
          icon={<Clapperboard className="size-4" />}
        >
          {busy ? "Starting…" : "Build the storyboard"}
        </Button>
      </div>
      <Message {...msg} />
    </form>
  );
}

/** The one Create Video page: the Script to Video form, with the older ways in folded away below it. */
export function CreateForm({
  options,
  onLongVideo,
  onShorts,
  onDraft,
}: {
  options: Options | null;
  onLongVideo: (jobId: string, title: string) => void;
  onShorts: (jobId: string, title: string) => void;
  onDraft: (id: string, notice: string) => void;
}) {
  const [other, setOther] = useState<"shorts" | "long">("shorts");
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto grid max-w-[720px] gap-6 px-4 py-8 sm:px-8 sm:py-14">
        <div className="grid gap-2">
          <h1 className="page-title m-0">Create video</h1>
          <p className="page-intro m-0">
            Paste a finished script and choose a Short or a long video. Lyric videos live under Lyrics in the side rail.
          </p>
        </div>

        <ScriptVideoForm options={options} onDraft={onDraft} onLongVideo={onLongVideo} />

        <details className="grid gap-4">
          <summary className="cursor-pointer text-base font-semibold text-ink-soft">Other ways to start</summary>
          <div className="mt-4 grid gap-4">
            <Tabs
              label="Other ways to start"
              value={other}
              onChange={setOther}
              items={[
                { value: "shorts", label: "Shorts from a content plan (.xlsx)" },
                { value: "long", label: "Upload a script table (.md)" },
              ]}
            />
            {other === "shorts" ? <ShortsForm onStarted={onShorts} /> : <LongVideoForm onStarted={onLongVideo} />}
          </div>
        </details>
      </div>
    </div>
  );
}
