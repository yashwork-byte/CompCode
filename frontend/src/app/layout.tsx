import type { Metadata } from "next";
import { Geist_Mono, Press_Start_2P, VT323 } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { MenuBar } from "@/components/menu-bar";
import { Dock } from "@/components/dock";

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Chunky pixel display font — window titles, buttons, badges, brand.
const pressStart = Press_Start_2P({
  variable: "--font-pixel",
  weight: "400",
  subsets: ["latin"],
});

// Readable retro terminal font — larger body copy, hints, clock.
const vt323 = VT323({
  variable: "--font-terminal",
  weight: "400",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CodeComp — reason over a codebase",
  description:
    "Ask questions about a codebase. Get answers grounded in the actual code.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistMono.variable} ${pressStart.variable} ${vt323.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col">
        <MenuBar />
        <div className="flex-1 pt-9 pb-24">{children}</div>
        <Dock />
        <Toaster richColors position="top-center" />
      </body>
    </html>
  );
}
