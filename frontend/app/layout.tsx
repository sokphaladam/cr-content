import type { Metadata } from "next";
import { Bricolage_Grotesque, Noto_Sans, Noto_Sans_Khmer } from "next/font/google";
import "./globals.css";

const bricolage = Bricolage_Grotesque({
  variable: "--font-bricolage",
  subsets: ["latin"],
  weight: ["500", "700", "800"],
});

const noto = Noto_Sans({
  variable: "--font-noto",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const notoKhmer = Noto_Sans_Khmer({
  variable: "--font-noto-khmer",
  subsets: ["khmer"],
  weight: ["400", "600"],
});

export const metadata: Metadata = {
  title: "Shorts Studio",
  description: "Make short vertical videos for TikTok, Reels and Shorts in English and Khmer.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${bricolage.variable} ${noto.variable} ${notoKhmer.variable} antialiased`}>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
