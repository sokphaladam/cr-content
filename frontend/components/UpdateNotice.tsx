"use client";

import { Download, X } from "lucide-react";
import { useEffect, useState } from "react";
import { dismiss, dismissed, install, startUpdates, useUpdates } from "@/lib/updates";
import { Button, IconButton } from "./ui";

const mb = (bytes: number) => (bytes / 1e6).toFixed(1);

/** Desktop app: a new version on GitHub, with its notes, installed with one click (the app restarts). */
export function UpdateNotice() {
  const u = useUpdates();
  const [hidden, setHidden] = useState(false);
  const [notes, setNotes] = useState(false);
  useEffect(startUpdates, []);

  const busy = u.status === "downloading" || u.status === "installing";
  const failed = u.installFailed && u.status !== "available"; // a failed check (offline, say) only shows in Settings
  if (!u.update || hidden || (!busy && !failed && (u.status !== "available" || dismissed(u.update.version)))) return null;
  const pct = u.progress?.total ? Math.min(100, (u.progress.downloaded / u.progress.total) * 100) : 0;

  return (
    <section
      aria-label="Update available"
      className="popover fixed bottom-4 left-4 z-40 grid w-[min(360px,calc(100vw-32px))] gap-3 p-4 lg:left-20"
    >
      <div className="flex items-start gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-cobalt-soft text-cobalt">
          <Download className="size-4" />
        </span>
        <div className="grid min-w-0 flex-1 gap-0.5">
          <span className="text-md font-semibold">Shorts Studio {u.update.version} is available</span>
          <span className="text-sm text-ink-soft">
            You have {u.update.current}.{" "}
            {u.update.notes && (
              <button type="button" className="cursor-pointer border-0 bg-transparent p-0 font-semibold text-cobalt" onClick={() => setNotes((n) => !n)}>
                {notes ? "Hide what's new" : "What's new"}
              </button>
            )}
          </span>
        </div>
        {!busy && (
          <IconButton
            label="Later"
            onClick={() => {
              dismiss(u.update!.version);
              setHidden(true);
            }}
          >
            <X className="size-4" />
          </IconButton>
        )}
      </div>
      {notes && <p className="well m-0 max-h-48 overflow-y-auto p-3 text-sm whitespace-pre-line">{u.update.notes}</p>}
      {busy ? (
        <div className="grid gap-1">
          <div role="progressbar" aria-label="Downloading the update" aria-valuenow={Math.round(pct)} className="h-1.5 overflow-hidden rounded-full bg-ink/[0.08]">
            <div className={`h-full rounded-full bg-cobalt transition-[width] ${u.progress?.total ? "" : "w-1/3 animate-pulse"}`} style={u.progress?.total ? { width: `${pct}%` } : undefined} />
          </div>
          <span className="text-sm text-ink-soft tabular-nums">
            {u.status === "installing"
              ? "Installing… Shorts Studio restarts in a moment."
              : u.progress?.total
                ? `Downloading ${mb(u.progress.downloaded)} of ${mb(u.progress.total)} MB`
                : "Downloading…"}
          </span>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <Button size="sm" variant="primary" onClick={() => void install()}>
            {failed ? "Try again" : "Install and restart"}
          </Button>
          <span className="text-sm text-ink-soft">Scheduled uploads pause for a moment.</span>
        </div>
      )}
      {failed && <p className="m-0 text-sm text-danger">{u.error}</p>}
    </section>
  );
}
