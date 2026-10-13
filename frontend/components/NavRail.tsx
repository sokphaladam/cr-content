"use client";

import { FolderOpen, Megaphone, Plus, Settings, Smartphone } from "lucide-react";
import type { ReactNode } from "react";
import type { Options } from "@/lib/api";

export type AppView = "studio" | "campaigns" | "settings";

function RailButton({
  label,
  active,
  onClick,
  className = "",
  children,
}: {
  label: string;
  active?: boolean; // only for buttons that switch a view or panel
  onClick: () => void;
  className?: string;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`${className} group relative grid w-full cursor-pointer justify-items-center gap-1 border-0 bg-transparent py-2 text-[10.5px] font-semibold transition-colors ${
        active ? "text-white" : "text-rail-ink hover:text-white"
      }`}
    >
      {/* the caption yellow marks where you are, like the word being spoken */}
      <span aria-hidden className={`absolute top-2 bottom-2 left-0 w-[3px] rounded-r bg-caption transition-opacity ${active ? "opacity-100" : "opacity-0"}`} />
      <span className={`grid size-9 place-items-center rounded-lg transition-colors ${active ? "bg-white/[0.1]" : "group-hover:bg-white/[0.06]"}`}>{children}</span>
      {label}
    </button>
  );
}

/** The dark frame on the left (from laptop width): create, library, settings, and whether the services are ready. */
export function NavRail({
  view,
  libraryOpen,
  options,
  onNew,
  onLibrary,
  onSettings,
  onCampaigns,
  onPreview,
}: {
  view: AppView;
  libraryOpen: boolean;
  options: Options | null;
  onNew: () => void;
  onLibrary: () => void;
  onSettings: () => void;
  onCampaigns: () => void;
  onPreview?: () => void; // below wide screens the preview is a slide-over
}) {
  const keys = options?.keys;
  const missing = keys ? [!keys.anthropic && "Claude", !keys.stock && "stock footage"].filter(Boolean) : [];
  return (
    <nav aria-label="App" className="flex h-full w-16 flex-col items-center bg-rail pt-3 pb-3">
      <span aria-label="Shorts Studio" title="Shorts Studio" className="mb-4 grid size-9 place-items-center rounded-lg bg-white/[0.06]">
        <span aria-hidden className="h-5 w-2.5 rounded-[3px] bg-white shadow-[inset_0_-6px_0_var(--color-caption)]" />
      </span>
      <div className="grid w-full gap-1">
        <RailButton label="New" onClick={onNew}>
          <Plus className="size-5" />
        </RailButton>
        <RailButton label="Library" active={view === "studio" && libraryOpen} onClick={onLibrary}>
          <FolderOpen className="size-5" />
        </RailButton>
        <RailButton label="Campaigns" active={view === "campaigns"} onClick={onCampaigns}>
          <Megaphone className="size-5" />
        </RailButton>
        {onPreview && (
          <RailButton label="Preview" onClick={onPreview} className="wide:hidden">
            <Smartphone className="size-5" />
          </RailButton>
        )}
      </div>
      <div className="mt-auto grid w-full gap-1">
        <RailButton label="Settings" active={view === "settings"} onClick={onSettings}>
          <span className="relative">
            <Settings className="size-5" />
            {keys && missing.length > 0 && (
              <span aria-hidden className="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-caption ring-2 ring-rail" />
            )}
          </span>
        </RailButton>
        {keys && (
          <span
            className="mx-auto mt-1 flex items-center gap-1 text-[10px] text-rail-ink"
            title={missing.length ? `Not set up yet: ${missing.join(", ")}. Open Settings.` : "Claude and stock footage are ready"}
          >
            <span className={`size-1.5 rounded-full ${missing.length ? "bg-caption" : "bg-ok"}`} />
            {missing.length ? "Setup" : "Ready"}
          </span>
        )}
      </div>
    </nav>
  );
}
