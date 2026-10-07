import { PanelLeft, Smartphone } from "lucide-react";
import Link from "next/link";
import type { Options } from "@/lib/api";
import { IconButton } from "./ui";

function Status({ ok, warn, children, title }: { ok: boolean; warn?: boolean; children: string; title?: string }) {
  return (
    <span title={title} className="hidden items-center gap-1.5 text-[12.5px] text-ink-soft md:inline-flex">
      <span className={`size-1.5 rounded-full ${ok ? "bg-ok" : warn ? "bg-warn" : "bg-danger"}`} />
      {children}
    </span>
  );
}

export function TopBar({
  options,
  onOpenLibrary,
  onOpenPreview,
  showPreviewButton,
}: {
  options: Options | null;
  onOpenLibrary: () => void;
  onOpenPreview: () => void;
  showPreviewButton: boolean;
}) {
  const keys = options?.keys;
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-panel px-3 sm:px-4">
      <IconButton label="Open library" onClick={onOpenLibrary} className="lg:hidden">
        <PanelLeft className="size-5" />
      </IconButton>
      <Link href="/" className="inline-flex items-center font-display text-lg leading-none font-extrabold tracking-tight text-ink no-underline" aria-label="Shorts Studio home">
        <span aria-hidden="true" className="mr-2 h-[22px] w-3 rounded-[3px] bg-ink shadow-[inset_0_-6px_0_var(--color-caption)]" />
        Shorts
        <span className="ml-1 rounded-[2px] bg-caption px-1 py-0.5">Studio</span>
      </Link>
      <div className="ml-auto flex items-center gap-4">
        {keys && (
          <>
            <Status ok={keys.anthropic} title={keys.anthropic ? "Claude writes, translates and imports scripts" : "Add ANTHROPIC_API_KEY to .env and restart the engine"}>
              {keys.anthropic ? "Claude connected" : "Claude not connected"}
            </Status>
            <Status ok={!!keys.stock} warn title={keys.stock ? "Stock footage search is on" : "Add a free PIXABAY_API_KEY to .env for real footage"}>
              {keys.stock ? `Footage: ${keys.stock === "pixabay" ? "Pixabay" : "Pexels"}` : "Footage: gradients only"}
            </Status>
          </>
        )}
        {showPreviewButton && (
          <IconButton label="Open preview" onClick={onOpenPreview} className="wide:hidden">
            <Smartphone className="size-5" />
          </IconButton>
        )}
      </div>
    </header>
  );
}
