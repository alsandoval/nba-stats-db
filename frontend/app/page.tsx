"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { DataService, Team } from "@/lib/data-service";

export default function OverviewPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [conference, setConference] = useState<"ALL" | "Eastern" | "Western">("ALL");
  const [sortField, setSortField] = useState<keyof Team>("net_rating");
  const [sortAsc, setSortAsc] = useState<boolean>(false);
  const [search, setSearch] = useState<string>("");

  useEffect(() => {
    DataService.getTeams().then(setTeams);
  }, []);

  const handleSort = (field: keyof Team) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const filteredTeams = teams
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

  // Calculate league averages
  const avgPace = teams.length ? (teams.reduce((s, t) => s + t.pace, 0) / teams.length).toFixed(1) : "99.2";
  const avgOffRtg = teams.length ? (teams.reduce((s, t) => s + t.off_rating, 0) / teams.length).toFixed(1) : "115.4";
  const avgTs = teams.length ? ((teams.reduce((s, t) => s + t.ts_pct, 0) / teams.length) * 100).toFixed(1) : "57.8";

  return (
    <div className="space-y-8">
      {/* Hero / KPI Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg relative overflow-hidden group hover:border-accent/40 transition">
          <div className="absolute top-0 right-0 w-24 h-24 bg-accent/5 rounded-full blur-xl group-hover:bg-accent/10 transition" />
          <span className="text-xs uppercase font-mono text-gray-400">OLAP Analytical Engine</span>
          <h3 className="text-2xl font-extrabold text-white mt-1">DuckDB + Parquet</h3>
          <p className="text-xs text-accentGreen mt-1 flex items-center gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-accentGreen" />
            Sub-15ms Vectorized WOWY
          </p>
        </div>

        <div className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg relative overflow-hidden group hover:border-accent/40 transition">
          <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-full blur-xl group-hover:bg-cyan-500/10 transition" />
          <span className="text-xs uppercase font-mono text-gray-400">Player Impact Solver</span>
          <h3 className="text-2xl font-extrabold text-white mt-1">Ridge RAPM</h3>
          <p className="text-xs text-cyan-400 mt-1 flex items-center gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
            Sparse CSC Matrix (&lt;0.1s solve)
          </p>
        </div>

        <div className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg relative overflow-hidden group hover:border-accent/40 transition">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-xl group-hover:bg-emerald-500/10 transition" />
          <span className="text-xs uppercase font-mono text-gray-400">Spatial xeFG% &amp; SMOE</span>
          <h3 className="text-2xl font-extrabold text-white mt-1">XGBoost Spatial</h3>
          <p className="text-xs text-emerald-400 mt-1 flex items-center gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            Real-time Shot Making Engine
          </p>
        </div>

        <div className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg relative overflow-hidden group hover:border-accent/40 transition">
          <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 rounded-full blur-xl group-hover:bg-purple-500/10 transition" />
          <span className="text-xs uppercase font-mono text-gray-400">Salary Cap Rules</span>
          <h3 className="text-2xl font-extrabold text-white mt-1">2023 CBA Aprons</h3>
          <p className="text-xs text-purple-400 mt-1 flex items-center gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
            First &amp; Second Apron Trade Machine
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
              <span className="text-xs font-mono text-gray-400">Financial OHLC Execution</span>
            </div>
            <h3 className="text-xl md:text-2xl font-black text-white">
              Live Game Center &amp; Differential Candlesticks
            </h3>
            <p className="text-xs md:text-sm text-gray-300 mt-1 max-w-2xl">
              Accompany live NBA games with minute-by-minute lead differential candlesticks (OHLC), continuous win probability curves, active 10-player on-court lineup cards, and shot quality xeFG% play-by-play.
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

      {/* Quick Launch Deep Analytics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <Link
          href="/wowy"
          className="p-5 rounded-2xl bg-gradient-to-br from-surfaceCard to-surface border border-borderDark hover:border-accent/60 transition group flex flex-col justify-between"
        >
          <div>
            <div className="text-2xl mb-2">⚡</div>
            <h4 className="text-lg font-bold text-white group-hover:text-accent transition">
              Vectorized WOWY Studio
            </h4>
            <p className="text-xs text-gray-400 mt-1">
              Select any combination of players ON or OFF court. Queries 64-bit integer bitmasks to calculate exact lineup net ratings and offensive efficiency.
            </p>
          </div>
          <div className="mt-4 flex items-center text-xs font-semibold text-accent gap-1">
            <span>Explore Lineup Combinations</span>
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
              Matchup &amp; Win Probability Studio
            </h4>
            <p className="text-xs text-gray-400 mt-1">
              Simulate head-to-head team matchups, test live game win probability sliders (margin, time remaining, possession), and replay clutch historical games.
            </p>
          </div>
          <div className="mt-4 flex items-center text-xs font-semibold text-cyan-400 gap-1">
            <span>Simulate Predictions &amp; Win Prob</span>
            <span>&rarr;</span>
          </div>
        </Link>

        <Link
          href="/cba"
          className="p-5 rounded-2xl bg-gradient-to-br from-surfaceCard to-surface border border-borderDark hover:border-purple-500/60 transition group flex flex-col justify-between"
        >
          <div>
            <div className="text-2xl mb-2">⚖️</div>
            <h4 className="text-lg font-bold text-white group-hover:text-purple-400 transition">
              CBA Second Apron &amp; Trade Machine
            </h4>
            <p className="text-xs text-gray-400 mt-1">
              Trade real NBA player contracts between any two franchises. Instantly verifies 2023 CBA rules, salary matching limits, and First/Second Apron penalties.
            </p>
          </div>
          <div className="mt-4 flex items-center text-xs font-semibold text-purple-400 gap-1">
            <span>Launch Trade Machine</span>
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
              <span>🏆</span> 2023-24 NBA Team Standings &amp; Net Ratings
            </h2>
            <p className="text-xs text-gray-400 mt-0.5 font-mono">
              League Averages: Pace: {avgPace} &middot; ORtg: {avgOffRtg} &middot; TS%: {avgTs}%
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
                  key={t.team_id}
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
                      <span className="text-[10px] text-gray-500 font-mono hidden md:inline">
                        {t.division}
                      </span>
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-gray-200">
                    {t.wins}-{t.losses}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-gray-400">
                    {(t.win_pct * 100).toFixed(1)}%
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
