import type { Metadata } from "next";
import { Manrope, Newsreader } from "next/font/google";

import { Sidebar } from "@/components/Sidebar";

import "./globals.css";

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-sans",
});

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "SolutionFlow · Enterprise Copilot",
  description: "Enterprise AI customer insight and solution workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${manrope.variable} ${newsreader.variable}`}>
        <div className="appShell">
          <div className="shellAtmosphere" aria-hidden="true" />
          <Sidebar />
          <main className="mainContent">{children}</main>
        </div>
      </body>
    </html>
  );
}
