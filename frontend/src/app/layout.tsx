import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "SignalForge — Autonomous Prediction Market Agent",
  description: "AI-powered prediction market intelligence. DGrid AI analysis, Kelly Criterion sizing, Arc-anchored reasoning traces.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
