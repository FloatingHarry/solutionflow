import type { Metadata } from "next";

import { Sidebar } from "@/components/Sidebar";

import "./globals.css";


export const metadata: Metadata = {
  title: "SolutionFlow",
  description: "Enterprise AI customer insight and solution workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="appShell">
          <Sidebar />
          <main className="mainContent">{children}</main>
        </div>
      </body>
    </html>
  );
}

