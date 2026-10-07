/** "just now", "5 min ago", "3 h ago", "yesterday", "Oct 6" */
export function relativeTime(iso: string, now = Date.now()): string {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const s = Math.max(0, Math.round((now - t) / 1000));
  if (s < 60) return "just now";
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} h ago`;
  if (h < 48) return "yesterday";
  return new Date(t).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export const langCode = (lang: string) => (lang === "km" ? "ខ្មែរ" : "EN");
export const isImagePath = (p: string) => /\.(jpe?g|png|webp)$/i.test(p);
