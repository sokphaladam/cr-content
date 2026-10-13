"use client";

import { ChevronDown, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { ArtStylePicker, artBlocker, useArtStatus } from "./ArtControls";
import { ShotList } from "./ShotList";
import { SongPictures } from "./SongPictures";
import {
  api,
  type Aspect,
  type Lang,
  type Look,
  type LyricPreset,
  type LyricStyle,
  type MusicVideoSettings,
  type PicturePace,
  type StyleCatalog,
  type VideoIdeaSuggestion,
} from "@/lib/api";
import { Button, Segmented } from "./ui";

// The catalog (presets, looks, installed fonts) is the same for every song: fetch it once per page load.
let catalogPromise: Promise<StyleCatalog | null> | null = null;
function useStyleCatalog() {
  const [catalog, setCatalog] = useState<StyleCatalog | null>(null);
  useEffect(() => {
    catalogPromise ??= api
      .options()
      .then((o) => o.styles ?? null)
      .catch(() => {
        catalogPromise = null; // try again next time
        return null;
      });
    let alive = true;
    void catalogPromise.then((c) => alive && setCatalog(c));
    return () => {
      alive = false;
    };
  }, []);
  return catalog;
}

/** A preset as a full style: the font is left to the engine, which picks the preset's font for the language. */
function fromPreset(catalog: StyleCatalog, key: LyricPreset): LyricStyle {
  const { preset, size, position, color, highlight, effect, outline, case: textCase } = catalog.presets[key];
  return { preset: preset ?? key, font: "", size, position, color, highlight, effect, outline, case: textCase };
}

/** The font the engine will use for this style and language. */
function fontFor(catalog: StyleCatalog, style: LyricStyle, lang: Lang) {
  const p = catalog.presets[style.preset] ?? catalog.presets.classic;
  return style.font || (lang === "km" ? p.font_km : p.font);
}

// CSS stand-ins for the colour grades in crcontent/styles.py LOOKS, applied to the swatches and the preview
const LOOK_CSS: Record<Look, string> = {
  natural: "brightness(0.96) saturate(1.08)",
  cinematic: "contrast(1.1) saturate(1.05) brightness(0.92) hue-rotate(-8deg)",
  film: "sepia(0.25) contrast(1.05) saturate(0.9)",
  moody: "contrast(1.12) saturate(0.7) brightness(0.82)",
  vibrant: "contrast(1.06) saturate(1.4)",
  dusk: "sepia(0.2) hue-rotate(-18deg) saturate(1.45) contrast(1.06)",
  mono: "grayscale(1) contrast(1.15)",
};
const SCENE_BG = "linear-gradient(180deg,#f2a65a 0%,#c9576b 38%,#3b4a8c 70%,#0f1a33 100%)";

const SIZE_PX = { s: 0.8, m: 1, l: 1.25 };

// crcontent/pipeline.py PICTURE_PACES; minutes are for a 3-minute song at ~40 s a picture
const PACES: Record<PicturePace, { label: string; hint: string }> = {
  fewer: { label: "Fewer", hint: "A new picture every ~8 s: about 20 pictures for a 3-minute song (~13 min to draw). Good for slow songs and quick drafts." },
  normal: { label: "Normal", hint: "A new picture every ~4.5 s: about 35 pictures for a 3-minute song (~25 min to draw)." },
  more: { label: "More", hint: "A new picture every ~3 s: about 50 pictures for a 3-minute song (~35 min to draw). For fast, high-energy songs." },
};

function textCss(style: LyricStyle, font: string, sung: boolean): React.CSSProperties {
  const color = sung ? style.highlight : style.color;
  const css: React.CSSProperties = { fontFamily: `"${font}", Arial, sans-serif`, color, fontWeight: 700 };
  if (style.outline === "outline") css.textShadow = "0 0 2px #000, 0 0 2px #000, 0 0 3px #000, 1px 2px 2px rgb(0 0 0 / 0.6)";
  if (style.outline === "shadow") css.textShadow = "0 2px 6px rgb(0 0 0 / 0.75)";
  if (style.outline === "glow") css.textShadow = `0 0 6px ${style.highlight}, 0 0 14px ${style.highlight}aa`;
  return css;
}

/** A sample line of lyrics drawn roughly the way the video will draw it, with the words being "sung" in a loop. */
function LyricPreview({ style, font, lang, aspect, look, sample }: { style: LyricStyle; font: string; lang: Lang; aspect: Aspect; look: Look; sample: string }) {
  const words = sample.split(/\s+/).filter(Boolean).slice(0, lang === "km" ? 4 : 7);
  const [sung, setSung] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setSung((n) => (n >= words.length + 2 ? 0 : n + 1)), 420);
    return () => clearInterval(t);
  }, [words.length]);
  const top = { low: aspect === "16:9" ? "80%" : "64%", middle: "50%", high: aspect === "16:9" ? "20%" : "24%" }[style.position];
  const display = (w: string) => (lang === "km" ? w : style.case === "upper" ? w.toUpperCase() : style.case === "lower" ? w.toLowerCase() : w);
  return (
    <div
      className={`@container relative mx-auto w-full overflow-hidden rounded-lg ${aspect === "16:9" ? "aspect-video" : "aspect-[9/16] max-w-[150px]"}`}
      aria-hidden
    >
      <div className="absolute inset-0" style={{ background: SCENE_BG, filter: LOOK_CSS[look] }} />
      <p
        lang={lang}
        className="absolute inset-x-[6%] m-0 -translate-y-1/2 text-center leading-tight"
        style={{ top, fontSize: `${(aspect === "16:9" ? 4.6 : 7.4) * SIZE_PX[style.size]}cqw` }}
      >
        <span
          className={style.outline === "box" ? "rounded-[0.15em] bg-black/40 box-decoration-clone px-[0.25em] py-[0.05em]" : ""}
          style={{ opacity: style.effect === "fade" ? (sung === 0 || sung > words.length ? 0.15 : 1) : 1, transition: "opacity 0.3s" }}
        >
          {words.map((w, i) => {
            const isSung = style.effect !== "fade" && i < sung;
            const hidden = style.effect === "pop" && i >= sung;
            return (
              <span key={i} style={{ ...textCss(style, font, isSung), opacity: hidden ? 0 : 1, transition: style.effect === "fill" ? "color 0.35s" : undefined }}>
                {display(w)}
                {i < words.length - 1 ? " " : ""}
              </span>
            );
          })}
        </span>
      </p>
    </div>
  );
}

