// node --test (Node 22 strips the types): no test framework needed for the pure editor logic
import assert from "node:assert/strict";
import { test } from "node:test";
import type { QualityCheck } from "./api.ts";
import { DraftHistory } from "./draftHistory.ts";
import { applyFix } from "./qualityFix.ts";

const check = (over: Partial<QualityCheck>): QualityCheck => ({
  id: "x", stage: "preview", category: "captions", severity: "medium", status: "warning", title: "t", description: "",
  detector: "x", ...over,
});
const draft = () => ({
  title: "T",
  captions: { y: 0.2, headline_y: 0.13, size: 1 },
  scenes: [
    { uid: "a", texts: [{ text: "keep", y: 0.2 }] },
    { uid: "empty", texts: [] }, // not rendered: kept scenes skip it
    { uid: "b", texts: [{ text: " ", y: 0.5 }, { text: "WOW", y: 0.2, at: 9 }] },
  ],
});
const kept = [{ uid: "a" }, { uid: "b" }];

test("a captions fix changes only the caption style", () => {
  const d = draft();
  const out = applyFix(d, check({ fix: { label: "Move", captions: { y: 0.62 } } }), kept);
  assert.deepEqual(out.captions, { y: 0.62, headline_y: 0.13, size: 1 });
  assert.deepEqual(out.scenes, d.scenes);
});

test("a text fix finds the scene by its kept index and the overlay by its non-empty index", () => {
  const out = applyFix(draft(), check({ scene: 1, fix: { label: "Move", text: 0, set: { y: 0.4, at: 0 } } }), kept);
  assert.deepEqual(out.scenes[2].texts, [{ text: " ", y: 0.5 }, { text: "WOW", y: 0.4, at: 0 }]);
  assert.deepEqual(out.scenes[0].texts, [{ text: "keep", y: 0.2 }]); // scene 0's overlay is left alone
});

test("no fix: the same draft back", () => {
  const d = draft();
  assert.equal(applyFix(d, check({}), kept), d);
});

test("an applied fix is one undo step", () => {
  const history = new DraftHistory<ReturnType<typeof draft>>();
  const before = draft();
  history.record(before);
  const after = applyFix(before, check({ fix: { label: "Move", captions: { y: 0.62 } } }), kept);
  assert.equal(history.undo(after), before);
});
