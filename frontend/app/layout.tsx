import type { Metadata } from "next";
import localFont from "next/font/local";
import { APPEARANCE_SCRIPT } from "@/lib/appearanceScript";
import "./globals.css";

// Bundled (app/fonts, variable woff2 from Google Fonts, OFL) instead of next/font/google: no download at build time,
// so the app builds offline, and Turbopack can't trip over Google's font URLs ("queries have exactly one entry").
const bricolage = localFont({
  src: "./fonts/bricolage-grotesque-latin.woff2",
  variable: "--font-bricolage",
  weight: "500 800",
  display: "swap",
});

const noto = localFont({
  src: "./fonts/noto-sans-latin.woff2",
  variable: "--font-noto",
  weight: "400 600",
  display: "swap",
});

const notoKhmer = localFont({
  src: "./fonts/noto-sans-khmer-khmer.woff2",
  variable: "--font-noto-khmer",
  weight: "400 600",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Shorts Studio",
  description: "Make short vertical videos for TikTok, Reels and Shorts in English and Khmer.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${bricolage.variable} ${noto.variable} ${notoKhmer.variable} antialiased`} suppressHydrationWarning>
      <head>
        {/* theme and interface size before the first paint (Settings → Appearance) */}
        <script dangerouslySetInnerHTML={{ __html: APPEARANCE_SCRIPT }} />
      </head>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
