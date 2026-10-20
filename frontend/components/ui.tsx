"use client";

import { Loader2, X } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";

/* ---------- Buttons ---------- */

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-cobalt text-white border-cobalt hover:bg-cobalt-deep hover:border-cobalt-deep",
  secondary: "bg-panel text-ink border-line hover:border-line-strong hover:bg-sunken",
  ghost: "bg-transparent text-ink-soft border-transparent hover:bg-ink/[0.05] hover:text-ink",
  danger: "bg-transparent text-danger border-transparent hover:bg-danger/[0.07]",
};
const SIZES: Record<Size, string> = {
  sm: "h-8 gap-1.5 px-2.5 text-base",
  md: "h-10 gap-2 px-4 text-md",
};

export function buttonClass(variant: Variant = "secondary", size: Size = "md", extra = "") {
  return `inline-flex shrink-0 cursor-pointer items-center justify-center rounded-lg border font-semibold whitespace-nowrap no-underline transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${SIZES[size]} ${extra}`;
}

export function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  icon,
  className = "",
  children,
  disabled,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
}) {
  return (
    <button type="button" {...rest} disabled={disabled || loading} className={buttonClass(variant, size, className)}>
      {loading ? <Loader2 className={size === "sm" ? "size-3.5 animate-spin" : "size-4 animate-spin"} aria-hidden /> : icon}
      {children}
    </button>
  );
}

/** Square icon-only button; `label` is required for screen readers and shows as a tooltip. */
export function IconButton({
  label,
  children,
  className = "",
  tone = "default",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string; tone?: "default" | "danger" | "rail" }) {
  const tones = {
    default: "text-ink-soft hover:bg-ink/[0.06] hover:text-ink",
    danger: "text-ink-soft hover:bg-ink/[0.06] hover:text-danger",
    rail: "text-rail-ink hover:bg-white/[0.08] hover:text-white", // on the dark navigation rail
  };
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      {...rest}
      className={`grid size-8 shrink-0 cursor-pointer place-items-center rounded-lg transition-colors disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent ${tones[tone]} ${className}`}
    >
      {children}
    </button>
  );
}

export function Spinner({ className = "size-4" }: { className?: string }) {
  return <Loader2 className={`animate-spin ${className}`} aria-hidden />;
}

/* ---------- Form bits ---------- */

export function Field({ label, htmlFor, hint, children }: { label: ReactNode; htmlFor?: string; hint?: string; children: ReactNode }) {
  return (
    <div className="grid min-w-0 gap-1.5">
      <label className="field-label" htmlFor={htmlFor}>
        {label} {hint && <span className="font-normal text-ink-soft/80">{hint}</span>}
      </label>
      {children}
    </div>
  );
}

/* ---------- File drop ---------- */

/** Does `file` match an <input accept> list (".mp3,.wav,audio/*")? An empty list takes anything. */
export function accepts(accept: string, file: File) {
  const rules = accept.split(",").map((r) => r.trim().toLowerCase()).filter(Boolean);
  if (!rules.length) return true;
  const name = file.name.toLowerCase();
  const type = file.type.toLowerCase();
  return rules.some((r) => (r.startsWith(".") ? name.endsWith(r) : r.endsWith("/*") ? type.startsWith(r.slice(0, -1)) : type === r));
}

const hasFiles = (e: React.DragEvent | DragEvent) => !!e.dataTransfer && Array.from(e.dataTransfer.types).includes("Files");

let guarded = false;
/** A file dropped outside every drop zone would otherwise replace the whole app with that file. */
function guardWindow() {
  if (guarded || typeof window === "undefined") return;
  guarded = true;
  const stop = (e: DragEvent) => {
    if (hasFiles(e)) e.preventDefault();
  };
  window.addEventListener("dragover", stop);
  window.addEventListener("drop", stop);
}

/** Files can be dragged onto `children` as well as picked with their file input: the ones `accept` allows go to
 * `onFiles` (only the first unless `multiple`); when none fit, `onReject` says what was expected. */
