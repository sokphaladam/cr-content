"use client";

/** Optional idea for a music video (setting, story, look); the footage for every section follows it. */
export function VideoIdea({ id, value, onChange }: { id: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="grid gap-1">
      <label htmlFor={id} className="field-label">
        Video idea <span className="font-normal">optional</span>
      </label>
      <textarea
        id={id}
        rows={2}
        maxLength={1000}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="A woman driving alone through neon Tokyo at night, rain on the windshield"
        className="field-input min-h-[3.5rem] resize-y text-[13.5px]"
      />
      <p className="m-0 text-xs text-ink-soft">The footage follows your idea, matched to each part of the song. Leave empty to let the lyrics decide.</p>
    </div>
  );
}
