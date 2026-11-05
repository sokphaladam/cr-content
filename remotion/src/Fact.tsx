import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useFont } from "./font";

export type FactProps = {
  shown: string;        // the number as the voice says it ("400", "2.5 MILLION")
  value: number | null; // counts up to it when a whole number from 10 up
  unit: string;         // the word after it ("YEARS"), "" for none
  y: number;            // the number's centre, px from the top (under the app header, over the picture)
  font: string;         // the font as a data: URL (one prebuilt bundle serves every Short), "" = system sans
  accent: string;
  seconds?: number;     // how long it stays on screen
};

const COUNT = 12;  // frames the count-up takes (0.4 s, as the ASS version)
const OUT = 7;     // frames of the exit

export const Fact = ({ shown, value, unit, y, font, accent }: FactProps) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const family = useFont(font);

  const land = spring({ frame, fps, config: { damping: 9, stiffness: 180, mass: 0.7 } });   // slams in, overshoots
  const thump = spring({ frame: frame - COUNT, fps, config: { damping: 7, stiffness: 260 } }); // a beat when it lands
  const exit = interpolate(frame, [durationInFrames - OUT, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.in(Easing.cubic),
  });
  const counts = value !== null && value >= 10 && value <= 1e9;
  const p = Math.min(frame / COUNT, 1);
  const text = counts && p < 1 ? Math.round(value * (1 - (1 - p) ** 3)).toLocaleString("en-US") : shown;

  const scale = interpolate(land, [0, 1], [0.35, 1]) * (1 + 0.07 * Math.sin(Math.PI * Math.min(thump, 1))) * (1 - 0.12 * exit);
  const blur = interpolate(frame, [0, 6], [14, 0], { extrapolateRight: "clamp" }) + 18 * exit;
  const glow = interpolate(frame, [0, 4, 22], [0, 0.9, 0.35], { extrapolateRight: "clamp" }) * (1 - exit);
  const bar = interpolate(frame, [6, 18], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });

  return (
    <AbsoluteFill style={{ opacity: 1 - exit }}>
      {/* a soft burst of light behind the number */}
      <div style={{
        position: "absolute", left: 540 - 420, top: y - 300, width: 840, height: 600, borderRadius: "50%",
        background: `radial-gradient(closest-side, ${accent}AA, ${accent}33 55%, transparent)`,
        opacity: glow, transform: `scale(${0.6 + 0.6 * land})`, filter: "blur(18px)",
      }} />
      {/* sparks flying out as it lands */}
      {Array.from({ length: 12 }, (_, k) => {
        const a = (k / 12) * Math.PI * 2 + 0.3;
        const t = interpolate(frame, [2, 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.quad) });
        const r = 150 + 330 * t;
        return (
          <div key={k} style={{
            position: "absolute", left: 540 + Math.cos(a) * r * 1.3 - 3, top: y + Math.sin(a) * r * 0.7 - 18,
            width: 6, height: 36, borderRadius: 3, background: k % 3 ? accent : "#fff",
            opacity: frame < 2 ? 0 : 1 - t, transform: `rotate(${a + Math.PI / 2}rad) scaleY(${1 - 0.6 * t})`,
          }} />
        );
      })}
      <div style={{
        position: "absolute", left: 0, right: 0, top: y - 110, display: "flex", flexDirection: "column", alignItems: "center",
        transform: `scale(${scale}) rotate(${interpolate(land, [0, 1], [-7, 0])}deg)`, filter: `blur(${blur}px)`,
      }}>
        <div style={{
          fontFamily: family, fontWeight: 900, fontSize: 170, lineHeight: 1, letterSpacing: -2,
          fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap",
          color: accent, WebkitTextStroke: "12px #111", paintOrder: "stroke fill",
          textShadow: `0 10px 0 #0008, 0 0 40px ${accent}88`,
        }}>{text}</div>
        <div style={{ height: 10, width: 360 * bar, marginTop: 14, borderRadius: 5, background: "#fff", boxShadow: `0 0 18px ${accent}` }} />
        {unit && (
          <div style={{ display: "flex", marginTop: 16 }}>
            {[...unit].map((ch, k) => {
              const s = spring({ frame: frame - 8 - k * 1.5, fps, config: { damping: 14, stiffness: 200 } });
              return (
                <span key={k} style={{
                  fontFamily: family, fontWeight: 900, fontSize: 64, letterSpacing: 6, color: "#fff", whiteSpace: "pre",
                  WebkitTextStroke: "8px #111", paintOrder: "stroke fill",
                  opacity: s, transform: `translateY(${(1 - s) * 40}px)`, display: "inline-block",
                }}>{ch}</span>
              );
            })}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
