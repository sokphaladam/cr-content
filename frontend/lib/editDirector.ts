import type { Clip, EditPlan, Scene, TrackName, TrackState } from "./api";
import { makeClip, trackOf } from "./clips.ts"; // .ts: node --test loads it as is

type Editable = {
  scenes: (Scene & { uid: string })[];
  clips: Clip[];
  tracks: Partial<Record<TrackName, TrackState>>;
};

/** The draft with the picked Edit Director decisions applied, as one edit. Its earlier clips (origin "director")
 *  are replaced, except on a locked lane; clips the creator made or changed are never touched. Calm scenes it set
 *  ("auto") are set again from the picks; a scene the creator set calm on or off keeps that.
 *  keptUids: the uids of the scenes the render keeps, in order (the decisions' scene numbers count those). */
export function applyEdits<T extends Editable>(d: T, plan: EditPlan, picked: Set<string>, keptUids: string[]): { draft: T; skipped: number } {
  let skipped = 0;
  let clips = d.clips.filter((c) => c.origin !== "director" || trackOf(d.tracks, c.track).locked);
  const calm = new Map<string, string>();
  for (const dec of plan.decisions) {
    if (!picked.has(dec.id)) continue;
    if (dec.kind === "calm") {
      const uid = keptUids[dec.scene];
      if (uid) calm.set(uid, dec.reason);
    } else if (dec.clip?.track) {
      if (trackOf(d.tracks, dec.clip.track).locked) {
        skipped += 1;
        continue;
      }
      clips = [...clips, makeClip(clips, dec.clip.track, dec.clip.start ?? 0, { ...dec.clip, origin: "director" })];
    }
  }
  const scenes = d.scenes.map((s) => {
    if (s.calm === "on" || s.calm === "off") return s;
    const note = calm.get(s.uid);
    return note ? { ...s, calm: "auto" as const, calm_note: note } : s.calm === "auto" ? { ...s, calm: "" as const, calm_note: "" } : s;
  });
  return { draft: { ...d, scenes, clips }, skipped };
}
