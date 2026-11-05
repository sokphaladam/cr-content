import { AbsoluteFill, Easing, Img, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useFont } from "./font";

export type SizeProps = {
  metres: number;  // the animal's length, as the voice says it
  shown: string;   // the number as said ("12", "2.5")
  unit: string;    // the unit as said ("METRES", "FEET")
  photo: string;   // a 2:1 frame of the animal from its own footage (data: URL), "" = a plain bar
  font: string;
  seconds?: number;
};

const SLATE = "#F8FAFC", AMBER = "#FACC15", SKY = "#38BDF8", PANEL = "rgba(2, 6, 23, 0.74)";
// the area the two figures stand in, over the picture and clear of the captions (y ~1230) and the app header
const LEFT = 170, WIDTH = 740, GROUND = 1010, TALL = 470, GAP = 48;

// what it's measured against: a person, or a phone for anything under 40 cm
const REFS = {
  person: { h: 1.75, w: 0.5, label: "YOU · 1.75 M" },
  phone: { h: 0.15, w: 0.075, label: "PHONE · 15 CM" },
};

const Person = ({ h, color }: { h: number; color: string }) => (
  <svg width={(h * 50) / 175} height={h} viewBox="0 0 50 175" style={{ display: "block" }}>
    <g fill={color}>
      <circle cx="25" cy="12" r="11" />
      <rect x="13" y="26" width="24" height="66" rx="7" />
      <rect x="3" y="28" width="8" height="60" rx="4" />
      <rect x="39" y="28" width="8" height="60" rx="4" />
      <rect x="14" y="86" width="10" height="89" rx="5" />
      <rect x="26" y="86" width="10" height="89" rx="5" />
    </g>
  </svg>
);

const Phone = ({ h, color }: { h: number; color: string }) => (
  <div style={{ width: h / 2, height: h, borderRadius: h * 0.09, border: `${Math.max(2, h * 0.04)}px solid ${color}`, boxSizing: "border-box" }} />
);

export const SizeCompare = ({ metres, shown, unit, photo, font }: SizeProps) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const family = useFont(font);
  const ref = metres >= 0.4 ? REFS.person : REFS.phone;

  // one scale for both, so the bigger one fits the area: px per metre
  const len = Math.max(metres, 0.01);
  const scale = Math.min((WIDTH - GAP) / (ref.w + len), TALL / Math.max(ref.h, len * 0.5));
  const refH = Math.max(ref.h * scale, 26), refW = ref.w * scale;
  const fullW = len * scale, fullH = Math.max(len * 0.5 * scale, 14);
  const x0 = LEFT + (WIDTH - (refW + GAP + fullW)) / 2;

  const enter = spring({ frame, fps, config: { damping: 16, stiffness: 140 } });
  const exit = interpolate(frame, [durationInFrames - 8, durationInFrames], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.in(Easing.cubic) });
  const ground = interpolate(frame, [2, 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const rise = spring({ frame: frame - 6, fps, config: { damping: 12, stiffness: 160 } });
  // the animal comes in at the person's size, then grows to its own: the moment the comparison lands
  const grow = spring({ frame: frame - 16, fps, config: { damping: 13, stiffness: 70, mass: 1.1 } });
  const start = Math.min(refH * 2, fullW);
  const w = interpolate(grow, [0, 1], [start, fullW]), h = interpolate(grow, [0, 1], [start / 2, fullH]);
  const animalIn = interpolate(frame, [14, 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const count = interpolate(frame, [18, 44], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const number = Number(shown.replace(/,/g, ""));
  const label = Number.isFinite(number) && count < 1
    ? (Number.isInteger(number) ? Math.round(number * count).toLocaleString("en-US") : (number * count).toFixed(1))
    : shown;
  const ax = x0 + refW + GAP;

  return (
    <AbsoluteFill style={{ opacity: 1 - exit, fontFamily: family }}>
      <div style={{
        position: "absolute", left: 110, top: 410, width: 860, height: 680, borderRadius: 44, background: PANEL,
        border: `2px solid ${SKY}55`, boxShadow: `0 30px 80px #0009, inset 0 0 60px ${SKY}18`,
        transform: `scale(${0.9 + 0.1 * enter})`, opacity: enter,
      }} />
      {/* the ground both stand on */}
      <div style={{ position: "absolute", left: 150, top: GROUND, width: 780 * ground, height: 4, borderRadius: 2, background: `${SLATE}66` }} />
      {/* the reference */}
      <div style={{ position: "absolute", left: x0, top: GROUND - refH, transformOrigin: "bottom", transform: `scaleY(${rise})` }}>
        {ref === REFS.person ? <Person h={refH} color={SLATE} /> : <Phone h={refH} color={SLATE} />}
      </div>
      <div style={{
        position: "absolute", left: x0 + refW / 2 - 200, width: 400, top: GROUND + 18, textAlign: "center",
        fontSize: 30, fontWeight: 900, letterSpacing: 2, color: `${SLATE}CC`, opacity: rise,
      }}>{ref.label}</div>
      {/* the animal, at its real size against the reference */}
      <div style={{
        position: "absolute", left: ax, top: GROUND - h, width: w, height: h, borderRadius: Math.min(24, h / 4),
        overflow: "hidden", opacity: animalIn, border: `3px solid ${SKY}`, boxShadow: `0 0 30px ${SKY}66`,
        background: photo ? "#000" : `linear-gradient(90deg, ${SKY}, ${SKY}AA)`,
      }}>
        {photo && <Img src={photo} style={{ width: "100%", height: "100%", objectFit: "cover" }} />}
      </div>
      {/* the ruler over it, and the number it measures */}
      <div style={{ position: "absolute", left: ax, top: GROUND - h - 34, width: w, height: 18, opacity: animalIn }}>
        <div style={{ position: "absolute", left: 0, right: 0, top: 8, height: 3, background: SKY }} />
        <div style={{ position: "absolute", left: 0, top: 0, width: 3, height: 18, background: SKY }} />
        <div style={{ position: "absolute", right: 0, top: 0, width: 3, height: 18, background: SKY }} />
      </div>
      <div style={{
        position: "absolute", left: 110, width: 860, top: Math.min(GROUND - h - 150, 900), textAlign: "center",
        opacity: animalIn, transform: `translateY(${(1 - animalIn) * 30}px)`, whiteSpace: "nowrap",
      }}>
        <span style={{ fontSize: 108, fontWeight: 900, color: AMBER, WebkitTextStroke: "10px #020617", paintOrder: "stroke fill", fontVariantNumeric: "tabular-nums" }}>{label}</span>
        <span style={{ fontSize: 54, fontWeight: 900, color: SKY, marginLeft: 18, letterSpacing: 3, WebkitTextStroke: "7px #020617", paintOrder: "stroke fill" }}>{unit}</span>
      </div>
    </AbsoluteFill>
  );
};
