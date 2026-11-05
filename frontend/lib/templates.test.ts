// node --test: graphics template defaults and checks (M5), mirroring crcontent/graphic_templates.py
import assert from "node:assert/strict";
import { test } from "node:test";
import type { TemplateDef } from "./api.ts";
import { fieldError, templateDefaults, templateErrors } from "./templates.ts";

const def: TemplateDef = {
  version: 1,
  label: "Lower third",
  description: "",
  seconds: 3,
  fields: [
    { key: "title", type: "text", label: "Title", default: "Raven", group: "content", max_len: 10, required: true },
    { key: "accent", type: "color", label: "Accent", default: "#FACC15", group: "style" },
    { key: "scale", type: "number", label: "Scale", default: 1, group: "position", min: 0.2, max: 3 },
    { key: "enter", type: "choice", label: "In", default: "pop", group: "motion", options: ["none", "pop"] },
  ],
};

test("defaults come from the definition", () => {
  assert.deepEqual(templateDefaults(def), { title: "Raven", accent: "#FACC15", scale: 1, enter: "pop" });
  assert.deepEqual(templateDefaults(undefined), {});
});

test("each kind of field is checked like the engine checks it", () => {
  assert.equal(fieldError(def.fields[0], ""), "Needed.");
  assert.equal(fieldError(def.fields[0], "x".repeat(11)), "11 characters, at most 10.");
  assert.equal(fieldError(def.fields[1], "yellow"), "A colour like #FACC15.");
  assert.equal(fieldError(def.fields[2], 9), "Between 0.2 and 3.");
  assert.equal(fieldError(def.fields[2], ""), "Not a number.");
  assert.equal(fieldError(def.fields[3], "spin"), "One of none, pop.");
  assert.equal(fieldError(def.fields[0], undefined), ""); // a missing prop takes its default
});

test("errors for a whole graphic", () => {
  assert.deepEqual(templateErrors(def, templateDefaults(def)), {});
  assert.deepEqual(Object.keys(templateErrors(def, { title: "", scale: 5 })), ["title", "scale"]);
  assert.deepEqual(templateErrors(undefined, {}), { template: "Unknown template." });
});
