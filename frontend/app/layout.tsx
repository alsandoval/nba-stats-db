import type { Metadata } from "next";
import { NavHeader } from "@/components/nav-header";
import { APP_RELEASE_VERSION, APP_BUILD_TIMESTAMP, DEFAULT_SEASON } from "@/lib/data-service";
import "./globals.css";

export const metadata: Metadata = {
  title: "Antigravity NBA Analytics & Live Companion Suite",
  description:
    "Commercial Release: 10-Season Complete NBA Archive (2015-16 to 2024-25), Live Team-Colored Win Probability OHLC Candlesticks, 5,393 Player-Seasons RAPM & LEBRON, 572 Spatial Shot Profiles, 641 Evaluated Lineups, and 450 CBA Contracts",
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

        <footer className="border-t border-borderDark bg-surface/60 py-8 px-4 text-center text-xs text-gray-400 font-mono space-y-3 mt-12">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-left space-y-1">
              <p className="text-gray-300">
                <strong className="text-white">Antigravity NBA Intelligence Suite</strong> &middot; 10-Season Complete Archive (2015-16 to 2024-25) &middot; Live ESPN &amp; Insider Wire
              </p>
              <p className="text-[11px] text-gray-500">
                12,729 Historical Games &middot; 5,393 Player-Seasons &middot; 300 Team-Seasons &middot; 572 Spatial Shot Profiles &middot; 641 Evaluated 5-Man Lineups &middot; 450 Active CBA Contracts
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-2">
              <span className="px-3 py-1 rounded-full bg-accent/15 border border-accent/40 text-accent font-extrabold text-[11px] tracking-wide">
                RELEASE {APP_RELEASE_VERSION}
              </span>
              <span className="px-3 py-1 rounded-full bg-surfaceCard border border-borderDark text-gray-300 font-bold text-[11px]">
                {APP_BUILD_TIMESTAMP}
              </span>
              <span className="px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/40 text-emerald-400 font-bold text-[11px]">
                Default Season: {DEFAULT_SEASON}
              </span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
