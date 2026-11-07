import { geoArea, geoDistance, geoGraticule10, geoOrthographic, geoPath } from "d3-geo";
import type { FeatureCollection, Geometry } from "geojson";
import { useMemo } from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import world from "world-atlas/countries-110m.json";
import { useFont } from "./font";

type Point = { label: string; lat: number; lon: number };
export type HistoryMapProps = {
  title: string;
  period: string;
  points: Point[];
  route: "none" | "through_the_places";
  zoom: "continent" | "country" | "region" | "city";
  map_source: string;
  region: Geometry | null;   // only ever a sourced shape (crcontent/graphic_templates.history_map)
  region_source: string;
  region_dates: string;
  accent: string;
  font: string;
  seconds?: number;
};

const SLATE = "#F8FAFC", SKY = "#38BDF8", INK = "#020617";
const CX = 540, CY = 720, R = 330;  // the same lens as MapZoom: clear of the top labels and the captions (y ~1230)
const ZOOM = { continent: 1.9, country: 3.4, region: 5.5, city: 9 };

const countries = feature(world as unknown as Topology, (world as unknown as Topology).objects.countries as GeometryCollection) as
  unknown as FeatureCollection<Geometry>;
const graticule = geoGraticule10();

// d3 wants clockwise outer rings; GeoJSON files are usually counter-clockwise, which d3 reads as "the whole globe but this"
const rewind = (g: Geometry): Geometry => {
  if (g.type === "GeometryCollection") return { ...g, geometries: g.geometries.map(rewind) };
  if (g.type !== "Polygon" && g.type !== "MultiPolygon") return g;
  if (geoArea(g) <= 2 * Math.PI) return g;
  return g.type === "Polygon"
    ? { ...g, coordinates: g.coordinates.map((r) => [...r].reverse()) }
    : { ...g, coordinates: g.coordinates.map((p) => p.map((r) => [...r].reverse())) };
};

const host = (url: string) => { try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return ""; } };

