import { Megaphone, Music2, PanelLeft, Settings, Smartphone } from "lucide-react";
import { IconButton } from "./ui";

/** Header below laptop width, where the navigation rail is hidden: library, settings and preview open from here. */
export function TopBar({
  onOpenLibrary,
  onOpenSettings,
  onOpenCampaigns,
  onOpenLyricVideo,
  onOpenPreview,
  showPreviewButton,
  setupNeeded,
}: {
  onOpenLibrary: () => void;
  onOpenSettings: () => void;
  onOpenCampaigns: () => void;
  onOpenLyricVideo: () => void;
  onOpenPreview: () => void;
  showPreviewButton: boolean;
  setupNeeded: boolean;
}) {
  return (
    <header className="flex h-14 shrink-0 items-center gap-2 bg-rail px-2 text-white lg:hidden">
      <IconButton label="Open library" onClick={onOpenLibrary} tone="rail">
        <PanelLeft className="size-5" />
      </IconButton>
      <span className="inline-flex items-center gap-2 font-display text-xl font-extrabold tracking-tight">
        <span aria-hidden className="h-5 w-2.5 rounded-[3px] bg-white shadow-[inset_0_-6px_0_var(--color-caption)]" />
        Shorts Studio
      </span>
      <span className="ml-auto flex items-center gap-1">
        {showPreviewButton && (
          <IconButton label="Open preview" onClick={onOpenPreview} tone="rail" className="wide:hidden">
            <Smartphone className="size-5" />
          </IconButton>
        )}
        <IconButton label="Lyric video" onClick={onOpenLyricVideo} tone="rail">
          <Music2 className="size-5" />
        </IconButton>
        <IconButton label="Campaigns" onClick={onOpenCampaigns} tone="rail">
          <Megaphone className="size-5" />
        </IconButton>
        <IconButton label="Settings" onClick={onOpenSettings} tone="rail" className="relative">
          <Settings className="size-5" />
          {setupNeeded && <span aria-hidden className="absolute top-1.5 right-1.5 size-2 rounded-full bg-caption ring-2 ring-rail" />}
        </IconButton>
      </span>
    </header>
  );
}
