import "@/styles/globals.css";
import "@excalidraw/excalidraw/index.css";
import { AppProviders } from "@/components/providers/app-providers";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ReactNode } from "react";

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  display: "swap",
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "SmartStudy — AI Whiteboard & Tutor",
  description: "Interactive infinite whiteboard with real-time AI vision, drawing assistance, and math reasoning.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className={`${inter.className} min-h-screen bg-slate-50 text-slate-900 antialiased`}>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
