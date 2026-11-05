import type { TemplateDef, TemplateField } from "./api";

/** A graphics template's defaults: what a new graphic of it starts with. */
export function templateDefaults(def: TemplateDef | undefined): Record<string, string | number> {
  return Object.fromEntries((def?.fields ?? []).map((f) => [f.key, f.default]));
}

/** What's wrong with one field's value, in plain words ("" = fine). The same checks as
 *  crcontent/graphic_templates.py validate(), so the editor shows them before the render would refuse. */
export function fieldError(f: TemplateField, value: string | number | undefined): string {
  const v = value ?? f.default;
  if (f.type === "number") {
    const n = typeof v === "number" ? v : Number(v);
    if (v === "" || !Number.isFinite(n)) return "Not a number.";
    if ((f.min !== undefined && n < f.min) || (f.max !== undefined && n > f.max)) return `Between ${f.min} and ${f.max}.`;
  } else if (f.type === "choice") {
    if (!f.options?.includes(String(v))) return `One of ${f.options?.join(", ")}.`;
  } else if (f.type === "color") {
    if (!/^#[0-9A-Fa-f]{6}$/.test(String(v))) return "A colour like #FACC15.";
  } else {
    const s = String(v);
    if (f.required && !s.trim()) return "Needed.";
    if (f.max_len !== undefined && s.length > f.max_len) return `${s.length} characters, at most ${f.max_len}.`;
  }
  return "";
}

/** Every field's problem, keyed by field ({} = the graphic can render). */
export function templateErrors(def: TemplateDef | undefined, props: Record<string, string | number>): Record<string, string> {
  if (!def) return { template: "Unknown template." };
  return Object.fromEntries(def.fields.map((f) => [f.key, fieldError(f, props[f.key])]).filter(([, e]) => e));
}
