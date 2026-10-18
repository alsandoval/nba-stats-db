"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { DataService, Team, Player, SEASONS_10YR } from "@/lib/data-service";

export default function OverviewPage() {
  const [season, setSeason] = useState<string>("2023-24");
  const [teams, setTeams] = useState<Team[]>([]);
  const [players, setPlayers] = useState<Player[]>([]);
  const [conference, setConference] = useState<"ALL" | "Eastern" | "Western">("ALL");
  const [sortField, setSortField] = useState<keyof Team>("win_pct");
  const [sortAsc, setSortAsc] = useState<boolean>(false);
  const [search, setSearch] = useState<string>("");

  useEffect(() => {
    DataService.getTeams(season).then(setTeams);
    DataService.getPlayers(season).then(setPlayers);
  }, [season]);

  const handleSort = (field: keyof Team) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
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
  const avgPace = teams.length
    ? (teams.reduce((s, t) => s + t.pace, 0) / teams.length).toFixed(1)
    : "99.2";
  const avgOffRtg = teams.length
    ? (teams.reduce((s, t) => s + t.off_rating, 0) / teams.length).toFixed(1)
    : "115.4";
  const avgTs = teams.length
    ? ((teams.reduce((s, t) => s + t.ts_pct, 0) / teams.length) * 100).toFixed(1)
    : "57.8";

  return (
    <div className="space-y-8">
      {/* Executive Commercial Header & Global 10-Season Switcher */}
      <div className="bg-surfaceCard border border-borderDark rounded-2xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-extrabold uppercase tracking-wider bg-accent/20 text-accent border border-accent/40">
              Enterprise Release • 10-Season Complete Archive
            </span>
            <span className="text-xs font-mono text-gray-400">
              12,729 Games • 5,393 Player-Seasons • 572 Shot Profiles • 641 Lineups
            </span>
          </div>
          <h1 className="text-xl md:text-2xl font-extrabold text-white">
            Antigravity NBA Intelligence &amp; Live Companion Suite
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
        <div className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg relative overflow-hidden group hover:border-accent/40 transition">
          <div className="absolute top-0 right-0 w-24 h-24 bg-accent/5 rounded-full blur-xl group-hover:bg-accent/10 transition" />
          <span className="text-xs uppercase font-mono text-gray-400">10-Season Archive</span>
          <h3 className="text-2xl font-extrabold text-white mt-1">12,729 Games</h3>
          <p className="text-xs text-accentGreen mt-1 flex items-center gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-accentGreen" />
            2015-16 to 2024-25 + Live ESPN Stream
          </p>
        </div>

        <div className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg relative overflow-hidden group hover:border-accent/40 transition">
          <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-full blur-xl group-hover:bg-cyan-500/10 transition" />
          <span className="text-xs uppercase font-mono text-gray-400">Player Impact &amp; LEBRON</span>
          <h3 className="text-2xl font-extrabold text-white mt-1">5,393 Seasons</h3>
          <p className="text-xs text-cyan-400 mt-1 flex items-center gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
            Ridge RAPM + Archetypes + 3D Clusters
          </p>
        </div>

        <div className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg relative overflow-hidden group hover:border-accent/40 transition">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-xl group-hover:bg-emerald-500/10 transition" />
          <span className="text-xs uppercase font-mono text-gray-400">Spatial Shot Quality</span>
          <h3 className="text-2xl font-extrabold text-white mt-1">572 Players + 30 Teams</h3>
          <p className="text-xs text-emerald-400 mt-1 flex items-center gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            Exact 6-Zone FGM/FGA &amp; SMOE Engine
          </p>
        </div>

        <div className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg relative overflow-hidden group hover:border-accent/40 transition">
          <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 rounded-full blur-xl group-hover:bg-purple-500/10 transition" />
          <span className="text-xs uppercase font-mono text-gray-400">CBA Capology &amp; Lineups</span>
          <h3 className="text-2xl font-extrabold text-white mt-1">450 Contracts • 641 Units</h3>
          <p className="text-xs text-purple-400 mt-1 flex items-center gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
            Multi-Year Cap Schedules &amp; Trade Machine
          </p>
        </div>
      </div>

      {/* Featured Live Game Companion Callout Banner */}
      <div className="bg-gradient-to-r from-red-950/40 via-surfaceCard to-blue-950/40 border-2 border-red-500/40 rounded-2xl p-6 shadow-2xl relative overflow-hidden flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-5">
          <div className="w-16 h-16 rounded-2xl bg-red-600/20 border border-red-500/50 flex items-center justify-center text-3xl animate-pulse">
            🔴
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="bg-red-500 text-white font-extrabold text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full animate-pulse">
                LIVE COMPANION
              </span>
              <span className="text-xs font-mono text-gray-400">
                Team-Colored Win Probability OHLC Candlesticks
              </span>
            </div>
            <h3 className="text-xl md:text-2xl font-black text-white">
              Live Game Center &amp; Team Win Probability Candlesticks
            </h3>
            <p className="text-xs md:text-sm text-gray-300 mt-1 max-w-2xl">
              Pick any live or recent NBA game by date. View minute-by-minute Win Probability OHLC candlesticks rendered in official high-contrast team colors, active 10-player on-court lineups, and shot quality xeFG% play-by-play.
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
            href="/rapm"
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
            href="/rapm"
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
            href="/rapm"
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
            href="/rapm"
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

      {/* Quick Launch Deep Analytics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <Link
          href="/wowy"
          className="p-5 rounded-2xl bg-gradient-to-br from-surfaceCard to-surface border border-borderDark hover:border-accent/60 transition group flex flex-col justify-between"
        >
          <div>
            <div className="text-2xl mb-2">⚡</div>
            <h4 className="text-lg font-bold text-white group-hover:text-accent transition">
              WOWY Bitmask &amp; 641 Lineup Studio
            </h4>
            <p className="text-xs text-gray-400 mt-1">
              Toggle any players ON/OFF court with 64-bit integer bitmasks and inspect all 641 evaluated 5-man NBA lineups with offensive/defensive synergy and spacing grades.
            </p>
          </div>
          <div className="mt-4 flex items-center text-xs font-semibold text-accent gap-1">
            <span>Explore 641 Lineup Evaluations</span>
            <span>&rarr;</span>
          </div>
        </Link>

        <Link
          href="/predictions"
          className="p-5 rounded-2xl bg-gradient-to-br from-surfaceCard to-surface border border-borderDark hover:border-cyan-500/60 transition group flex flex-col justify-between"
        >
          <div>
            <div className="text-2xl mb-2">🔮</div>
            <h4 className="text-lg font-bold text-white group-hover:text-cyan-400 transition">
              Cross-Era Predictor &amp; 12,729 Games Archive
            </h4>
            <p className="text-xs text-gray-400 mt-1">
              Simulate head-to-head matchups across any of the last 10 seasons (e.g. 2015-16 GSW vs 2023-24 BOS) and search all 12,729 historical Regular Season &amp; Playoff games.
            </p>
          </div>
          <div className="mt-4 flex items-center text-xs font-semibold text-cyan-400 gap-1">
            <span>Simulate Matchups &amp; Browse Archive</span>
            <span>&rarr;</span>
          </div>
        </Link>

        <Link
          href="/shots"
          className="p-5 rounded-2xl bg-gradient-to-br from-surfaceCard to-surface border border-borderDark hover:border-emerald-500/60 transition group flex flex-col justify-between"
        >
          <div>
            <div className="text-2xl mb-2">🎯</div>
            <h4 className="text-lg font-bold text-white group-hover:text-emerald-400 transition">
              572-Player &amp; 30-Team Spatial Shot Atlas
            </h4>
            <p className="text-xs text-gray-400 mt-1">
              Inspect real court zone FGM/FGA/FG% (Restricted Area, Paint, Mid-Range, Left/Right Corner 3, Above the Break 3) and SMOE for all 572 players and 30 teams.
            </p>
          </div>
          <div className="mt-4 flex items-center text-xs font-semibold text-emerald-400 gap-1">
            <span>Open Spatial Shot Quality Atlas</span>
            <span>&rarr;</span>
          </div>
        </Link>
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
              {season} League Averages: Pace: {avgPace} &middot; ORtg: {avgOffRtg} &middot; TS%: {avgTs}%
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Search */}
            <input
              type="text"
              placeholder="Search franchise..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-surface border border-borderDark rounded-lg px-3 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-accent w-44"
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
              {filteredTeams.map((t, idx) => (
                <tr
                  key={`${t.season || season}-${t.team_id}`}
                  className="hover:bg-surface/50 transition cursor-pointer group"
                >
                  <td className="py-2.5 px-4 font-mono text-xs text-gray-500 font-bold">
                    {idx + 1}
                  </td>
                  <td className="py-2.5 px-4">
                    <div className="flex items-center gap-2.5">
                      <span className="font-extrabold text-xs px-2 py-0.5 rounded bg-surface border border-borderDark text-accent font-mono">
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
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
