import type { Metadata } from "next";
import { NavHeader } from "@/components/nav-header";
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

        <footer className="border-t border-borderDark py-6 text-center text-xs text-gray-500 font-mono space-y-1.5">
          <p className="text-gray-400">
            <strong className="text-white">Antigravity NBA Intelligence Suite</strong> &middot; 10-Season Complete Archive (2015-16 to 2024-25) &middot; Live ESPN NBA Stream
          </p>
          <p className="text-[11px] text-gray-500">
            12,729 Historical Games &middot; 5,393 Player-Seasons &middot; 300 Team-Seasons &middot; 572 Spatial Shot Profiles &middot; 641 Evaluated 5-Man Lineups &middot; 450 Active CBA Contracts
          </p>
        </footer>
      </body>
    </html>
  );
}
