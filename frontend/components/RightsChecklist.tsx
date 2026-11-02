"use client";

import { ChevronDown, ChevronRight, FileCheck2, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Permission, type RightsAsset } from "@/lib/api";
import { Button, IconButton, useToast } from "./ui";

const TYPES: RightsAsset["type"][] = ["footage", "image", "music", "sound", "voice", "font", "other"];
const PERMS: Permission[] = ["unknown", "yes", "no"];
const documented = (a: RightsAsset) => !!(a.source.trim() && a.license.trim() && a.confirmed);

/** Your record of every asset's source and licence. Suggestions from the app are marked until you confirm them;
 *  nothing here is verified, and YouTube Studio's own copyright checks still apply. */
export function RightsChecklist({ scope, name }: { scope: "video" | "song"; name: string }) {
  const toast = useToast();
  const [items, setItems] = useState<RightsAsset[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.rights(scope, name).then((r) => setItems(r.items)).catch(() => setItems(null));
  }, [scope, name]);

  if (!items) return null; // an older engine: no checklist

  const edit = (id: string, patch: Partial<RightsAsset>) => {
    setItems(items.map((a) => (a.id === id ? { ...a, ...patch, auto: false } : a)));
    setDirty(true);
  };
  const add = () => {
    const id = `own:${Date.now()}`;
    setItems([...items, { id, name: "New asset", type: "other", source: "", license: "", attribution_required: "unknown", attribution_text: "",
      commercial: "unknown", derivatives: "unknown", restrictions: "", confirmed: false, notes: "", auto: false }]);
    setOpen(id);
    setDirty(true);
  };
  async function save() {
    setSaving(true);
    try {
      setItems((await api.saveRights(scope, name, items!)).items);
      setDirty(false);
      toast("Rights checklist saved", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }

  const done = items.filter(documented).length;
  const text = (a: RightsAsset, k: "name" | "source" | "license" | "attribution_text" | "restrictions" | "notes", label: string, long = false) => (
    <label className="grid gap-0.5">
      <span className="field-label">{label}</span>
      {long ? (
        <textarea className="field-input min-h-14 text-sm" value={a[k]} maxLength={k === "notes" ? 1000 : 500} onChange={(e) => edit(a.id, { [k]: e.target.value })} />
      ) : (
        <input className="field-input h-8 py-0 text-sm" value={a[k]} maxLength={300} onChange={(e) => edit(a.id, { [k]: e.target.value })} />
      )}
    </label>
  );
  const perm = (a: RightsAsset, k: "attribution_required" | "commercial" | "derivatives", label: string) => (
    <label className="grid gap-0.5">
      <span className="field-label">{label}</span>
      <select className="field-input h-8 py-0 text-sm" value={a[k]} onChange={(e) => edit(a.id, { [k]: e.target.value as Permission })}>
        {PERMS.map((p) => <option key={p}>{p}</option>)}
      </select>
    </label>
  );

  return (
    <section aria-label="Rights checklist" className="grid gap-3 card p-3.5">
      <div className="grid gap-1">
        <h3 className="m-0 flex items-center gap-1.5 text-base font-bold">
          <FileCheck2 className="size-4 text-cobalt" aria-hidden /> Rights checklist
        </h3>
        <p className="m-0 text-sm text-ink-soft">
          {done} of {items.length} assets <b>documented locally</b> (source, licence, confirmed by you). <b>Not verified</b>: this
          is your own record. Copyright (Content ID) and ad suitability <b>require YouTube Studio&apos;s checks</b>.
        </p>
      </div>
      <ul className="m-0 grid list-none gap-1 p-0">
        {items.map((a) => (
          <li key={a.id} className="rounded-md border border-line">
            <button type="button" onClick={() => setOpen(open === a.id ? null : a.id)} aria-expanded={open === a.id}
              className="flex w-full cursor-pointer items-center gap-1.5 px-2 py-1.5 text-left text-sm">
              {open === a.id ? <ChevronDown className="size-3.5 shrink-0" aria-hidden /> : <ChevronRight className="size-3.5 shrink-0" aria-hidden />}
              <span className="min-w-0 flex-1 truncate">{a.name}</span>
              {(a.commercial === "no" || a.derivatives === "no") && <span className="text-2xs font-semibold text-danger">Not allowed?</span>}
              <span className={`rounded px-1.5 text-2xs font-semibold ${documented(a) ? "bg-ok/10 text-ok" : a.auto ? "bg-sunken text-ink-soft" : "bg-warn/10 text-warn"}`}>
                {documented(a) ? "Documented" : a.auto ? "Suggested" : "Incomplete"}
              </span>
            </button>
            {open === a.id && (
              <div className="grid gap-2 border-t border-line p-2">
                {text(a, "name", "Asset")}
                <label className="grid gap-0.5">
                  <span className="field-label">Type</span>
                  <select className="field-input h-8 py-0 text-sm" value={a.type} onChange={(e) => edit(a.id, { type: e.target.value as RightsAsset["type"] })}>
                    {TYPES.map((t) => <option key={t}>{t}</option>)}
                  </select>
                </label>
                {text(a, "source", "Source / creator")}
                {text(a, "license", "Licence or permission")}
                <div className="grid grid-cols-3 gap-1.5">
                  {perm(a, "attribution_required", "Credit needed")}
                  {perm(a, "commercial", "Commercial use")}
                  {perm(a, "derivatives", "Adaptation")}
                </div>
                {a.attribution_required !== "no" && text(a, "attribution_text", "Credit text", true)}
                {text(a, "restrictions", "Expiry / restrictions")}
                {text(a, "notes", "Notes", true)}
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 text-sm font-semibold">
                    <input type="checkbox" className="size-4 accent-cobalt" checked={a.confirmed} onChange={(e) => edit(a.id, { confirmed: e.target.checked })} />
                    I checked this
                  </label>
                  <IconButton label={`Remove ${a.name}`} tone="danger" onClick={() => { setItems(items.filter((x) => x.id !== a.id)); setDirty(true); }}>
                    <Trash2 className="size-3.5" />
                  </IconButton>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>
      <div className="flex gap-2">
        <Button size="sm" variant="ghost" icon={<Plus className="size-3.5" />} onClick={add}>Add asset</Button>
        <Button size="sm" variant="primary" className="ml-auto" disabled={!dirty} loading={saving} onClick={save}>Save</Button>
      </div>
    </section>
  );
}
