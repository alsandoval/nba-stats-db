import type { Metadata } from "next";
import { NavHeader } from "@/components/nav-header";
import "./globals.css";

export const metadata: Metadata = {
  title: "Antigravity NBA Analytics Platform",
  description: "Enterprise Sub-15ms WOWY, Sparse Ridge RAPM, Spatial Shot Quality, and Matchup Predictions",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen flex flex-col bg-background text-gray-100 antialiased selection:bg-accent selection:text-white">
        <NavHeader />

        <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-8">{children}</main>

        <footer className="border-t border-borderDark py-6 text-center text-xs text-gray-500 font-mono space-y-1">
          <p>
            Antigravity NBA Platform &middot; Powered by DuckDB Parquet, Sparse Ridge RAPM, and XGBoost
          </p>
          <p className="text-[11px] text-gray-600">
            Engineered for High-Performance Standalone Deployment &amp; GitHub Pages
          </p>
        </footer>
      </body>
    </html>
  );
}