function Pick<T extends string>({ label, value, options, onChange }: { label: string; value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <div className="grid justify-items-start gap-1">
      <span className="field-label">{label}</span>
      <Segmented name={label} size="sm" value={value} options={options} onChange={onChange} />
    </div>
  );
}

/** Idea, footage look and lyric style for a music video. `name` is the song's folder (for Claude's idea suggestions). */
export function MusicVideoOptions({
  name,
  lang,
  aspect,
  sample,
  sections,
  value,
  onChange,
}: {
  name: string;
  lang: Lang;
  aspect: Aspect;
  sample: string; // a lyric line for the style preview
  sections: string[]; // the song's section names, in order (for the shot list)
  value: MusicVideoSettings;
  onChange: (v: MusicVideoSettings) => void;
}) {
  const catalog = useStyleCatalog();
  const art = useArtStatus();
  const [ideas, setIdeas] = useState<VideoIdeaSuggestion[] | null>(null);
  const [ideasBusy, setIdeasBusy] = useState(false);
  const [ideasError, setIdeasError] = useState("");
  const [custom, setCustom] = useState(false);

  const look: Look = value.look || "natural";
  const style: LyricStyle | null = catalog ? (value.lyric_style ?? fromPreset(catalog, "classic")) : null;
  const setStyle = (patch: Partial<LyricStyle>) => style && onChange({ ...value, lyric_style: { ...style, ...patch } });

  async function suggest() {
    setIdeasBusy(true);
    setIdeasError("");
    try {
      setIdeas((await api.videoIdeas(name)).ideas);
    } catch (e) {
      setIdeasError((e as Error).message);
    } finally {
      setIdeasBusy(false);
    }
  }

  const ideaId = `mv-idea-${name}`;
  return (
    <div className="grid gap-3">
      <div className="grid gap-1">
        <div className="flex items-center justify-between gap-2">
          <label htmlFor={ideaId} className="field-label">
            Video idea <span className="font-normal">optional</span>
          </label>
          <Button size="sm" variant="ghost" icon={<Sparkles className="size-3.5" />} loading={ideasBusy} onClick={suggest}>
            {ideas ? "More ideas" : "Suggest ideas"}
          </Button>
        </div>
        <textarea
          id={ideaId}
          rows={2}
          maxLength={4000}
          value={value.idea}
          onChange={(e) => onChange({ ...value, idea: e.target.value })}
          placeholder="Empty city streets at blue hour, rain on neon signs, a lone figure under an umbrella"
          className="field-input min-h-[3.5rem] resize-y text-[13.5px]"
        />
        {ideasError && <p className="m-0 text-xs text-danger">{ideasError}</p>}
        {ideas && (
          <ul className="m-0 grid list-none gap-1.5 p-0">
            {ideas.map((idea, i) => {
              const chosen = value.idea === idea.idea;
              return (
                <li key={i}>
                  <button
                    type="button"
                    aria-pressed={chosen}
                    onClick={() =>
                      onChange({ ...value, idea: idea.idea, look: idea.look, lyric_style: catalog ? fromPreset(catalog, idea.lyric_style) : value.lyric_style })
                    }
                    className={`grid w-full cursor-pointer gap-0.5 rounded-lg border p-2 text-left text-[12.5px] transition-colors hover:bg-ink/[0.04] ${
                      chosen ? "border-cobalt bg-cobalt/[0.06]" : "border-line bg-transparent"
                    }`}
                  >
                    <span className="font-semibold text-ink">{idea.title}</span>
                    <span className="text-ink-soft">{idea.idea}</span>
                    <span className="text-[11.5px] text-ink-soft">
                      {catalog?.looks[idea.look] ?? idea.look} look · {catalog?.presets[idea.lyric_style]?.label ?? idea.lyric_style} lyrics
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        <p className="m-0 text-xs text-ink-soft">The footage follows your idea, matched to each part of the song. Leave empty to let the lyrics decide.</p>
        {sections.length > 0 && (
          <ShotList
            name={name}
            sections={sections}
            idea={value.idea}
            direction={value.direction}
            onChange={(direction) => onChange({ ...value, direction })}
            onDirected={(d) =>
              onChange({
                ...value,
                direction: d,
                ...(d.look ? { look: d.look } : {}),
                ...(catalog && d.lyric_preset ? { lyric_style: { ...fromPreset(catalog, d.lyric_preset), font: d.lyric_font ?? "" } } : {}),
              })
            }
          />
        )}
      </div>

      <div className="grid gap-1">
        <span className="field-label">Visuals</span>
        <ArtStylePicker value={value.art_style ?? ""} onChange={(art_style) => onChange({ ...value, art_style })} status={art.status} reload={art.reload} />
        {value.art_style && !artBlocker(art.status, value.art_style) && (
          <>
            <p className="m-0 text-xs text-ink-soft">
              Claude plans a picture story from the lyrics, then each one is drawn on your GPU (about 40 seconds each) and cut on the beat with 3D
              camera moves, zoom punches and flashes. A chorus sung again shows its pictures again, from new camera angles.
            </p>
            <div className="mt-1 grid justify-items-start gap-1">
              <span className="field-label">Pictures</span>
              <Segmented
                name={`${ideaId}-pictures`}
                size="sm"
                value={value.pictures ?? "normal"}
                onChange={(pictures: PicturePace) => onChange({ ...value, pictures })}
                options={(Object.keys(PACES) as PicturePace[]).map((k) => ({ value: k, label: PACES[k].label }))}
              />
              <p className="m-0 text-xs text-ink-soft">{PACES[value.pictures ?? "normal"].hint}</p>
            </div>
            <SongPictures
              name={name}
              direction={value.direction ?? null}
              style={value.art_style}
              pace={value.pictures ?? "normal"}
              idea={value.idea}
              look={look}
              aspect={aspect}
              status={art.status}
              blocker={artBlocker(art.status, value.art_style)}
            />
          </>
        )}
      </div>

      {catalog && style && (
        <>
          <div className="grid gap-1">
            <span className="field-label">Footage look</span>
            <div role="radiogroup" aria-label="Footage look" className="grid grid-cols-3 gap-1.5">
              {(Object.keys(catalog.looks) as Look[]).map((k) => (
                <button
                  key={k}
                  type="button"
                  role="radio"
                  aria-checked={look === k}
                  onClick={() => onChange({ ...value, look: k })}
                  className={`grid cursor-pointer gap-1 rounded-lg border bg-transparent p-1 text-[11.5px] font-semibold ${look === k ? "border-cobalt text-ink" : "border-line text-ink-soft"}`}
                >
                  <span className="block h-7 rounded" style={{ background: SCENE_BG, filter: LOOK_CSS[k] }} />
                  {catalog.looks[k]}
                </button>
              ))}
            </div>
            <p className="m-0 text-xs text-ink-soft">One colour grade over every clip, with a slow camera drift, so the footage looks like one film.</p>
          </div>

          <div className="grid gap-1.5">
            <span className="field-label">Lyrics style</span>
            <div role="radiogroup" aria-label="Lyrics style" className="grid grid-cols-3 gap-1.5">
              {(Object.keys(catalog.presets) as LyricPreset[]).map((k) => {
                const p = fromPreset(catalog, k);
                const active = style.preset === k;
                return (
                  <button
                    key={k}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => onChange({ ...value, lyric_style: p })}
                    className={`grid cursor-pointer place-items-center gap-0.5 rounded-lg border bg-[#141a26] px-1 py-1.5 ${active ? "border-cobalt outline-2 outline-cobalt" : "border-line"}`}
                  >
                    <span lang={lang} className="text-[15px] leading-none" style={textCss(p, fontFor(catalog, p, lang), true)}>
                      {lang === "km" ? "ចម្រៀង" : p.case === "upper" ? "AA" : p.case === "lower" ? "aa" : "Aa"}
                    </span>
                    <span className="text-[11px] font-semibold text-white/70">{catalog.presets[k].label}</span>
                  </button>
                );
              })}
            </div>
            <LyricPreview style={style} font={fontFor(catalog, style, lang)} lang={lang} aspect={aspect} look={look} sample={sample} />
            <button
              type="button"
              aria-expanded={custom}
              onClick={() => setCustom((c) => !c)}
              className="flex cursor-pointer items-center gap-1 justify-self-start border-0 bg-transparent p-0 text-[12.5px] font-semibold text-cobalt"
            >
              <ChevronDown className={`size-3.5 transition-transform ${custom ? "rotate-180" : ""}`} /> Customize font, colours and effect
            </button>
            {custom && (
              <div className="grid gap-2.5 rounded-lg border border-line p-2.5">
                <div className="grid gap-1">
                  <label className="field-label" htmlFor={`${ideaId}-font`}>
                    Font
                  </label>
                  <select
                    id={`${ideaId}-font`}
                    value={fontFor(catalog, style, lang)}
                    onChange={(e) => setStyle({ font: e.target.value })}
                    className="field-input h-9 py-0 text-[13px]"
                  >
                    {(catalog.fonts[lang] ?? []).map((f) => (
                      <option key={f} value={f} style={{ fontFamily: `"${f}"` }}>
                        {f}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-wrap gap-3">
                  <label className="grid gap-1 text-[12.5px]">
                    <span className="field-label">Text</span>
                    <input type="color" value={style.color} onChange={(e) => setStyle({ color: e.target.value.toUpperCase() })} className="h-8 w-12 cursor-pointer rounded border border-line bg-panel p-0.5" />
                  </label>
                  <label className="grid gap-1 text-[12.5px]">
                    <span className="field-label">Sung words</span>
                    <input type="color" value={style.highlight} onChange={(e) => setStyle({ highlight: e.target.value.toUpperCase() })} className="h-8 w-12 cursor-pointer rounded border border-line bg-panel p-0.5" />
                  </label>
                </div>
                <Pick
                  label="Effect"
                  value={style.effect}
                  onChange={(effect) => setStyle({ effect })}
                  options={[
                    { value: "karaoke", label: "Karaoke" },
                    { value: "fill", label: "Fill" },
                    { value: "pop", label: "Pop" },
                    { value: "fade", label: "Fade" },
                  ]}
                />
                <Pick
                  label="Edge"
                  value={style.outline}
                  onChange={(outline) => setStyle({ outline })}
                  options={[
                    { value: "outline", label: "Outline" },
                    { value: "shadow", label: "Shadow" },
                    { value: "box", label: "Box" },
                    { value: "glow", label: "Glow" },
                  ]}
                />
                <div className="flex flex-wrap gap-3">
                  <Pick
                    label="Size"
                    value={style.size}
                    onChange={(size) => setStyle({ size })}
                    options={[
                      { value: "s", label: "S" },
                      { value: "m", label: "M" },
                      { value: "l", label: "L" },
                    ]}
                  />
                  <Pick
                    label="Position"
                    value={style.position}
                    onChange={(position) => setStyle({ position })}
                    options={[
                      { value: "high", label: "High" },
                      { value: "middle", label: "Middle" },
                      { value: "low", label: "Low" },
                    ]}
                  />
                </div>
                {lang !== "km" && (
                  <Pick
                    label="Letters"
                    value={style.case}
                    onChange={(c) => setStyle({ case: c })}
                    options={[
                      { value: "as_is", label: "As written" },
                      { value: "upper", label: "CAPS" },
                      { value: "lower", label: "lower" },
                    ]}
                  />
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
