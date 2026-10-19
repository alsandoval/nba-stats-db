"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { DataService, Team, Player, SEASONS_10YR } from "@/lib/data-service";
import { getTeamPalette } from "@/components/differential-candlestick-chart";

export default function OverviewPage() {
  const [season, setSeason] = useState<string>("2023-24");
  const [teams, setTeams] = useState<Team[]>([]);
  const [players, setPlayers] = useState<Player[]>([]);
  const [conference, setConference] = useState<"ALL" | "Eastern" | "Western">("ALL");
  const [sortField, setSortField] = useState<keyof Team>("win_pct");
  const [sortAsc, setSortAsc] = useState<boolean>(false);
  const [search, setSearch] = useState<string>("");
  const [selectedFranchise, setSelectedFranchise] = useState<Team | null>(null);

  useEffect(() => {
    DataService.getTeams(season).then(setTeams);
    DataService.getPlayers(season).then(setPlayers);
  }, [season]);

  const handleSort = (field: keyof Team) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(field === "def_rating");
    }
  };

  const filteredTeams = useMemo(() => {
    return teams
      .filter((t) => (conference === "ALL" ? true : t.conference === conference))
      .filter(
        (t) =>
          t.full_name.toLowerCase().includes(search.toLowerCase()) ||
          t.abbreviation.toLowerCase().includes(search.toLowerCase())
      )
      .sort((a, b) => {
        const valA = a[sortField];
        const valB = b[sortField];
        if (typeof valA === "number" && typeof valB === "number") {
          return sortAsc ? valA - valB : valB - valA;
        }
        return 0;
      });
  }, [teams, conference, search, sortField, sortAsc]);

  // Season League Leaders (qualified players with >= 20 GP or top available)
  const seasonLeaders = useMemo(() => {
    if (!players.length) return null;
    const qual = players.filter((p) => p.gp >= 20);
    const pool = qual.length >= 10 ? qual : players;
    const byPts = [...pool].sort((a, b) => b.pts - a.pts)[0];
    const byReb = [...pool].sort((a, b) => b.reb - a.reb)[0];
    const byAst = [...pool].sort((a, b) => b.ast - a.ast)[0];
    const byRapm = [...pool].sort((a, b) => b.rapm - a.rapm)[0];
    return { byPts, byReb, byAst, byRapm };
  }, [players]);

  // Calculate league averages
  const avgPaceNum = teams.length
    ? teams.reduce((s, t) => s + t.pace, 0) / teams.length
    : 99.2;
  const avgOffRtgNum = teams.length
    ? teams.reduce((s, t) => s + t.off_rating, 0) / teams.length
    : 115.4;
  const avgDefRtgNum = teams.length
    ? teams.reduce((s, t) => s + t.def_rating, 0) / teams.length
    : 115.4;
  const avgTs = teams.length
    ? ((teams.reduce((s, t) => s + t.ts_pct, 0) / teams.length) * 100).toFixed(1)
    : "57.8";

  // 4-Quadrant Efficiency Scatter bounds
  const scatterBounds = useMemo(() => {
    if (!teams.length) return { minOff: 105, maxOff: 124, minDef: 105, maxDef: 124 };
    const offs = teams.map((t) => t.off_rating);
    const defs = teams.map((t) => t.def_rating);
    return {
      minOff: Math.min(...offs) - 1.5,
      maxOff: Math.max(...offs) + 1.5,
      minDef: Math.min(...defs) - 1.5,
      maxDef: Math.max(...defs) + 1.5,
    };
  }, [teams]);

  // Selected Franchise 10-Year History & Roster
  const franchiseHistory = useMemo(
    () => (selectedFranchise ? DataService.getTeamHistory(selectedFranchise.abbreviation) : []),
    [selectedFranchise]
  );

  const franchiseRoster = useMemo(() => {
    if (!selectedFranchise) return [];
    return players
      .filter((p) => p.team_abbreviation === selectedFranchise.abbreviation)
      .sort((a, b) => b.pts - a.pts)
      .slice(0, 8);
  }, [selectedFranchise, players]);

  const exportStandingsCsv = () => {
    if (!filteredTeams.length) return;
    const headers = ["Rank", "Season", "Team", "Abbr", "Conf", "W", "L", "WinPct", "ORtg", "DRtg", "NetRtg", "Pace", "TS%"];
    const rows = filteredTeams.map((t, i) => [
      i + 1,
      season,
      `"${t.full_name}"`,
      t.abbreviation,
      t.conference,
      t.wins,
      t.losses,
      (t.win_pct * 100).toFixed(1),
      t.off_rating,
      t.def_rating,
      t.net_rating,
      t.pace,
      (t.ts_pct * 100).toFixed(1),
    ]);
    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `nba_standings_${season}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8">
      {/* Executive Commercial Header & Global 10-Season Switcher */}
      <div className="bg-surfaceCard border border-borderDark rounded-2xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-extrabold uppercase tracking-wider bg-accent/20 text-accent border border-accent/40">
              Commercial Edition • 10-Season Complete Intelligence Suite
            </span>
            <span className="text-xs font-mono text-gray-400">
              Press <kbd className="px-1.5 py-0.5 rounded bg-surface border border-borderDark text-accent">⌘K</kbd> to Instant Search Any Player or Team
            </span>
          </div>
          <h1 className="text-xl md:text-2xl font-extrabold text-white">
            Antigravity NBA Executive War Room &amp; Live Companion
          </h1>
        </div>

        {/* 10-Season Selector */}
        <div className="flex items-center gap-2.5">
          <span className="text-xs font-mono text-gray-400 uppercase font-bold">Active Season:</span>
          <select
            value={season}
            onChange={(e) => setSeason(e.target.value)}
            className="bg-surface border border-accent/50 rounded-xl px-3.5 py-2 text-xs font-mono font-extrabold text-white focus:outline-none focus:border-accent shadow-sm"
          >
            {SEASONS_10YR.map((s) => (
              <option key={s} value={s}>
                {s} NBA Season
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Hero / KPI Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link
          href="/predictions"
          className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg relative overflow-hidden group hover:border-accent/50 transition"
        >
          <div className="absolute top-0 right-0 w-24 h-24 bg-accent/5 rounded-full blur-xl group-hover:bg-accent/10 transition" />
          <span className="text-xs uppercase font-mono text-gray-400">10-Season Archive</span>
          <h3 className="text-2xl font-extrabold text-white mt-1">12,729 Games</h3>
          <p className="text-xs text-accentGreen mt-1 flex items-center gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-accentGreen" />
            2015-16 to 2024-25 + Series Simulator
          </p>
        </Link>

        <Link
          href="/rapm"
          className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg relative overflow-hidden group hover:border-cyan-500/50 transition"
        >
          <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-full blur-xl group-hover:bg-cyan-500/10 transition" />
          <span className="text-xs uppercase font-mono text-gray-400">Player Impact &amp; LEBRON</span>
          <h3 className="text-2xl font-extrabold text-white mt-1">5,393 Seasons</h3>
          <p className="text-xs text-cyan-400 mt-1 flex items-center gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
            Ridge RAPM + 10-Yr Career Curves
          </p>
        </Link>

        <Link
          href="/scouting"
          className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg relative overflow-hidden group hover:border-emerald-500/50 transition"
        >
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-xl group-hover:bg-emerald-500/10 transition" />
          <span className="text-xs uppercase font-mono text-gray-400">Scouting, Clutch &amp; Hustle</span>
          <h3 className="text-2xl font-extrabold text-white mt-1">Clutch • Defend • Draft</h3>
          <p className="text-xs text-emerald-400 mt-1 flex items-center gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            469 Clutch • 567 Hustle • Draft VOPE
          </p>
        </Link>

        <Link
          href="/cba"
          className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg relative overflow-hidden group hover:border-purple-500/50 transition"
        >
          <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 rounded-full blur-xl group-hover:bg-purple-500/10 transition" />
          <span className="text-xs uppercase font-mono text-gray-400">CBA Capology &amp; Lineups</span>
          <h3 className="text-2xl font-extrabold text-white mt-1">450 Contracts • 1,141 Units</h3>
          <p className="text-xs text-purple-400 mt-1 flex items-center gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
            Trade Machine + RAPM/Wins Impact
          </p>
        </Link>
      </div>

      {/* Featured Live Game Companion Callout Banner */}
      <div className="bg-gradient-to-r from-red-950/40 via-surfaceCard to-blue-950/40 border-2 border-red-500/40 rounded-2xl p-6 shadow-2xl relative overflow-hidden flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-5">
          <div className="w-16 h-16 rounded-2xl bg-red-600/20 border border-red-500/50 flex items-center justify-center text-3xl animate-pulse shrink-0">
            🔴
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="bg-red-500 text-white font-extrabold text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full animate-pulse">
                LIVE COMPANION
              </span>
              <span className="text-xs font-mono text-gray-400">
                Team-Colored Win Probability OHLC Candlesticks + Live Court Shot Map
              </span>
            </div>
            <h3 className="text-xl md:text-2xl font-black text-white">
              Live Game Center, Team Win Prob Candlesticks &amp; Momentum Alerts
            </h3>
            <p className="text-xs md:text-sm text-gray-300 mt-1 max-w-2xl">
              Pick any live or recent NBA game by date. View minute-by-minute Win Probability OHLC candlesticks rendered in official high-contrast team colors, interactive clutch swing jumps, and live court shot maps.
            </p>
          </div>
        </div>

        <Link
          href="/live"
          className="px-6 py-3 bg-red-600 hover:bg-red-500 text-white font-black text-sm rounded-xl shadow-lg shadow-red-600/30 transition flex items-center gap-2 whitespace-nowrap"
        >
          <span>Launch Live Companion</span>
          <span>&rarr;</span>
        </Link>
      </div>

      {/* Selected Season League Leaders Strip */}
      {seasonLeaders && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            href={`/rapm?player=${seasonLeaders.byPts?.player_id}`}
            className="bg-surfaceCard border border-borderDark hover:border-accent/50 rounded-2xl p-4 flex items-center justify-between transition group"
          >
            <div>
              <span className="text-[10px] font-mono uppercase text-gray-400 block">
                {season} Scoring Leader
              </span>
              <span className="text-base font-extrabold text-white group-hover:text-accent transition">
                {seasonLeaders.byPts?.full_name}
              </span>
              <span className="text-xs font-mono text-gray-400 block">
                {seasonLeaders.byPts?.team_abbreviation} • {seasonLeaders.byPts?.gp} GP
              </span>
            </div>
            <div className="text-right font-mono">
              <span className="text-2xl font-black text-accent">{seasonLeaders.byPts?.pts}</span>
              <span className="text-[10px] text-gray-400 block">PPG</span>
            </div>
          </Link>

          <Link
            href={`/rapm?player=${seasonLeaders.byReb?.player_id}`}
            className="bg-surfaceCard border border-borderDark hover:border-cyan-500/50 rounded-2xl p-4 flex items-center justify-between transition group"
          >
            <div>
              <span className="text-[10px] font-mono uppercase text-gray-400 block">
                {season} Rebounding Leader
              </span>
              <span className="text-base font-extrabold text-white group-hover:text-cyan-400 transition">
                {seasonLeaders.byReb?.full_name}
              </span>
              <span className="text-xs font-mono text-gray-400 block">
                {seasonLeaders.byReb?.team_abbreviation} • {seasonLeaders.byReb?.gp} GP
              </span>
            </div>
            <div className="text-right font-mono">
              <span className="text-2xl font-black text-cyan-400">{seasonLeaders.byReb?.reb}</span>
              <span className="text-[10px] text-gray-400 block">RPG</span>
            </div>
          </Link>

          <Link
            href={`/rapm?player=${seasonLeaders.byAst?.player_id}`}
            className="bg-surfaceCard border border-borderDark hover:border-emerald-500/50 rounded-2xl p-4 flex items-center justify-between transition group"
          >
            <div>
              <span className="text-[10px] font-mono uppercase text-gray-400 block">
                {season} Assists Leader
              </span>
              <span className="text-base font-extrabold text-white group-hover:text-emerald-400 transition">
                {seasonLeaders.byAst?.full_name}
              </span>
              <span className="text-xs font-mono text-gray-400 block">
                {seasonLeaders.byAst?.team_abbreviation} • {seasonLeaders.byAst?.gp} GP
              </span>
            </div>
            <div className="text-right font-mono">
              <span className="text-2xl font-black text-emerald-400">{seasonLeaders.byAst?.ast}</span>
              <span className="text-[10px] text-gray-400 block">APG</span>
            </div>
          </Link>

          <Link
            href={`/rapm?player=${seasonLeaders.byRapm?.player_id}`}
            className="bg-surfaceCard border border-borderDark hover:border-purple-500/50 rounded-2xl p-4 flex items-center justify-between transition group"
          >
            <div>
              <span className="text-[10px] font-mono uppercase text-gray-400 block">
                {season} #1 RAPM Impact
              </span>
              <span className="text-base font-extrabold text-white group-hover:text-purple-400 transition">
                {seasonLeaders.byRapm?.full_name}
              </span>
              <span className="text-xs font-mono text-gray-400 block">
                {seasonLeaders.byRapm?.team_abbreviation} • {seasonLeaders.byRapm?.offensive_archetype}
              </span>
            </div>
            <div className="text-right font-mono">
              <span className="text-2xl font-black text-purple-400">
                +{seasonLeaders.byRapm?.rapm.toFixed(2)}
              </span>
              <span className="text-[10px] text-gray-400 block">RAPM</span>
            </div>
          </Link>
        </div>
      )}

      {/* NEW: INTERACTIVE 4-QUADRANT TEAM EFFICIENCY LANDSCAPE (ORtg vs DRtg in Team Colors) */}
      <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-extrabold text-white flex items-center gap-2">
              <span>🧭</span> {season} 4-Quadrant Team Efficiency Landscape (ORtg vs DRtg)
            </h2>
            <p className="text-xs font-mono text-gray-400">
              X-Axis: Offensive Rating (Higher Right &rarr;) &middot; Y-Axis: Defensive Rating (Better Defense Top &uarr;) &middot; Click any team node to open Franchise War Room
            </p>
          </div>
          <span className="text-xs font-mono text-accent bg-accent/10 border border-accent/30 px-3 py-1 rounded-full">
            Click Team Badge for 10-Yr War Room
          </span>
        </div>

        <div className="relative w-full h-[360px] bg-surface rounded-2xl border border-borderDark overflow-hidden p-4">
          {/* Quadrant Background Labels */}
          <div className="absolute top-3 right-4 text-[10px] font-mono uppercase font-extrabold text-emerald-400/70 bg-emerald-950/40 px-2.5 py-1 rounded border border-emerald-500/30">
            🏆 Elite Contenders (+ORtg, +DRtg)
          </div>
          <div className="absolute top-3 left-4 text-[10px] font-mono uppercase font-bold text-cyan-400/70 bg-cyan-950/30 px-2.5 py-1 rounded border border-cyan-500/20">
            🛡️ Defensive Grinders (-ORtg, +DRtg)
          </div>
          <div className="absolute bottom-3 right-4 text-[10px] font-mono uppercase font-bold text-amber-400/70 bg-amber-950/30 px-2.5 py-1 rounded border border-amber-500/20">
            🔥 Glass Cannons (+ORtg, -DRtg)
          </div>
          <div className="absolute bottom-3 left-4 text-[10px] font-mono uppercase font-bold text-red-400/70 bg-red-950/30 px-2.5 py-1 rounded border border-red-500/20">
            📉 Lottery / Rebuild (-ORtg, -DRtg)
          </div>

          {/* League Average Crosshairs */}
          <div className="absolute inset-x-0 top-1/2 border-t border-dashed border-gray-600/60 pointer-events-none" />
          <div className="absolute inset-y-0 left-1/2 border-l border-dashed border-gray-600/60 pointer-events-none" />

          {/* Team Nodes */}
          {filteredTeams.map((t) => {
            const xPct = Math.min(
              94,
              Math.max(
                6,
                ((t.off_rating - scatterBounds.minOff) /
                  Math.max(1, scatterBounds.maxOff - scatterBounds.minOff)) *
                  88 +
                  6
              )
            );
            // Invert Y so lower Def Rating (better defense) is near top (yPct smaller)
            const yPct = Math.min(
              90,
              Math.max(
                10,
                ((t.def_rating - scatterBounds.minDef) /
                  Math.max(1, scatterBounds.maxDef - scatterBounds.minDef)) *
                  80 +
                  10
              )
            );
            const pal = getTeamPalette(t.abbreviation);
            return (
              <button
                key={t.team_id}
                onClick={() => setSelectedFranchise(t)}
                style={{
                  left: `${xPct}%`,
                  top: `${yPct}%`,
                  backgroundColor: pal.primary,
                  borderColor: pal.secondary,
                }}
                className="absolute -translate-x-1/2 -translate-y-1/2 px-2 py-0.5 rounded-md border text-[10px] font-mono font-extrabold text-white shadow-lg hover:scale-125 hover:z-30 transition transform"
                title={`${t.full_name} (${t.wins}-${t.losses}) • ORtg ${t.off_rating} • DRtg ${t.def_rating} • Net ${t.net_rating >= 0 ? `+${t.net_rating}` : t.net_rating}`}
              >
                {t.abbreviation}
              </button>
            );
          })}
        </div>
      </div>

      {/* Standings & Team Power Ratings Table */}
      <div className="bg-surfaceCard rounded-2xl border border-borderDark shadow-xl overflow-hidden">
        {/* Table Controls */}
        <div className="p-5 border-b border-borderDark flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>🏆</span> {season} NBA Team Standings &amp; Efficiency Ratings (All 30 Franchises)
            </h2>
            <p className="text-xs text-gray-400 mt-0.5 font-mono">
              {season} League Averages: Pace: {avgPaceNum.toFixed(1)} &middot; ORtg: {avgOffRtgNum.toFixed(1)} &middot; TS%: {avgTs}% &middot; Click any row for 10-Yr Franchise War Room
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Search */}
            <input
              type="text"
              placeholder="Search franchise..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-surface border border-borderDark rounded-lg px-3 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-accent w-40"
            />

            {/* Conference Selector */}
            <div className="flex bg-surface rounded-lg p-0.5 border border-borderDark text-xs font-mono">
              {(["ALL", "Eastern", "Western"] as const).map((conf) => (
                <button
                  key={conf}
                  onClick={() => setConference(conf)}
                  className={`px-3 py-1 rounded-md transition ${
                    conference === conf
                      ? "bg-accent text-white font-bold shadow-sm"
                      : "text-gray-400 hover:text-white"
                  }`}
                >
                  {conf}
                </button>
              ))}
            </div>

            <button
              onClick={exportStandingsCsv}
              className="px-3 py-1.5 rounded-lg bg-surface hover:bg-accent/20 border border-borderDark hover:border-accent/50 text-xs font-mono text-gray-300 hover:text-white transition"
            >
              ⬇ CSV
            </button>
          </div>
        </div>

        {/* Responsive Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface text-gray-400 text-xs uppercase font-mono border-b border-borderDark">
              <tr>
                <th className="py-3 px-4">#</th>
                <th
                  className="py-3 px-4 cursor-pointer hover:text-white"
                  onClick={() => handleSort("full_name")}
                >
                  Franchise {sortField === "full_name" && (sortAsc ? "▲" : "▼")}
                </th>
                <th
                  className="py-3 px-3 text-right cursor-pointer hover:text-white"
                  onClick={() => handleSort("wins")}
                >
                  W-L {sortField === "wins" && (sortAsc ? "▲" : "▼")}
                </th>
                <th
                  className="py-3 px-3 text-right cursor-pointer hover:text-white"
                  onClick={() => handleSort("win_pct")}
                >
                  Win% {sortField === "win_pct" && (sortAsc ? "▲" : "▼")}
                </th>
                <th className="py-3 px-3 text-center hidden md:table-cell">Home</th>
                <th className="py-3 px-3 text-center hidden md:table-cell">Road</th>
                <th className="py-3 px-3 text-center hidden lg:table-cell">L10</th>
                <th
                  className="py-3 px-3 text-right cursor-pointer hover:text-white"
                  onClick={() => handleSort("off_rating")}
                >
                  ORtg {sortField === "off_rating" && (sortAsc ? "▲" : "▼")}
                </th>
                <th
                  className="py-3 px-3 text-right cursor-pointer hover:text-white"
                  onClick={() => handleSort("def_rating")}
                >
                  DRtg {sortField === "def_rating" && (sortAsc ? "▲" : "▼")}
                </th>
                <th
                  className="py-3 px-3 text-right cursor-pointer hover:text-white"
                  onClick={() => handleSort("net_rating")}
                >
                  Net Rtg {sortField === "net_rating" && (sortAsc ? "▲" : "▼")}
                </th>
                <th
                  className="py-3 px-3 text-right cursor-pointer hover:text-white"
                  onClick={() => handleSort("pace")}
                >
                  Pace {sortField === "pace" && (sortAsc ? "▲" : "▼")}
                </th>
                <th
                  className="py-3 px-3 text-right cursor-pointer hover:text-white"
                  onClick={() => handleSort("ts_pct")}
                >
                  TS% {sortField === "ts_pct" && (sortAsc ? "▲" : "▼")}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-borderDark/40">
              {filteredTeams.map((t, idx) => {
                const pal = getTeamPalette(t.abbreviation);
                return (
                  <tr
                    key={`${t.season || season}-${t.team_id}`}
                    onClick={() => setSelectedFranchise(t)}
                    className="hover:bg-surface/60 transition cursor-pointer group"
                  >
                    <td className="py-2.5 px-4 font-mono text-xs text-gray-500 font-bold">
                      {idx + 1}
                    </td>
                    <td className="py-2.5 px-4">
                      <div className="flex items-center gap-2.5">
                        <span
                          className="font-extrabold text-xs px-2 py-0.5 rounded text-white font-mono shadow-xs"
                          style={{ backgroundColor: pal.primary }}
                        >
                          {t.abbreviation}
                        </span>
                        <span className="font-bold text-white group-hover:text-accent transition text-sm">
                          {t.full_name}
                        </span>
                        <span className="text-[10px] text-gray-500 font-mono hidden xl:inline">
                          {t.division}
                        </span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-gray-200 font-semibold">
                      {t.wins}-{t.losses}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-gray-300">
                      {(t.win_pct * 100).toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-3 text-center font-mono text-xs text-gray-400 hidden md:table-cell">
                      {t.home_record || "-"}
                    </td>
                    <td className="py-2.5 px-3 text-center font-mono text-xs text-gray-400 hidden md:table-cell">
                      {t.road_record || "-"}
                    </td>
                    <td className="py-2.5 px-3 text-center font-mono text-xs text-gray-400 hidden lg:table-cell">
                      {t.l10 || "-"}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-gray-300">
                      {t.off_rating.toFixed(1)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-gray-300">
                      {t.def_rating.toFixed(1)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold">
                      <span
                        className={
                          t.net_rating > 0
                            ? "text-emerald-400"
                            : t.net_rating < 0
                            ? "text-red-400"
                            : "text-gray-400"
                        }
                      >
                        {t.net_rating > 0 ? `+${t.net_rating.toFixed(1)}` : t.net_rating.toFixed(1)}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-gray-400">
                      {t.pace.toFixed(1)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-gray-400">
                      {(t.ts_pct * 100).toFixed(1)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* FRANCHISE 10-YEAR WAR ROOM MODAL */}
      {selectedFranchise && (
        <div
          className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setSelectedFranchise(null)}
        >
          <div
            className="bg-surfaceCard border border-borderDark rounded-2xl max-w-3xl w-full p-6 shadow-2xl space-y-6 max-h-[88vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-4 border-b border-borderDark pb-4">
              <div className="flex items-center gap-3.5">
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center font-black text-lg text-white shadow-lg"
                  style={{ backgroundColor: getTeamPalette(selectedFranchise.abbreviation).primary }}
                >
                  {selectedFranchise.abbreviation}
                </div>
                <div>
                  <span className="text-xs font-mono text-gray-400 uppercase">
                    {selectedFranchise.conference} Conference • {selectedFranchise.division} Division
                  </span>
                  <h3 className="text-2xl font-black text-white">{selectedFranchise.full_name}</h3>
                  <p className="text-xs font-mono text-gray-300 mt-0.5">
                    {season} Record: <strong>{selectedFranchise.wins}-{selectedFranchise.losses}</strong> (
                    {(selectedFranchise.win_pct * 100).toFixed(1)}%) &middot; ORtg{" "}
                    {selectedFranchise.off_rating} &middot; DRtg {selectedFranchise.def_rating} &middot; Net{" "}
                    <strong
                      className={
                        selectedFranchise.net_rating >= 0 ? "text-emerald-400" : "text-red-400"
                      }
                    >
                      {selectedFranchise.net_rating >= 0
                        ? `+${selectedFranchise.net_rating}`
                        : selectedFranchise.net_rating}
                    </strong>
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedFranchise(null)}
                className="w-8 h-8 rounded-full bg-surface border border-borderDark text-gray-400 hover:text-white flex items-center justify-center"
              >
                &times;
              </button>
            </div>

            {/* 10-Season Franchise Trajectory */}
            <div>
              <h4 className="text-xs font-mono uppercase text-gray-400 font-bold mb-3">
                📈 10-Season Franchise Trajectory (2015-16 to 2024-25)
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-5 lg:grid-cols-10 gap-2 text-center font-mono text-xs">
                {franchiseHistory.map((h) => (
                  <div
                    key={h.season}
                    onClick={() => {
                      if (h.season) setSeason(h.season);
                      setSelectedFranchise(h);
                    }}
                    className={`p-2 rounded-xl border cursor-pointer transition ${
                      h.season === season
                        ? "bg-accent/20 border-accent text-white"
                        : "bg-surface border-borderDark hover:border-gray-600 text-gray-300"
                    }`}
                  >
                    <div className="text-[10px] text-gray-400 font-bold">{h.season?.slice(2)}</div>
                    <div className="font-extrabold text-white mt-0.5">
                      {h.wins}-{h.losses}
                    </div>
                    <div
                      className={`text-[10px] font-bold mt-0.5 ${
                        h.net_rating >= 0 ? "text-emerald-400" : "text-red-400"
                      }`}
                    >
                      {h.net_rating >= 0 ? `+${h.net_rating}` : h.net_rating}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Season Top Roster Contributors */}
            <div>
              <h4 className="text-xs font-mono uppercase text-gray-400 font-bold mb-2.5">
                🏀 {season} Top Roster Impact Contributors ({selectedFranchise.abbreviation})
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs font-mono">
                {franchiseRoster.map((p) => (
                  <div
                    key={p.player_id}
                    className="p-3 rounded-xl bg-surface border border-borderDark flex items-center justify-between"
                  >
                    <div className="truncate">
                      <span className="font-bold text-white font-sans block truncate">
                        {p.full_name}
                      </span>
                      <span className="text-[10px] text-gray-400">
                        {p.pts} PPG • {p.reb} RPG • {p.ast} APG • {p.offensive_archetype}
                      </span>
                    </div>
                    <div className="text-right shrink-0 ml-2">
                      <span
                        className={`font-extrabold block ${
                          p.rapm >= 0 ? "text-emerald-400" : "text-red-400"
                        }`}
                      >
                        {p.rapm >= 0 ? `+${p.rapm}` : p.rapm} RAPM
                      </span>
                      <span className="text-[10px] text-amber-300">
                        +{p.wins_added ?? 0} Wins
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Deep Links Bar */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-borderDark text-xs font-mono">
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  href={`/wowy?team=${selectedFranchise.team_id}`}
                  className="px-3.5 py-2 rounded-xl bg-accent hover:bg-accentHover text-white font-bold transition"
                >
                  ⚡ Open in WOWY Lineup Studio
                </Link>
                <Link
                  href={`/shots?team=${selectedFranchise.abbreviation}`}
                  className="px-3.5 py-2 rounded-xl bg-surface hover:bg-surfaceCard border border-borderDark text-emerald-400 font-bold transition"
                >
                  🎯 Team Spatial Shot Atlas
                </Link>
                <Link
                  href={`/cba?team=${selectedFranchise.team_id}`}
                  className="px-3.5 py-2 rounded-xl bg-surface hover:bg-surfaceCard border border-borderDark text-purple-400 font-bold transition"
                >
                  ⚖️ Cap Sheet &amp; Trade Machine
                </Link>
              </div>
              <button
                onClick={() => setSelectedFranchise(null)}
                className="px-4 py-2 rounded-xl bg-surface border border-borderDark text-gray-300 hover:text-white"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
