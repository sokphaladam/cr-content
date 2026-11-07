import { Composition } from "remotion";
import { Fact, type FactProps } from "./Fact";
import { HistoryMap, type HistoryMapProps } from "./HistoryMap";
import { MapZoom, type MapProps } from "./MapZoom";
import { placed } from "./Placed";
import { SizeCompare, type SizeProps } from "./SizeCompare";
import { Callout, DocumentExcerpt, KineticTitle, LowerThird, Process, SplitCompare, Spotlight, Timeline } from "./Templates";

// One composition per graphic. Each renders as a short transparent clip that ffmpeg lays over the Short
// (crcontent/shorts/motion.py), so only the frames a graphic is on screen get rendered. Every one is wrapped in
// placed(): position, scale, rotation, opacity and entry/exit presets from the editor (none of them = as before).
const length = ({ props }: { props: Record<string, unknown> }) =>
  ({ durationInFrames: Math.max(12, Math.round(Number(props.seconds ?? 2) * 30)) });
const frame = { width: 1080, height: 1920, fps: 30, durationInFrames: 75, calculateMetadata: length };
const accent = "#FACC15";

export const Root = () => (
  <>
    <Composition id="Fact" component={placed(Fact)} {...frame} durationInFrames={60}
      defaultProps={{ shown: "400", value: 400, unit: "YEARS", y: 576, font: "", accent, seconds: 2 } as FactProps} />
    <Composition id="SizeCompare" component={placed(SizeCompare)} {...frame} durationInFrames={100}
      defaultProps={{ metres: 6, shown: "6", unit: "METRES", photo: "", font: "", seconds: 3.4 } as SizeProps} />
    <Composition id="MapZoom" component={placed(MapZoom)} {...frame} durationInFrames={96}
      defaultProps={{ lat: 72, lon: -40, place: "Greenland", zoom: "country", font: "", seconds: 3.2 } as MapProps} />
    <Composition id="HistoryMap" component={placed(HistoryMap)} {...frame} durationInFrames={135}
      defaultProps={{ title: "Angkor", period: "c. 1200 CE", points: [{ label: "Angkor Thom", lat: 13.44, lon: 103.86 }, { label: "Phnom Kulen", lat: 13.56, lon: 104.11 }],
        route: "through_the_places", zoom: "region", map_source: "Natural Earth (modern borders)", region: null, region_source: "", region_dates: "",
        accent, font: "", seconds: 4.5 } as HistoryMapProps} />

    <Composition id="KineticTitle" component={placed(KineticTitle)} {...frame}
      defaultProps={{ text: "WAIT FOR IT", style: "bold" as const, accent, font: "", seconds: 2.5 }} />
    <Composition id="Callout" component={placed(Callout)} {...frame}
      defaultProps={{ shape: "circle" as const, label: "LOOK HERE", size: 180, accent, font: "", seconds: 2.5 }} />
    <Composition id="LowerThird" component={placed(LowerThird)} {...frame}
      defaultProps={{ title: "Common octopus", subtitle: "Octopus vulgaris", accent, font: "", seconds: 3 }} />
    <Composition id="Spotlight" component={placed(Spotlight)} {...frame}
      defaultProps={{ photo: "", spot_x: 0.5, spot_y: 0.45, radius: 0.22, dim: 0.7, label: "", accent, font: "", seconds: 2 }} />
    <Composition id="SplitCompare" component={placed(SplitCompare)} {...frame}
      defaultProps={{ title: "", left_label: "Octopus", left_value: "3", right_label: "Human", right_value: "1", accent, font: "", seconds: 3 }} />
    <Composition id="Process" component={placed(Process)} {...frame}
      defaultProps={{ title: "How it works", steps: "Bend the wire; Hook the food; Pull it out", accent, font: "", seconds: 3.5 }} />
    <Composition id="Timeline" component={placed(Timeline)} {...frame}
      defaultProps={{ title: "", events: "802: Jayavarman II crowned; 1113: Angkor Wat begun", source: "", accent, font: "", seconds: 4 }} />

    <Composition id="DocumentExcerpt" component={placed(DocumentExcerpt)} {...frame}
      defaultProps={{ quote: "The walls are of stone, and very high.", source: "Zhou Daguan, The Customs of Cambodia", date: "1297", accent, font: "", seconds: 4 }} />

  </>
);
