// node --test: applying the Edit Director's decisions (M7)
import assert from "node:assert/strict";
import { test } from "node:test";
import type { Clip, EditPlan } from "./api.ts";
import { makeClip, replace } from "./clips.ts";
import { applyEdits } from "./editDirector.ts";

const scene = (uid: string, calm: "" | "auto" | "on" | "off" = "") => ({ uid, narration: "x", visual_query: "", on_screen_text: "", media: "", calm, calm_note: "" });
const plan: EditPlan = {
  gaps: [],
  notes: [],
  sound_source: "rules",
  decisions: [
    { id: "d1", kind: "calm", scene: 1, reason: "An explanation.", essential: false },
    { id: "d2", kind: "calm", scene: 2, reason: "Payoff held.", essential: true },
    { id: "d3", kind: "graphic", scene: 0, reason: "Names it.", essential: false, clip: { track: "graphics", template: "LowerThird", start: 1, duration: 3, props: { title: "Crow" } } },
    { id: "d4", kind: "sound", scene: 2, reason: "Payoff.", essential: true, clip: { track: "sfx", sound: "chime", start: 9, duration: 1.6 } },
  ],
};
const mine = makeClip([], "sfx", 2, { id: "mine", sound: "impact" });
const oldDirector: Clip = { ...makeClip([mine], "graphics", 5, { template: "Fact" }), origin: "director" };
const edited: Clip = { ...makeClip([mine, oldDirector], "sfx", 7, { sound: "whoosh" }), origin: "edited" };
const draft = () => ({ scenes: [scene("a"), scene("b", "auto"), scene("c", "off")], clips: [mine, oldDirector, edited], tracks: {} });

test("picked decisions are applied; earlier director clips replaced, the creator's kept", () => {
  const { draft: out, skipped } = applyEdits(draft(), plan, new Set(["d1", "d2", "d3", "d4"]), ["a", "b", "c"]);
  assert.equal(skipped, 0);
  assert.deepEqual(out.clips.map((c) => [c.track, c.origin ?? ""]), [["sfx", ""], ["sfx", "edited"], ["graphics", "director"], ["sfx", "director"]]);
  assert.equal(new Set(out.clips.map((c) => c.id)).size, out.clips.length); // ids stay unique
  assert.deepEqual(out.scenes.map((s) => s.calm), ["", "auto", "off"]); // the creator's "off" stands
  assert.equal(out.scenes[1].calm_note, "An explanation.");
});

test("unpicked calm is cleared; a locked lane keeps its clips and gets none", () => {
  const locked = { ...draft(), tracks: { graphics: { mute: false, solo: false, volume: 1, locked: true, hidden: false } } };
  const { draft: out, skipped } = applyEdits(locked, plan, new Set(["d3", "d4"]), ["a", "b", "c"]);
  assert.equal(skipped, 1);
  assert.ok(out.clips.some((c) => c.id === oldDirector.id)); // kept: its lane is locked
  assert.deepEqual(out.scenes.map((s) => s.calm), ["", "", "off"]);
});

test("changing a director clip makes it the creator's", () => {
  const moved = replace([oldDirector], oldDirector.id, (c) => [{ ...c, start: 6 }]);
  assert.equal(moved[0].origin, "edited");
  assert.equal(replace([mine], mine.id, (c) => [{ ...c, start: 3 }])[0].origin ?? "", "");
});
