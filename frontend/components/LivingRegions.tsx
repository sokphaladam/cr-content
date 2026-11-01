"use client";

import { Eye, Trash2 } from "lucide-react";
import { useRef, useState } from "react";
import type { LivingRegion } from "@/lib/api";
import { Button } from "./ui";

const ANCHORS = ["top", "bottom", "left", "right"] as const;
const COLORS: Record<string, string> = {
  sway: "#22c55e", breathe: "#3b82f6", nod: "#14b8a6", write: "#ec4899", blink: "#eab308", flicker: "#f97316",
  rain: "#38bdf8", leaves: "#ef4444", steam: "#e5e7eb", protect: "#a855f7",
};

/**
 * The living loop's editor: drag boxes over the cover picture to mark what moves, pick how each one moves and how
 * much, and preview the loop (made on this computer in a few seconds). Boxes are kept in 0..1 of the picture.
 */
export function LivingRegions({ picture, regions, kinds, onChange, onPreview, preview, disabled }: {
  picture: string; // the cover picture's url
  regions: LivingRegion[];
  kinds: Record<string, string>; // kind -> label
  onChange: (next: LivingRegion[]) => void;
  onPreview: () => void;
  preview: string; // the preview clip's url ("" = none yet)
  disabled?: boolean;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [drag, setDrag] = useState<{ x: number; y: number; x2: number; y2: number } | null>(null);
  const [picked, setPicked] = useState<number | null>(null);
  const at = (e: React.PointerEvent) => {
    const r = box.current!.getBoundingClientRect();
    return { x: Math.min(Math.max((e.clientX - r.left) / r.width, 0), 1), y: Math.min(Math.max((e.clientY - r.top) / r.height, 0), 1) };
  };
  const set = (i: number, patch: Partial<LivingRegion>) => onChange(regions.map((r, k) => (k === i ? { ...r, ...patch } : r)));

  return (
    <div className="grid gap-2">
      <p className="m-0 text-sm text-ink-soft">
        Drag a box over each part that should move, then pick how it moves. Only those parts change; the rest stays exactly as drawn. Put
        <b> Protect</b> over a face next to moving hair. Rain, leaves and steam fall only inside their box (a window, a mug).
      </p>
      <div ref={box} className="relative aspect-video w-full touch-none overflow-hidden rounded-lg bg-black select-none"
        onPointerDown={(e) => {
          if (disabled) return;
          e.currentTarget.setPointerCapture(e.pointerId);
          const p = at(e);
          setDrag({ x: p.x, y: p.y, x2: p.x, y2: p.y });
        }}
        onPointerMove={(e) => drag && setDrag({ ...drag, x2: at(e).x, y2: at(e).y })}
        onPointerUp={() => {
          if (!drag) return;
          const [x, w] = [Math.min(drag.x, drag.x2), Math.abs(drag.x2 - drag.x)];
          const [y, h] = [Math.min(drag.y, drag.y2), Math.abs(drag.y2 - drag.y)];
          setDrag(null);
          if (w < 0.02 || h < 0.02) return; // a click, not a box
          onChange([...regions, { kind: "sway", box: [x, y, w, h], intensity: 50, anchor: "top" }]);
          setPicked(regions.length);
        }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={picture} alt="Cover picture" draggable={false} className="size-full object-cover" />
        {regions.map((r, i) => (
          <div key={i} className="absolute border-2" aria-hidden
            style={{ left: `${r.box[0] * 100}%`, top: `${r.box[1] * 100}%`, width: `${r.box[2] * 100}%`, height: `${r.box[3] * 100}%`,
              borderColor: COLORS[r.kind], background: picked === i ? `${COLORS[r.kind]}33` : undefined }}>
            <span className="absolute top-0 left-0 px-1 text-xs font-bold text-black" style={{ background: COLORS[r.kind] }}>{i + 1}</span>
          </div>
        ))}
        {drag && (
          <div className="absolute border-2 border-dashed border-white" aria-hidden
            style={{ left: `${Math.min(drag.x, drag.x2) * 100}%`, top: `${Math.min(drag.y, drag.y2) * 100}%`,
              width: `${Math.abs(drag.x2 - drag.x) * 100}%`, height: `${Math.abs(drag.y2 - drag.y) * 100}%` }} />
        )}
      </div>
      {regions.length > 0 && (
        <ol className="m-0 grid list-none gap-1.5 p-0">
          {regions.map((r, i) => (
            <li key={i} className={`flex flex-wrap items-center gap-2 rounded-lg border px-2 py-1.5 text-sm ${picked === i ? "border-cobalt" : "border-line"}`}
              onFocus={() => setPicked(i)} onMouseEnter={() => setPicked(i)}>
              <span className="w-5 font-bold" style={{ color: COLORS[r.kind] }}>{i + 1}</span>
              <select className="field-input h-8 w-auto py-0 text-sm" aria-label={`Region ${i + 1}: how it moves`} value={r.kind} disabled={disabled}
                onChange={(e) => set(i, { kind: e.target.value, anchor: e.target.value === "sway" ? "top" : "bottom" })}>
                {Object.entries(kinds).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
              </select>
              {(r.kind === "sway" || r.kind === "breathe" || r.kind === "nod") && (
                <label className="flex items-center gap-1">
                  <span className="text-ink-soft">fixed at</span>
                  <select className="field-input h-8 w-auto py-0 text-sm" value={r.anchor} disabled={disabled}
                    onChange={(e) => set(i, { anchor: e.target.value as LivingRegion["anchor"] })}>
                    {ANCHORS.map((a) => <option key={a} value={a}>{a}</option>)}
                  </select>
                </label>
              )}
              {r.kind !== "protect" && (
                <label className="flex items-center gap-1">
                  <span className="text-ink-soft">strength</span>
                  <input type="range" min={0} max={100} value={r.intensity} disabled={disabled} className="w-24 accent-cobalt"
                    aria-label={`Region ${i + 1}: strength`} onChange={(e) => set(i, { intensity: Number(e.target.value) })} />
                  <span className="w-7 tabular-nums text-ink-soft">{r.intensity}</span>
                </label>
              )}
              <Button size="sm" variant="ghost" icon={<Trash2 className="size-3.5" />} disabled={disabled} className="ml-auto"
                onClick={() => { onChange(regions.filter((_, k) => k !== i)); setPicked(null); }}>Remove</Button>
            </li>
          ))}
        </ol>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" variant="secondary" icon={<Eye className="size-3.5" />} disabled={disabled || !regions.length} onClick={onPreview}>
          Preview
        </Button>
        <span className="text-sm text-ink-soft">A small preview of the whole loop, made in a few seconds.</span>
      </div>
      {preview && <video key={preview} src={preview} className="w-full rounded-lg bg-black" autoPlay loop muted playsInline aria-label="Living loop preview" />}
    </div>
  );
}
