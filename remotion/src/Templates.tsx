import { AbsoluteFill, Easing, Img, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useFont } from "./font";

// The editor's graphics templates (attention roadmap M5). Each draws around the frame's centre (540, 960) on a
// transparent 1080 x 1920 frame; Placed moves, scales and animates it in and out. Their props are checked against
// crcontent/graphic_templates.py before they get here.

const C = { x: 540, y: 960 };
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const stroke = (px: number) => ({ WebkitTextStroke: `${px}px #111`, paintOrder: "stroke fill" as const });

/* ---------- Kinetic title: a hook or section headline, word by word ---------- */

export type KineticTitleProps = { text: string; style: "bold" | "box" | "outline"; accent: string; font: string; seconds?: number };

export const KineticTitle = ({ text, style, accent, font }: KineticTitleProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const family = useFont(font);
  const words = text.trim().split(/\s+/).filter(Boolean);
  const size = text.length <= 12 ? 140 : text.length <= 26 ? 104 : 78;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0 24px", maxWidth: 960, textAlign: "center" }}>
        {words.map((w, k) => {
          const s = spring({ frame: frame - k * 3, fps, config: { damping: 11, stiffness: 190 } });
          return (
            <span
              key={k}
              style={{
                fontFamily: family, fontWeight: 900, fontSize: size, lineHeight: 1.1, textTransform: "uppercase",
                display: "inline-block", opacity: Math.min(1, s * 1.5), transform: `translateY(${(1 - s) * 60}px) scale(${0.7 + 0.3 * s})`,
                ...(style === "box"
                  ? { background: accent, color: "#111", padding: "4px 18px", borderRadius: 10, margin: "6px 0" }
                  : style === "outline"
                    ? { color: "transparent", WebkitTextStroke: `5px ${accent}` }
                    : { color: k === words.length - 1 ? accent : "#fff", ...stroke(12) }),
              }}
            >
              {w}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/* ---------- Callout: a circle, arrow or box drawing attention to something, with a label ---------- */

export type CalloutProps = { shape: "circle" | "arrow" | "box"; label: string; size: number; accent: string; font: string; seconds?: number };

export const Callout = ({ shape, label, size, accent, font }: CalloutProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const family = useFont(font);
  const draw = interpolate(frame, [0, 14], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const tag = spring({ frame: frame - 10, fps, config: { damping: 13, stiffness: 180 } });
  const r = size;
  const w = shape === "box" ? r * 2.2 : r * 2;
  const h = shape === "box" ? r * 1.5 : r * 2;
  const perimeter = shape === "circle" ? 2 * Math.PI * r : 2 * (w + h);
  return (
    <AbsoluteFill>
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        {shape === "arrow" ? (
          <g stroke={accent} strokeWidth={16} strokeLinecap="round" fill="none" style={{ filter: "drop-shadow(0 4px 6px #0009)" }}>
            <line x1={C.x} y1={C.y - r * 2.4} x2={C.x} y2={C.y - r * 2.4 + (r * 2.4 - 20) * draw} />
            {draw > 0.85 && <polyline points={`${C.x - 46},${C.y - 66} ${C.x},${C.y - 18} ${C.x + 46},${C.y - 66}`} />}
          </g>
        ) : shape === "circle" ? (
          <circle cx={C.x} cy={C.y} r={r} stroke={accent} strokeWidth={14} fill="none" strokeDasharray={perimeter}
            strokeDashoffset={perimeter * (1 - draw)} transform={`rotate(-90 ${C.x} ${C.y})`} style={{ filter: "drop-shadow(0 4px 6px #0009)" }} />
        ) : (
          <rect x={C.x - w / 2} y={C.y - h / 2} width={w} height={h} rx={24} stroke={accent} strokeWidth={14} fill="none"
            strokeDasharray={perimeter} strokeDashoffset={perimeter * (1 - draw)} style={{ filter: "drop-shadow(0 4px 6px #0009)" }} />
        )}
      </svg>
      {label && (
        <div style={{
          position: "absolute", left: 0, right: 0, top: shape === "arrow" ? C.y - r * 2.4 - 110 : C.y + h / 2 + 28,
          display: "flex", justifyContent: "center", opacity: tag, transform: `translateY(${(1 - tag) * 24}px)`,
        }}>
          <span style={{ fontFamily: family, fontWeight: 900, fontSize: 58, color: "#111", background: accent, padding: "8px 24px", borderRadius: 14, textTransform: "uppercase", maxWidth: 900, textAlign: "center" }}>
            {label}
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
};

/* ---------- Lower third: a subject, species or place, with a short line under it ---------- */

export type LowerThirdProps = { title: string; subtitle: string; accent: string; font: string; seconds?: number };

export const LowerThird = ({ title, subtitle, accent, font }: LowerThirdProps) => {
  const frame = useCurrentFrame();
  const family = useFont(font);
  const bar = interpolate(frame, [0, 10], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const text = interpolate(frame, [6, 16], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 90, top: C.y - 90, width: 900, display: "flex", gap: 22 }}>
        <div style={{ width: 14, borderRadius: 7, background: accent, transform: `scaleY(${bar})`, transformOrigin: "top" }} />
        <div style={{ background: "rgba(10,12,18,0.82)", padding: "22px 30px", borderRadius: 18, clipPath: `inset(0 ${(1 - bar) * 100}% 0 0)` }}>
          <div style={{ fontFamily: family, fontWeight: 900, fontSize: 72, color: "#fff", lineHeight: 1.05, opacity: text, transform: `translateX(${(1 - text) * -30}px)` }}>{title}</div>
          {subtitle && <div style={{ fontFamily: family, fontWeight: 700, fontSize: 44, color: accent, marginTop: 8, opacity: text }}>{subtitle}</div>}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- Freeze-frame spotlight: the picture holds still, everything but the subject dims ---------- */

export type SpotlightProps = { photo: string; spot_x: number; spot_y: number; radius: number; dim: number; label: string; accent: string; font: string; seconds?: number };

export const Spotlight = ({ photo, spot_x, spot_y, radius, dim, label, accent, font }: SpotlightProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const family = useFont(font);
  const open = spring({ frame, fps, config: { damping: 15, stiffness: 120 } });
  const cx = spot_x * 1080;
  const cy = spot_y * 1920;
  const r = radius * 1080 * (0.6 + 0.4 * open);
  return (
    <AbsoluteFill>
      {photo && <Img src={photo} style={{ position: "absolute", inset: 0, width: 1080, height: 1920, objectFit: "cover" }} />}
      <div style={{ position: "absolute", inset: 0, background: `radial-gradient(circle at ${cx}px ${cy}px, transparent ${r}px, rgba(0,0,0,${dim * open}) ${r + 24}px)` }} />
      <div style={{ position: "absolute", left: cx - r, top: cy - r, width: r * 2, height: r * 2, borderRadius: "50%", border: `8px solid ${accent}`, opacity: open, boxShadow: `0 0 30px ${accent}` }} />
      {label && (
        <div style={{ position: "absolute", left: 0, right: 0, top: Math.min(cy + r + 30, 1700), display: "flex", justifyContent: "center", opacity: open }}>
          <span style={{ fontFamily: family, fontWeight: 900, fontSize: 60, color: "#111", background: accent, padding: "8px 24px", borderRadius: 14, textTransform: "uppercase" }}>{label}</span>
        </div>
      )}
    </AbsoluteFill>
  );
};

/* ---------- Split comparison: two subjects, sizes or states side by side ---------- */

export type SplitCompareProps = { title: string; left_label: string; left_value: string; right_label: string; right_value: string; accent: string; font: string; seconds?: number };

export const SplitCompare = ({ title, left_label, left_value, right_label, right_value, accent, font }: SplitCompareProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const family = useFont(font);
  const l = spring({ frame, fps, config: { damping: 14, stiffness: 150 } });
  const r = spring({ frame: frame - 5, fps, config: { damping: 14, stiffness: 150 } });
  const vs = spring({ frame: frame - 12, fps, config: { damping: 8, stiffness: 220 } });
  const panel = (label: string, value: string, s: number, side: number, colour: string) => (
    <div style={{
      width: 430, minHeight: 360, borderRadius: 28, background: "rgba(10,12,18,0.85)", border: `6px solid ${colour}`,
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 14, padding: 24,
      opacity: s, transform: `translateX(${(1 - s) * 160 * side}px)`,
    }}>
      <div style={{ fontFamily: family, fontWeight: 900, fontSize: 92, color: colour, textAlign: "center", lineHeight: 1 }}>{value}</div>
      <div style={{ fontFamily: family, fontWeight: 800, fontSize: 46, color: "#fff", textAlign: "center", textTransform: "uppercase" }}>{label}</div>
    </div>
  );
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 30 }}>
      {title && <div style={{ fontFamily: family, fontWeight: 900, fontSize: 64, color: "#fff", textTransform: "uppercase", opacity: l, ...stroke(10) }}>{title}</div>}
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        {panel(left_label, left_value, l, -1, accent)}
        {panel(right_label, right_value, r, 1, "#FFFFFF")}
      </div>
      <div style={{
        position: "absolute", left: C.x - 60, top: C.y - 60 + (title ? 47 : 0), width: 120, height: 120, borderRadius: "50%",
        background: accent, display: "grid", placeItems: "center", transform: `scale(${vs})`,
        fontFamily: family, fontWeight: 900, fontSize: 52, color: "#111",
      }}>VS</div>
    </AbsoluteFill>
  );
};

/* ---------- Process: a few steps in order, one after another ---------- */

export type ProcessProps = { title: string; steps: string; accent: string; font: string; seconds?: number };

export const Process = ({ title, steps, accent, font }: ProcessProps) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const family = useFont(font);
  const items = steps.split(/[;\n]/).map((s) => s.trim()).filter(Boolean).slice(0, 5);
  const every = Math.max(6, Math.floor((durationInFrames * 0.6) / Math.max(items.length, 1)));
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: 900, display: "flex", flexDirection: "column", gap: 26 }}>
        {title && <div style={{ fontFamily: family, fontWeight: 900, fontSize: 66, color: "#fff", textTransform: "uppercase", ...stroke(10) }}>{title}</div>}
        {items.map((step, k) => {
          const s = spring({ frame: frame - k * every, fps, config: { damping: 14, stiffness: 170 } });
          return (
            <div key={k} style={{ display: "flex", alignItems: "center", gap: 24, opacity: s, transform: `translateX(${(1 - s) * -60}px)` }}>
              <div style={{ width: 92, height: 92, flexShrink: 0, borderRadius: "50%", background: accent, display: "grid", placeItems: "center", fontFamily: family, fontWeight: 900, fontSize: 52, color: "#111" }}>{k + 1}</div>
              <div style={{ fontFamily: family, fontWeight: 800, fontSize: 54, color: "#fff", background: "rgba(10,12,18,0.82)", padding: "14px 26px", borderRadius: 16, lineHeight: 1.1 }}>{step}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