export function DropZone({
  accept = "",
  multiple = false,
  disabled = false,
  onFiles,
  onReject,
  label = "Drop to add",
  className = "",
  children,
}: {
  accept?: string;
  multiple?: boolean;
  disabled?: boolean;
  onFiles: (files: File[]) => void;
  onReject?: (message: string) => void;
  label?: string;
  className?: string;
  children: ReactNode;
}) {
  const [over, setOver] = useState(false);
  const depth = useRef(0); // dragenter/dragleave fire for every child the pointer crosses
  useEffect(guardWindow, []);

  return (
    <div
      className={`relative ${className}`}
      onDragEnter={(e) => {
        if (disabled || !hasFiles(e)) return;
        e.preventDefault();
        depth.current += 1;
        setOver(true);
      }}
      onDragOver={(e) => {
        if (disabled || !hasFiles(e)) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = "copy";
      }}
      onDragLeave={() => {
        depth.current = Math.max(0, depth.current - 1);
        if (!depth.current) setOver(false);
      }}
      onDrop={(e) => {
        if (disabled || !hasFiles(e)) return;
        e.preventDefault();
        e.stopPropagation();
        depth.current = 0;
        setOver(false);
        const ok = Array.from(e.dataTransfer.files).filter((f) => accepts(accept, f));
        if (!ok.length) {
          const exts = accept.split(",").map((r) => r.trim()).filter((r) => r.startsWith("."));
          onReject?.(`That file can't be used here${exts.length ? ` (use ${exts.join(", ")})` : ""}.`);
          return;
        }
        onFiles(multiple ? ok : ok.slice(0, 1));
      }}
    >
      {children}
      {over && (
        <div className="pointer-events-none absolute inset-0 z-20 grid place-items-center rounded-xl border-2 border-dashed border-cobalt bg-cobalt/10">
          <span className="rounded-md bg-cobalt px-3 py-1.5 text-base font-semibold text-white shadow">{label}</span>
        </div>
      )}
    </div>
  );
}

/** A file field you can drop a file on or click to choose one; shows the chosen file's name. */
export function FileInput({
  id,
  accept,
  file,
  onFile,
  onReject,
  disabled = false,
}: {
  id: string;
  accept: string;
  file: string; // the chosen file's name ("" = none yet)
  onFile: (file: File) => void;
  onReject?: (message: string) => void;
  disabled?: boolean;
}) {
  return (
    <DropZone accept={accept} disabled={disabled} onFiles={(f) => onFile(f[0])} onReject={onReject} label="Drop the file">
      <div className={`flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-xl border-2 border-dashed border-line bg-sunken/50 px-4 py-4 ${disabled ? "opacity-60" : ""}`}>
        <label htmlFor={id} className={`${buttonClass("secondary", "sm")} ${disabled ? "pointer-events-none" : "cursor-pointer"}`}>
          Choose file
        </label>
        <input
          id={id}
          type="file"
          accept={accept}
          disabled={disabled}
          className="sr-only"
          onChange={(e) => {
            const f = e.target.files?.[0];
            e.target.value = ""; // choosing the same file again (after editing it) reads it again
            if (f) onFile(f);
          }}
        />
        {file ? <span className="min-w-0 truncate text-base font-semibold text-ink">{file}</span> : <span className="text-base text-ink-soft">or drag it here</span>}
      </div>
    </DropZone>
  );
}

export function Message({ text, error }: { text: string; error?: boolean }) {
  if (!text) return null;
  return (
    <p role={error ? "alert" : "status"} className={`m-0 text-base ${error ? "text-danger" : "text-ink-soft"}`}>
      {text}
    </p>
  );
}

/** Small option toggle for values (language, media type). */
export function Segmented<T extends string>({
  name,
  value,
  options,
  onChange,
  size = "md",
}: {
  name: string;
  value: T;
  options: { value: T; label: ReactNode; lang?: string }[];
  onChange: (v: T) => void;
  size?: Size;
}) {
  return (
    <div role="radiogroup" className={`inline-flex rounded-lg bg-ink/[0.06] p-0.5 ${size === "sm" ? "h-8" : "h-10"}`}>
      {options.map((o) => (
        <label key={o.value} className="relative cursor-pointer">
          <input type="radio" name={name} value={o.value} checked={value === o.value} onChange={() => onChange(o.value)} className="peer sr-only" />
          <span
            lang={o.lang}
            className={`flex h-full items-center rounded-md px-3 font-semibold text-ink-soft transition-colors peer-checked:bg-panel peer-checked:text-ink peer-checked:shadow-sm peer-focus-visible:outline-2 peer-focus-visible:outline-cobalt ${
              size === "sm" ? "text-sm" : "text-base"
            }`}
          >
            {o.label}
          </span>
        </label>
      ))}
    </div>
  );
}

