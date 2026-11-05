// node --test: the timeline clip edits (M4)
import assert from "node:assert/strict";
import { test } from "node:test";
import type { Clip } from "./api.ts";
import { audible, duplicate, duplicateIn, makeClip, moveTo, newId, replace, snap, snapTargets, split, splitAt, trimEnd, trimStart } from "./clips.ts";

const sound = (over: Partial<Clip> = {}) => makeClip([], "sfx", 2, { sound: "impact", duration: 1, ...over });

test("new clips get unique ids and sensible lengths", () => {
  const a = makeClip([], "graphics", 1.234);
  assert.equal(a.id, "clip-1");
  assert.equal(a.start, 1.23);
  assert.equal(a.duration, 3);
  const b = makeClip([a, { ...a, id: "clip-2" }], "sfx", 0);
  assert.equal(b.id, "clip-3");
  assert.equal(newId([]), "clip-1");
});

test("snap sticks to the nearest target within the tolerance", () => {
  assert.equal(snap(4.93, [5, 10], 0.1), 5);
  assert.equal(snap(4.7, [5, 10], 0.1), 4.7);
  assert.equal(snap(5.04, [4.98, 5.05], 0.1), 5.05);
  const clips = [sound(), { ...sound(), id: "o", start: 6 }];
  assert.deepEqual(snapTargets(clips, "clip-1", [0.5]), [0.5, 6, 7]);
});

test("moving snaps by either edge and never goes before 0", () => {
  const c = sound();
  assert.equal(moveTo(c, 4.95, [5], 0.1).start, 5); // start onto 5
  assert.equal(moveTo(c, 3.96, [5], 0.1).start, 4); // end onto 5
  assert.equal(moveTo(c, -3, [], 0.1).start, 0);
});

test("trimming the head moves into the sound; the tail stops at the file's end", () => {
  const c = sound({ start: 2, duration: 1, source_in: 0.2 });
  const t = trimStart(c, 2.5);
  assert.deepEqual([t.start, t.duration, t.source_in], [2.5, 0.5, 0.7]);
  assert.equal(trimStart(c, 1).start, 1.8); // only 0.2 s of sound before it
  assert.equal(trimStart(c, 9).duration, 0.1); // never shorter than MIN_LEN
  assert.equal(trimEnd(c, 9, 1.5).duration, 1.3); // 1.5 s file, starting 0.2 s in
  const g = makeClip([], "graphics", 1);
  assert.equal(trimEnd(g, 9).duration, 8); // a graphic can be as long as you like
  assert.equal(trimStart(g, 0).source_in, 0);
});

test("split carries the sound on and keeps fades on the outer ends", () => {
  const c = sound({ start: 2, duration: 2, source_in: 0.5, fade_in: 0.3, fade_out: 0.4 });
  const [a, b] = split(c, 3, "clip-9")!;
  assert.deepEqual([a.start, a.duration, a.fade_in, a.fade_out], [2, 1, 0.3, 0]);
  assert.deepEqual([b.id, b.start, b.duration, b.source_in, b.fade_in, b.fade_out], ["clip-9", 3, 1, 1.5, 0, 0.4]);
  assert.equal(split(c, 2.05, "x"), null); // too close to an edge
  assert.equal(split(c, 5, "x"), null);
});

test("duplicate and replace", () => {
  const c = makeClip([], "graphics", 1, { template: "Fact", props: { shown: "3" } });
  const d = duplicate(c, [c]);
  assert.deepEqual([d.id, d.start], ["clip-2", 4]);
  d.props.shown = "9";
  assert.equal(c.props.shown, "3"); // props copied, not shared
  assert.deepEqual(replace([c, d], c.id, () => []).map((x) => x.id), ["clip-2"]);
  assert.deepEqual(replace([c], c.id, (x) => split(x, 2, "s")!).map((x) => x.id), ["clip-1", "s"]);
});

test("solo and mute decide what the preview plays", () => {
  assert.equal(audible({}, "sfx"), true);
  assert.equal(audible({ sfx: { mute: true, solo: false, volume: 1, locked: false, hidden: false } }, "sfx"), false);
  const soloVoice = { voice: { mute: false, solo: true, volume: 1, locked: false, hidden: false } };
  assert.equal(audible(soloVoice, "voice"), true);
  assert.equal(audible(soloVoice, "music"), false);
});

test("array-level split and duplicate", () => {
  const c = makeClip([], "sfx", 0, { duration: 2 });
  assert.deepEqual(splitAt([c], c.id, 1).map((x) => [x.id, x.start]), [["clip-1", 0], ["clip-2", 1]]);
  assert.equal(splitAt([c], c.id, 5).length, 1);
  assert.equal(splitAt([c], "missing", 1).length, 1);
  assert.deepEqual(duplicateIn([c], c.id).map((x) => x.start), [0, 2]);
  // after a split, the copy of the first half skips past the second half instead of covering it
  const halves = splitAt([c], c.id, 1);
  assert.deepEqual(duplicateIn(halves, "clip-1").map((x) => x.start), [0, 1, 2]);
  const other = makeClip([], "graphics", 2, { id: "g", duration: 5 });
  assert.equal(duplicateIn([c, other], c.id)[2].start, 2); // another lane's clip doesn't count
});
