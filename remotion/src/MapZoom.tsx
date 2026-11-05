import { geoContains, geoGraticule10, geoOrthographic, geoPath } from "d3-geo";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { useMemo } from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import world from "world-atlas/countries-110m.json";
import { useFont } from "./font";

export type MapProps = {
  lat: number;
  lon: number;
  place: string;  // the name as the voice says it ("the Arctic Ocean", "Greenland")
  zoom: "world" | "continent" | "country" | "region" | "city";
  font: string;
  seconds?: number;
};

const SLATE = "#F8FAFC", AMBER = "#FACC15", SKY = "#38BDF8";
const CX = 540, CY = 720, R = 330;  // the lens: over the picture, clear of the top labels and the captions (y ~1230)
const ZOOM = { world: 1, continent: 1.9, country: 3.4, region: 5.5, city: 9 };

const countries = feature(world as unknown as Topology, (world as unknown as Topology).objects.countries as GeometryCollection) as
  unknown as FeatureCollection<Geometry>;
const graticule = geoGraticule10();

export const MapZoom = ({ lat, lon, place, zoom, font }: MapProps) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const family = useFont(font);
  const home = useMemo(() => countries.features.find((f: Feature<Geometry>) => geoContains(f, [lon, lat])), [lat, lon]);

  const lens = spring({ frame, fps, config: { damping: 14, stiffness: 150 } });
  const exit = interpolate(frame, [durationInFrames - 8, durationInFrames], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.in(Easing.cubic) });
  // spin to the place, then dive in
  const spin = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const dive = interpolate(frame, [24, 54], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const k = ZOOM[zoom] ?? 3.4;
  const projection = geoOrthographic()
    .translate([CX, CY])
    .scale(R * 0.96 * (1 + (k - 1) * dive))
    .rotate([-lon + 110 * (1 - spin), -lat + 25 * (1 - spin)])
    .clipAngle(90);
  const path = geoPath(projection);
  const [px, py] = projection([lon, lat]) ?? [CX, CY];
  const pin = spring({ frame: frame - 46, fps, config: { damping: 9, stiffness: 200 } });
  const glow = interpolate(frame, [40, 56], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const tag = spring({ frame: frame - 52, fps, config: { damping: 15, stiffness: 160 } });
  const pulse = ((frame - 46) % 24) / 24;

  return (
    <AbsoluteFill style={{ opacity: 1 - exit, fontFamily: family }}>
      <svg width={1080} height={1920} style={{ position: "absolute", transform: `scale(${0.7 + 0.3 * lens})`, transformOrigin: `${CX}px ${CY}px`, opacity: lens }}>
        <defs>
          <clipPath id="lens"><circle cx={CX} cy={CY} r={R} /></clipPath>
          <radialGradient id="sea" cx="45%" cy="40%"><stop offset="0%" stopColor="#0C4A6E" /><stop offset="100%" stopColor="#082F49" /></radialGradient>
          <filter id="soft"><feGaussianBlur stdDeviation="14" /></filter>
        </defs>
        <circle cx={CX} cy={CY} r={R + 18} fill={SKY} opacity={0.22} filter="url(#soft)" />
        <g clipPath="url(#lens)">
          <rect x={CX - R} y={CY - R} width={2 * R} height={2 * R} fill="#020617" />
          <path d={path({ type: "Sphere" }) ?? ""} fill="url(#sea)" />
          <path d={path(graticule) ?? ""} fill="none" stroke={SKY} strokeOpacity={0.12} strokeWidth={1.2} />
          <path d={path(countries) ?? ""} fill="#475569" stroke={SKY} strokeOpacity={0.55} strokeWidth={1.2} />
          {home && <path d={path(home) ?? ""} fill={AMBER} fillOpacity={0.85 * glow} stroke={AMBER} strokeOpacity={glow} strokeWidth={2} />}
          {pin > 0.01 && (
            <g>
              {frame > 46 && <circle cx={px} cy={py} r={14 + 60 * pulse} fill="none" stroke={AMBER} strokeWidth={4} opacity={1 - pulse} />}
              <g transform={`translate(${px}, ${py - 70 * (1 - pin)})`} opacity={Math.min(pin * 2, 1)}>
                <path d="M0 0 C -6 -14 -22 -24 -22 -42 A 22 22 0 1 1 22 -42 C 22 -24 6 -14 0 0 Z" fill={AMBER} stroke="#020617" strokeWidth={4} />
                <circle cx={0} cy={-42} r={8} fill="#020617" />
              </g>
            </g>
          )}
        </g>
        <circle cx={CX} cy={CY} r={R} fill="none" stroke={SKY} strokeWidth={4} />
      </svg>
      <div style={{
        position: "absolute", left: 0, right: 0, top: CY + R + 26, display: "flex", justifyContent: "center",
        opacity: Math.min(tag, 1), transform: `translateY(${(1 - tag) * 30}px)`,
      }}>
        <div style={{
          padding: "14px 34px", borderRadius: 999, background: "rgba(2, 6, 23, 0.86)", border: `3px solid ${SKY}`,
          color: SLATE, fontSize: 50, fontWeight: 900, letterSpacing: 2, whiteSpace: "nowrap", maxWidth: 860,
          overflow: "hidden", textOverflow: "ellipsis", boxShadow: `0 0 30px ${SKY}55`,
        }}>
          <span style={{ color: AMBER }}>● </span>{place.toUpperCase()}
        </div>
      </div>
    </AbsoluteFill>
  );
};
