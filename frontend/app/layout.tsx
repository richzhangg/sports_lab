import "./globals.css";
import type { Metadata } from "next";
import { Fraunces, Instrument_Sans, IBM_Plex_Mono } from "next/font/google";

const display = Fraunces({
  subsets: ["latin"],
  display: "swap",
  axes: ["opsz"],
  variable: "--font-display",
});
const sans = Instrument_Sans({
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600"],
  variable: "--font-sans",
});
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Sports Opportunity Modeling Lab",
  description:
    "Construct, run, compare, and validate mathematical models of socioeconomic accessibility in collegiate athletics.",
};

import SiteHeader from "@/components/SiteHeader";
import { ScrollProgress } from "@/components/Motion";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable} ${mono.variable}`}>
      <body className="antialiased">
        <ScrollProgress />
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
