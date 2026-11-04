import type { QualityCheck } from "./api";

type Fixable = {
  captions: object;
  scenes: { uid: string; texts?: { text: string }[] }[];
};

/** `draft` with the pre-render finding `check`'s safe fix applied (the same draft when it has none). `kept`: the
 *  scenes the check's `scene` index counts (the ones toScript() renders); the fix's `text` counts non-empty overlays,
 *  as toScript() sends them. Pure, so the editor applies it with one setDraft: one undo step. */
export function applyFix<D extends Fixable>(draft: D, check: QualityCheck, kept: { uid: string }[]): D {
  const { fix, scene } = check;
  if (!fix) return draft;
  const uid = scene !== undefined ? kept[scene]?.uid : undefined;
  return {
    ...draft,
    captions: fix.captions ? { ...draft.captions, ...fix.captions } : draft.captions,
    scenes: draft.scenes.map((s) => {
      if (fix.text === undefined || !fix.set || s.uid !== uid || !s.texts) return s;
      let k = -1;
      return { ...s, texts: s.texts.map((t) => (t.text.trim() && ++k === fix.text ? { ...t, ...fix.set } : t)) };
    }),
  };
}