export const HistoryMap = ({ title, period, points, route, zoom, map_source, region, region_source, region_dates, accent, font }: HistoryMapProps) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const family = useFont(font);
  const pts = points?.length ? points : [{ label: title, lat: 0, lon: 0 }];
  const lat = pts.reduce((s, p) => s + p.lat, 0) / pts.length;
  const lon = pts.reduce((s, p) => s + p.lon, 0) / pts.length;
  // several places: fit them to the lens; one place: the zoom asked for
  const far = Math.max(...pts.map((p) => geoDistance([lon, lat], [p.lon, p.lat])));
  const k = far > 0 ? Math.max(1, Math.min(40, 0.6 / Math.sin(Math.min(far, Math.PI / 2)))) : ZOOM[zoom] ?? 5.5;
  const shape = useMemo(() => (region ? rewind(region) : null), [region]);

  const lens = spring({ frame, fps, config: { damping: 14, stiffness: 150 } });
  const exit = interpolate(frame, [durationInFrames - 8, durationInFrames], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.in(Easing.cubic) });
  const dive = interpolate(frame, [0, 36], [0, 1], { extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });  // regional to local
  const projection = geoOrthographic()
    .translate([CX, CY])
    .scale(R * 0.96 * (k / 2.5 + (k - k / 2.5) * dive))
    .rotate([-lon, -lat])
    .clipAngle(90);
  const path = geoPath(projection);
  const fill = interpolate(frame, [30, 46], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const draw = interpolate(frame, [42, 72], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.quad) });
  const line = route !== "none" && pts.length > 1 ? path({ type: "LineString", coordinates: pts.map((p) => [p.lon, p.lat]) }) ?? "" : "";
  const tag = spring({ frame: frame - 20, fps, config: { damping: 15, stiffness: 160 } });
  const credit = [map_source, region ? `Region ${region_dates} · ${host(region_source)}` : ""].filter(Boolean).join("  |  ");

  return (
    <AbsoluteFill style={{ opacity: 1 - exit, fontFamily: family }}>
      {period && (
        <div style={{ position: "absolute", left: 0, right: 0, top: CY - R - 110, display: "flex", justifyContent: "center", opacity: Math.min(tag, 1) }}>
          <div style={{ padding: "8px 26px", borderRadius: 12, background: accent, color: INK, fontSize: 44, fontWeight: 900, letterSpacing: 3 }}>
            {period.toUpperCase()}
          </div>
        </div>
      )}
      <svg width={1080} height={1920} style={{ position: "absolute", transform: `scale(${0.7 + 0.3 * lens})`, transformOrigin: `${CX}px ${CY}px`, opacity: lens }}>
        <defs>
          <clipPath id="hlens"><circle cx={CX} cy={CY} r={R} /></clipPath>
          <radialGradient id="hsea" cx="45%" cy="40%"><stop offset="0%" stopColor="#1E293B" /><stop offset="100%" stopColor="#0F172A" /></radialGradient>
          <marker id="harrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M0 0 L10 5 L0 10 Z" fill={accent} opacity={draw >= 1 ? 1 : 0} />
          </marker>
        </defs>
        <g clipPath="url(#hlens)">
          <rect x={CX - R} y={CY - R} width={2 * R} height={2 * R} fill={INK} />
          <path d={path({ type: "Sphere" }) ?? ""} fill="url(#hsea)" />
          <path d={path(graticule) ?? ""} fill="none" stroke={SLATE} strokeOpacity={0.08} strokeWidth={1.2} />
          <path d={path(countries) ?? ""} fill="#57534E" stroke="#D6D3D1" strokeOpacity={0.35} strokeWidth={1.2} />
          {shape && <path d={path(shape) ?? ""} fill={accent} fillOpacity={0.35 * fill} stroke={accent} strokeOpacity={fill} strokeWidth={3} strokeDasharray="10 6" />}
          {line && <path d={line} pathLength={1} fill="none" stroke={accent} strokeWidth={7} strokeLinecap="round"
            strokeDasharray="1 1" strokeDashoffset={1 - draw} markerEnd="url(#harrow)" />}
        </g>
        <circle cx={CX} cy={CY} r={R} fill="none" stroke={accent} strokeWidth={4} />
        {pts.map((p, i) => {
          const xy = projection([p.lon, p.lat]);
          const pop = spring({ frame: frame - 34 - 6 * i, fps, config: { damping: 10, stiffness: 200 } });
          if (!xy || pop < 0.01) return null;
          const left = xy[0] > CX + 120;
          return (
            <g key={i} opacity={Math.min(pop * 2, 1)}>
              <circle cx={xy[0]} cy={xy[1]} r={13 * pop} fill={accent} stroke={INK} strokeWidth={4} />
              <text x={xy[0] + (left ? -24 : 24)} y={xy[1] + 12} textAnchor={left ? "end" : "start"} fontSize={36} fontWeight={800}
                fill={SLATE} stroke={INK} strokeWidth={8} paintOrder="stroke" style={{ fontFamily: family }}>{p.label}</text>
            </g>
          );
        })}
      </svg>
      <div style={{ position: "absolute", left: 0, right: 0, top: CY + R + 26, display: "flex", flexDirection: "column", alignItems: "center", gap: 12,
        opacity: Math.min(tag, 1), transform: `translateY(${(1 - tag) * 30}px)` }}>
        <div style={{ padding: "12px 32px", borderRadius: 999, background: "rgba(2, 6, 23, 0.86)", border: `3px solid ${accent}`, color: SLATE,
          fontSize: 48, fontWeight: 900, letterSpacing: 2, whiteSpace: "nowrap", maxWidth: 860, overflow: "hidden", textOverflow: "ellipsis" }}>
          {title.toUpperCase()}
        </div>
        {credit && <div style={{ color: SLATE, opacity: 0.8, fontSize: 22, maxWidth: 900, textAlign: "center", textShadow: `0 2px 6px ${INK}` }}>{credit}</div>}
      </div>
    </AbsoluteFill>
  );
};
