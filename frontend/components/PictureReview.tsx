"use client";

import { ChevronLeft, ChevronRight, Dices, ImageIcon, Paintbrush, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { fileUrl, type Aspect } from "@/lib/api";
import { Button, IconButton, Spinner } from "./ui";

export interface ReviewItem {
  label: string; // "Scene 3" / "Chorus · 0:45"
  text: string; // what is said or sung over it
  prompt: string;
  media: string | null; // the drawn picture (project-relative), null = not drawn yet
}

/**
 * Pictures one at a time: each is drawn when you get to it (if it isn't yet), then you keep it and go on, ask for
 * another take, or rewrite its prompt and draw again. Drawing happens on this computer, so it costs nothing.
 */
export function PictureReview({
  items,
  start = 0,
  aspect,
  blocker,
  onDraw,
  onPrompt,
  onClose,
}: {
  items: ReviewItem[];
  start?: number;
  aspect: Aspect;
  blocker: string; // why drawing can't happen ("" = ready)
  onDraw: (index: number, newTake: boolean) => Promise<boolean>;
  onPrompt: (index: number, prompt: string) => void;
  onClose: () => void;
}) {
  const [index, setIndex] = useState(Math.min(start, Math.max(items.length - 1, 0)));
  const [drawing, setDrawing] = useState(false);
  const tried = useRef(new Set<number>()); // drawn automatically once; after that only on request
  const item = items[index];

  async function draw(newTake: boolean) {
    setDrawing(true);
    await onDraw(index, newTake);
    setDrawing(false);
  }

  // arriving at a picture that isn't drawn yet draws it
  useEffect(() => {
    if (!item || item.media || blocker || !item.prompt.trim() || tried.current.has(index)) return;
    tried.current.add(index);
    void draw(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only when moving to another picture
  }, [index]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && !drawing && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawing, onClose]);

  if (!item) return null;
  const drawn = items.filter((i) => i.media).length;
  const last = index === items.length - 1;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-3" role="dialog" aria-modal="true" aria-label="Draw pictures one by one">
      <div className="absolute inset-0 bg-ink/50" onClick={() => !drawing && onClose()} />
      <div className="relative flex max-h-[94vh] w-[min(560px,96vw)] flex-col overflow-hidden rounded-xl bg-paper shadow-2xl">
        <div className="flex h-12 shrink-0 items-center justify-between gap-2 border-b border-line bg-panel px-3.5">
          <span className="font-display text-lg font-bold tabular-nums">
            Picture {index + 1} of {items.length} <span className="text-sm font-normal text-ink-soft">· {drawn} drawn</span>
          </span>
          <IconButton label="Close" onClick={onClose} disabled={drawing}>
            <X className="size-5" />
          </IconButton>
        </div>
        <div className="grid min-h-0 gap-2.5 overflow-y-auto p-3.5">
          <div
            className={`relative mx-auto grid place-items-center overflow-hidden rounded-lg bg-ink/[0.06] ${
              aspect === "16:9" ? "aspect-video w-full" : "aspect-[9/16] h-[min(52vh,560px)]"
            }`}
          >
            {item.media && (
              // eslint-disable-next-line @next/next/no-img-element -- a local file from the engine
              <img src={fileUrl(item.media)} alt={item.prompt} className={`size-full object-cover transition-opacity ${drawing ? "opacity-40" : ""}`} />
            )}
            {!item.media && !drawing && <ImageIcon className="size-8 text-ink-soft/60" aria-hidden />}
            {drawing && (
              <span className="absolute inset-0 grid place-content-center justify-items-center gap-1.5 text-sm font-semibold text-ink">
                <Spinner className="size-6" />
                Drawing… about 40 seconds
              </span>
            )}
          </div>
          <div className="grid gap-0.5">
            <span className="text-base font-semibold">{item.label}</span>
            {item.text && <span className="line-clamp-3 text-sm text-ink-soft italic">“{item.text}”</span>}
          </div>
          <label className="grid gap-1">
            <span className="field-label">What the picture shows</span>
            <textarea
              rows={3}
              value={item.prompt}
              disabled={drawing}
              onChange={(e) => onPrompt(index, e.target.value)}
              className="field-input min-h-[68px] resize-y text-sm leading-snug"
            />
          </label>
          {blocker && <p className="m-0 text-sm text-danger">{blocker}</p>}
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-1.5 border-t border-line bg-panel px-3.5 py-2.5">
          <Button size="sm" variant="ghost" icon={<ChevronLeft className="size-4" />} disabled={drawing || index === 0} onClick={() => setIndex((i) => i - 1)}>
            Back
          </Button>
          <div className="flex-1" />
          <Button
            size="sm"
            icon={item.media ? <Dices className="size-3.5" /> : <Paintbrush className="size-3.5" />}
            disabled={drawing || !!blocker || !item.prompt.trim()}
            onClick={() => draw(!!item.media)}
            title={item.media ? "The same prompt, a different picture" : "Draw this picture"}
          >
            {item.media ? "Another take" : "Draw"}
          </Button>
          <Button
            size="sm"
            variant="primary"
            disabled={drawing}
            onClick={() => (last ? onClose() : setIndex((i) => i + 1))}
          >
            {last ? "Done" : item.media ? "Keep & next" : "Skip"}
            {!last && <ChevronRight className="size-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
