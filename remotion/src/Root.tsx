import { Composition } from "remotion";
import { Fact, type FactProps } from "./Fact";
import { MapZoom, type MapProps } from "./MapZoom";
import { SizeCompare, type SizeProps } from "./SizeCompare";

// One composition per graphic. Each renders as a short transparent clip that ffmpeg lays over the Short
// (crcontent/shorts/motion.py), so only the frames a graphic is on screen get rendered.
const length = ({ props }: { props: Record<string, unknown> }) =>
  ({ durationInFrames: Math.max(12, Math.round(Number(props.seconds ?? 2) * 30)) });

export const Root = () => (
  <>
    <Composition id="Fact" component={Fact} width={1080} height={1920} fps={30} durationInFrames={60}
      defaultProps={{ shown: "400", value: 400, unit: "YEARS", y: 576, font: "", accent: "#FACC15", seconds: 2 } as FactProps}
      calculateMetadata={length} />
    <Composition id="SizeCompare" component={SizeCompare} width={1080} height={1920} fps={30} durationInFrames={100}
      defaultProps={{ metres: 6, shown: "6", unit: "METRES", photo: "", font: "", seconds: 3.4 } as SizeProps}
      calculateMetadata={length} />
    <Composition id="MapZoom" component={MapZoom} width={1080} height={1920} fps={30} durationInFrames={96}
      defaultProps={{ lat: 72, lon: -40, place: "Greenland", zoom: "country", font: "", seconds: 3.2 } as MapProps}
      calculateMetadata={length} />
  </>
);
