import type { ComponentType } from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

/** What every graphic shares (attention roadmap M5): where it sits, how big, turned, see-through, and how it comes
 *  in and goes out. Templates draw around the frame's centre; this moves the whole drawing. The defaults change
 *  nothing, so a graphic rendered without them (Shorts mode's Fact, MapZoom, SizeCompare) looks as before. */
export type Placement = {
  at_x?: number;     // centre, as a share of the width (0.5 = middle); not x / y, which some templates use themselves
  at_y?: number;     // centre, as a share of the height
  scale?: number;
  rotation?: number; // degrees
  opacity?: number;
  enter?: string;    // ENTERS
  exit?: string;
};

export const ENTERS = ["none", "fade", "pop", "slide_up", "slide_left", "wipe"] as const;
const IN = 9;  // frames of the entry
const OUT = 7; // frames of the exit

const ease = { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) } as const;

/** How far a preset has moved the graphic in or out: t = 0 hidden, 1 settled. */
function look(preset: string, t: number) {
  switch (preset) {
    case "fade": return { o: t, dx: 0, dy: 0, s: 1, clip: 0 };
    case "pop": return { o: Math.min(1, t * 2), dx: 0, dy: 0, s: 0.6 + 0.4 * t + 0.08 * Math.sin(Math.PI * t), clip: 0 };
    case "slide_up": return { o: t, dx: 0, dy: (1 - t) * 140, s: 1, clip: 0 };
    case "slide_left": return { o: t, dx: (1 - t) * 220, dy: 0, s: 1, clip: 0 };
    case "wipe": return { o: 1, dx: 0, dy: 0, s: 1, clip: (1 - t) * 100 };
    default: return { o: 1, dx: 0, dy: 0, s: 1, clip: 0 };
  }
}

export function placed<P extends object>(Inner: ComponentType<P>) {
  const Placed = (props: P & Placement) => {
    const frame = useCurrentFrame();
    const { durationInFrames, width, height } = useVideoConfig();
    const { at_x: x = 0.5, at_y: y = 0.5, scale = 1, rotation = 0, opacity = 1, enter = "none", exit = "none" } = props;
    const a = look(enter, interpolate(frame, [0, IN], [0, 1], ease));
    const b = look(exit, interpolate(frame, [durationInFrames - OUT, durationInFrames], [1, 0], ease));
    const identity = x === 0.5 && y === 0.5 && scale === 1 && !rotation && opacity === 1 && enter === "none" && exit === "none";
    if (identity) return <Inner {...props} />;
    return (
      <AbsoluteFill
        style={{
          opacity: opacity * a.o * b.o,
          transform: `translate(${(x - 0.5) * width + a.dx + b.dx}px, ${(y - 0.5) * height + a.dy + b.dy}px) rotate(${rotation}deg) scale(${scale * a.s * b.s})`,
          transformOrigin: "50% 50%",
          clipPath: a.clip || b.clip ? `inset(0 ${Math.max(a.clip, b.clip)}% 0 0)` : undefined,
        }}
      >
        <Inner {...props} />
      </AbsoluteFill>
    );
  };
  return Placed;
}
