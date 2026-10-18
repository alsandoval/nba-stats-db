"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { checkBackendStatus, DataService, Player, Team } from "@/lib/data-service";

export function NavHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const [isLive, setIsLive] = useState<boolean>(false);
  const [menuOpen, setMenuOpen] = useState<boolean>(false);

  // Global Cmd+K / Ctrl+K Spotlight Command Palette
  const [cmdOpen, setCmdOpen] = useState<boolean>(false);
  const [cmdQuery, setCmdQuery] = useState<string>("");
  const [players, setPlayers] = useState<Player[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);

  useEffect(() => {
    checkBackendStatus().then(setIsLive);
    DataService.getPlayers("2023-24").then(setPlayers);
    DataService.getTeams("2023-24").then(setTeams);
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmdOpen((prev) => !prev);
      } else if (e.key === "Escape") {
        setCmdOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const navLinks = [
    { href: "/", label: "Overview", icon: "📊", desc: "10-Season Standings, 4-Quadrant Efficiency Map & Franchise War Room" },
    { href: "/live", label: "Live Center", icon: "🔴", isLive: true, desc: "Live ESPN Scoreboard, Team Win Prob Candlesticks & Live Shot Map" },
    { href: "/wowy", label: "WOWY Studio", icon: "⚡", desc: "64-Bit ON/OFF Lineup Builder, 641 Synergy Units & 500 Real NBA Lineups" },
    { href: "/rapm", label: "RAPM Hub", icon: "📈", desc: "5,393 Player-Seasons RAPM, LEBRON, Wins Added & 10-Yr Career Curves" },
    { href: "/shots", label: "Shot Quality", icon: "🎯", desc: "All 572 Players & 30 Teams 6-Zone Court Splits, SMOE & Click Simulator" },
    { href: "/scouting", label: "Scouting & Clutch", icon: "🔬", desc: "Clutch Killers, Hustle Tracking, Rim Defense, Draft Value & Combine" },
    { href: "/predictions", label: "Predictions", icon: "🔮", desc: "Cross-Era Matchup & Best-of-7 Series Simulator + 12,729 Games Archive" },
    { href: "/cba", label: "CBA & Trade", icon: "⚖️", desc: "2-Team Trade Machine with RAPM/Wins Impact & All 450 Active Contracts" },
    { href: "/compare", label: "Compare", icon: "👥", desc: "Cross-Era Player Comparison Studio with Radar Polygon & Zone Splits" },
  ];

  const matchingScenes = useMemo(() => {
    if (!cmdQuery.trim()) return navLinks;
    const q = cmdQuery.toLowerCase();
    return navLinks.filter(
      (n) => n.label.toLowerCase().includes(q) || n.desc.toLowerCase().includes(q)
    );
  }, [cmdQuery]);

  const matchingTeams = useMemo(() => {
    const q = cmdQuery.trim().toLowerCase();
    if (!q) return teams.slice(0, 6);
    return teams
      .filter(
        (t) =>
          t.full_name.toLowerCase().includes(q) ||
          t.abbreviation.toLowerCase().includes(q) ||
          t.city.toLowerCase().includes(q)
      )
      .slice(0, 8);
  }, [teams, cmdQuery]);

  const matchingPlayers = useMemo(() => {
    const q = cmdQuery.trim().toLowerCase();
    if (!q) return players.slice(0, 8);
    return players
      .filter(
        (p) =>
          p.full_name.toLowerCase().includes(q) ||
          p.team_abbreviation.toLowerCase().includes(q) ||
          (p.offensive_archetype || "").toLowerCase().includes(q) ||
          (p.college || "").toLowerCase().includes(q)
      )
      .slice(0, 12);
  }, [players, cmdQuery]);

  const navigateTo = (href: string) => {
    setCmdOpen(false);
    setCmdQuery("");
    router.push(href);
  };

  return (
    <>
      <header className="border-b border-borderDark bg-surface/95 backdrop-blur-md sticky top-0 z-50 px-4 md:px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
          {/* Brand Logo */}
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2 group shrink-0">
              <span className="text-2xl transform group-hover:scale-110 transition duration-200">
                🏀
              </span>
              <div className="flex flex-col">
                <span className="font-extrabold text-base tracking-wider text-white flex items-center gap-1.5">
                  ANTIGRAVITY{" "}
                  <span className="text-accent text-[11px] font-semibold bg-accent/10 px-1.5 py-0.5 rounded border border-accent/30">
                    NBA
                  </span>
                </span>
                <span className="text-[9px] text-gray-400 font-mono">
                  10-Season Intelligence Suite
                </span>
              </div>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden xl:flex items-center gap-0.5 font-medium text-xs">
              {navLinks.map((link) => {
                const active = pathname === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition flex items-center gap-1 whitespace-nowrap ${
                      active
                        ? "bg-accent/20 text-accent border border-accent/40 shadow-sm"
                        : "text-gray-300 hover:text-white hover:bg-surfaceCard"
                    }`}
                  >
                    <span>{link.icon}</span>
                    <span>{link.label}</span>
                    {(link as any).isLive && (
                      <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping inline-block ml-0.5" />
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Global Omni-Search Trigger & Status Pill */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCmdOpen(true)}
              className="flex items-center gap-2 bg-surfaceCard hover:bg-surface border border-borderDark hover:border-accent/50 px-3 py-1.5 rounded-xl text-xs font-mono text-gray-300 hover:text-white transition shadow-inner"
              title="Open Global Omni-Search (Ctrl+K / Cmd+K)"
            >
              <span>🔍</span>
              <span className="hidden sm:inline text-gray-400">Search 5,393 players, 30 teams...</span>
              <span className="sm:hidden text-gray-400">Search</span>
              <kbd className="px-1.5 py-0.5 text-[10px] rounded bg-surface border border-borderDark text-accent font-bold">
                ⌘K
              </kbd>
            </button>

            {/* Mode Pill */}
            <div className="hidden md:flex items-center gap-1.5 bg-surfaceCard px-2.5 py-1 rounded-full border border-borderDark text-[10px] font-mono">
              <span
                className={`w-2 h-2 rounded-full ${
                  isLive ? "bg-accentGreen animate-pulse shadow-glow" : "bg-cyan-400"
                }`}
              />
              <span className="text-gray-300">
                {isLive ? "FastAPI Live" : "Edge Static"}
              </span>
            </div>

            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="xl:hidden p-2 rounded-lg bg-surfaceCard border border-borderDark text-gray-300 hover:text-white"
            >
              <span className="text-lg">☰</span>
            </button>
          </div>
        </div>

        {/* Mobile Drawer */}
        {menuOpen && (
          <div className="xl:hidden mt-3 pt-3 border-t border-borderDark grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMenuOpen(false)}
                className={`p-2.5 rounded-lg flex items-center gap-2 ${
                  pathname === link.href
                    ? "bg-accent/20 text-accent border border-accent/30 font-bold"
                    : "bg-surfaceCard text-gray-300"
                }`}
              >
                <span>{link.icon}</span>
                <span>{link.label}</span>
              </Link>
            ))}
          </div>
        )}
      </header>

      {/* GLOBAL OMNI-SEARCH COMMAND PALETTE MODAL (Cmd+K / Ctrl+K) */}
      {cmdOpen && (
        <div
          className="fixed inset-0 z-[100] bg-black/75 backdrop-blur-sm flex items-start justify-center pt-16 px-4"
          onClick={() => setCmdOpen(false)}
        >
          <div
            className="bg-surfaceCard border border-accent/40 rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Search Input Bar */}
            <div className="p-4 border-b border-borderDark flex items-center gap-3 bg-surface">
              <span className="text-lg">🔍</span>
              <input
                type="text"
                autoFocus
                value={cmdQuery}
                onChange={(e) => setCmdQuery(e.target.value)}
                placeholder="Search any NBA player (Jokic, Curry, Wemby), franchise (BOS, LAL), archetype, or tool..."
                className="w-full bg-transparent text-sm font-mono text-white placeholder-gray-500 focus:outline-none"
              />
              <button
                onClick={() => setCmdOpen(false)}
                className="px-2 py-0.5 rounded bg-surfaceCard border border-borderDark text-[10px] font-mono text-gray-400 hover:text-white"
              >
                ESC
              </button>
            </div>

            <div className="max-h-[70vh] overflow-y-auto p-4 space-y-5 divide-y divide-borderDark/50">
              {/* 1. Matching Players */}
              <div>
                <div className="text-[10px] font-mono uppercase text-gray-400 font-bold mb-2 flex items-center justify-between">
                  <span>NBA Players ({matchingPlayers.length} shown)</span>
                  <span>Click Action to Inspect</span>
                </div>
                <div className="space-y-1.5">
                  {matchingPlayers.map((p) => (
                    <div
                      key={p.player_id}
                      className="p-2.5 rounded-xl bg-surface/80 hover:bg-surface border border-borderDark/70 flex flex-wrap items-center justify-between gap-2 text-xs font-mono transition"
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="px-2 py-0.5 rounded bg-surfaceCard border border-borderDark text-accent font-bold">
                          {p.team_abbreviation}
                        </span>
                        <div>
                          <span className="font-bold text-white font-sans">{p.full_name}</span>
                          <span className="text-[10px] text-gray-400 block">
                            {p.pts} PPG • {p.reb} RPG • {p.ast} APG • RAPM{" "}
                            <strong className={p.rapm >= 0 ? "text-emerald-400" : "text-red-400"}>
                              {p.rapm >= 0 ? `+${p.rapm}` : p.rapm}
                            </strong>{" "}
                            • {p.offensive_archetype}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => navigateTo(`/rapm?q=${encodeURIComponent(p.full_name)}`)}
                          className="px-2 py-1 rounded bg-accent/20 hover:bg-accent text-accent hover:text-white border border-accent/40 text-[10px] font-bold transition"
                        >
                          📈 RAPM Dossier
                        </button>
                        <button
                          onClick={() => navigateTo(`/shots?player=${p.player_id}`)}
                          className="px-2 py-1 rounded bg-emerald-500/20 hover:bg-emerald-500 text-emerald-300 hover:text-black border border-emerald-500/40 text-[10px] font-bold transition"
                        >
                          🎯 Shot Atlas
                        </button>
                        <button
                          onClick={() => navigateTo(`/compare?p1=${p.player_id}`)}
                          className="px-2 py-1 rounded bg-cyan-500/20 hover:bg-cyan-400 text-cyan-300 hover:text-black border border-cyan-500/40 text-[10px] font-bold transition"
                        >
                          👥 Compare
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 2. Matching Franchises */}
              <div className="pt-4">
                <div className="text-[10px] font-mono uppercase text-gray-400 font-bold mb-2">
                  NBA Franchises ({matchingTeams.length} shown)
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {matchingTeams.map((t) => (
                    <div
                      key={t.team_id}
                      className="p-2.5 rounded-xl bg-surface/80 hover:bg-surface border border-borderDark/70 flex items-center justify-between text-xs font-mono"
                    >
                      <div>
                        <span className="font-bold text-white font-sans">{t.full_name}</span>
                        <span className="text-[10px] text-gray-400 block">
                          {t.wins}-{t.losses} • Net{" "}
                          {t.net_rating >= 0 ? `+${t.net_rating}` : t.net_rating} • ORtg{" "}
                          {t.off_rating}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => navigateTo(`/wowy?team=${t.team_id}`)}
                          className="px-2 py-1 rounded bg-surfaceCard hover:bg-accent text-gray-300 hover:text-white border border-borderDark text-[10px] transition"
                        >
                          ⚡ WOWY
                        </button>
                        <button
                          onClick={() => navigateTo(`/cba?team=${t.team_id}`)}
                          className="px-2 py-1 rounded bg-surfaceCard hover:bg-purple-500 text-gray-300 hover:text-white border border-borderDark text-[10px] transition"
                        >
                          ⚖️ Cap
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 3. Matching Analytics Scenes */}
              <div className="pt-4">
                <div className="text-[10px] font-mono uppercase text-gray-400 font-bold mb-2">
                  Analytics Scenes &amp; Engines
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {matchingScenes.map((s) => (
                    <button
                      key={s.href}
                      onClick={() => navigateTo(s.href)}
                      className="p-2.5 rounded-xl bg-surface/80 hover:bg-accent/20 border border-borderDark hover:border-accent/50 text-left transition flex items-start gap-2.5"
                    >
                      <span className="text-lg">{s.icon}</span>
                      <div>
                        <div className="text-xs font-bold text-white">{s.label}</div>
                        <div className="text-[10px] font-mono text-gray-400 line-clamp-1">
                          {s.desc}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