/** Underlined tabs for switching views (not values). */
export function Tabs<T extends string>({
  value,
  onChange,
  items,
  label,
}: {
  value: T;
  onChange: (v: T) => void;
  items: { value: T; label: ReactNode; count?: number }[];
  label: string;
}) {
  return (
    <div role="tablist" aria-label={label} className="flex gap-5 border-b border-line">
      {items.map((it) => {
        const active = it.value === value;
        return (
          <button
            key={it.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(it.value)}
            className={`-mb-px flex cursor-pointer items-center gap-1.5 border-b-2 bg-transparent px-0.5 pt-1 pb-2.5 text-md font-semibold transition-colors ${
              active ? "border-ink text-ink" : "border-transparent text-ink-soft hover:text-ink"
            }`}
          >
            {it.label}
            {it.count !== undefined && (
              <span className={`rounded-full px-1.5 py-px text-xs leading-4 ${active ? "bg-ink text-on-ink" : "bg-ink/[0.07] text-ink-soft"}`}>
                {it.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export function Chip({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "caption" | "ink" }) {
  const t = { neutral: "bg-ink/[0.06] text-ink-soft", caption: "bg-caption text-media", ink: "bg-ink text-on-ink" }[tone];
  return <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs leading-none font-semibold ${t}`}>{children}</span>;
}

/* ---------- Toasts ---------- */

type Toast = { id: number; text: string; tone: "info" | "success" | "error" };
const ToastContext = createContext<(text: string, tone?: Toast["tone"]) => void>(() => {});
export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);
  const push = useCallback((text: string, tone: Toast["tone"] = "info") => {
    const id = ++nextId.current;
    setToasts((t) => [...t.slice(-2), { id, text, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), tone === "error" ? 7000 : 3500);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed right-4 bottom-4 z-50 grid w-[min(380px,calc(100vw-32px))] gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            role={t.tone === "error" ? "alert" : "status"}
            className={`pointer-events-auto flex items-start gap-3 rounded-xl px-4 py-3 text-base shadow-(--shadow-pop) ${
              t.tone === "error" ? "bg-danger text-white" : "bg-ink text-on-ink"
            }`}
          >
            {t.tone === "success" && <span aria-hidden className="mt-1 size-2 shrink-0 rounded-full bg-caption" />}
            <span className="flex-1">{t.text}</span>
            <button
              type="button"
              aria-label="Dismiss"
              onClick={() => setToasts((all) => all.filter((x) => x.id !== t.id))}
              className="-mr-1 cursor-pointer rounded bg-transparent text-current opacity-70 hover:opacity-100"
            >
              <X className="size-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/* ---------- Slide-over panel (library / preview on smaller screens) ---------- */

export function Drawer({
  open,
  side,
  onClose,
  label,
  children,
}: {
  open: boolean;
  side: "left" | "right";
  onClose: () => void;
  label: string;
  children: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40" role="dialog" aria-modal="true" aria-label={label}>
      <div className="absolute inset-0 bg-ink/40" onClick={onClose} />
      <div
        className={`absolute top-0 bottom-0 flex w-[min(360px,90vw)] flex-col bg-paper shadow-2xl ${side === "left" ? "left-0" : "right-0"}`}
      >
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-line bg-panel px-4">
          <span className="pane-title">{label}</span>
          <IconButton label="Close" onClick={onClose}>
            <X className="size-5" />
          </IconButton>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}

/* ---------- Pane resize handle ---------- */

/** A thin draggable edge between two panes. `edge` is the side of the pane it sits on; dragging changes that pane's
 *  width (double-click resets it). Arrow keys move it too, for keyboard users. */
export function ResizeHandle({
  edge,
  width,
  min,
  max,
  label,
  onResize,
  onReset,
}: {
  edge: "left" | "right";
  width: number;
  min: number;
  max: number;
  label: string;
  onResize: (width: number, done: boolean) => void;
  onReset: () => void;
}) {
  const [dragging, setDragging] = useState(false);
  const start = useRef({ x: 0, width: 0 });
  const dir = edge === "right" ? 1 : -1; // a right edge grows to the right, a left edge to the left
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      aria-valuenow={width}
      aria-valuemin={min}
      aria-valuemax={max}
      tabIndex={0}
      title={`${label} (double-click to reset)`}
      onPointerDown={(e) => {
        e.preventDefault();
        e.currentTarget.setPointerCapture(e.pointerId);
        start.current = { x: e.clientX, width };
        setDragging(true);
      }}
      onPointerMove={(e) => dragging && onResize(start.current.width + (e.clientX - start.current.x) * dir, false)}
      onPointerUp={(e) => {
        if (!dragging) return;
        setDragging(false);
        onResize(start.current.width + (e.clientX - start.current.x) * dir, true);
      }}
      onDoubleClick={onReset}
      onKeyDown={(e) => {
        const step = e.shiftKey ? 48 : 16;
        if (e.key === "ArrowLeft") onResize(width - step * dir, true);
        else if (e.key === "ArrowRight") onResize(width + step * dir, true);
        else return;
        e.preventDefault();
      }}
      className={`group absolute top-0 bottom-0 z-10 w-2 cursor-col-resize touch-none outline-none ${edge === "right" ? "-right-1" : "-left-1"}`}
    >
      <span
        aria-hidden
        className={`absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2 transition-colors ${
          dragging ? "bg-cobalt" : "bg-transparent group-hover:bg-cobalt/50 group-focus-visible:bg-cobalt"
        }`}
      />
    </div>
  );
}
