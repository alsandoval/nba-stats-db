"use client";

import React, { useEffect, useState } from "react";
import { VirtualTable, PercentileBadge } from "@/components/virtual-table";
import { DataService, RAPMPlayer, Player } from "@/lib/data-service";

export default function RAPMPage() {
  const [players, setPlayers] = useState<RAPMPlayer[]>([]);
  const [allPlayersData, setAllPlayersData] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [teamFilter, setTeamFilter] = useState("ALL");
  const [lambdaReg, setLambdaReg] = useState(1200);
  const [minPoss, setMinPoss] = useState(50);
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);

  // Load RAPM data
  useEffect(() => {
    setLoading(true);
    DataService.getRAPMLeaderboard(lambdaReg).then((data) => {
      setPlayers(data);
      setLoading(false);
    });
  }, [lambdaReg]);

  // Load detailed player profiles for slide-over inspection
  useEffect(() => {
    DataService.getPlayers().then(setAllPlayersData);
  }, []);

  const teams = Array.from(new Set(players.map((p) => p.team_abbreviation))).sort();

  const filtered = players
    .filter((p) => p.possessions >= minPoss)
    .filter((p) => (teamFilter === "ALL" ? true : p.team_abbreviation === teamFilter))
    .filter(
      (p) =>
        p.player_name.toLowerCase().includes(search.toLowerCase()) ||
        p.team_abbreviation.toLowerCase().includes(search.toLowerCase())
    );

  const handleRowClick = (row: RAPMPlayer) => {
    const fullProfile = allPlayersData.find((p) => p.player_id === row.player_id);
    if (fullProfile) {
      setSelectedPlayer(fullProfile);
    }
  };

  const columns = [
    {
      key: "rank",
      header: "#",
      width: "60px",
      align: "center" as const,
      render: (_: any, __: any) => {
        const idx = filtered.indexOf(__) + 1;
        return <span className="font-mono text-xs text-gray-500 font-bold">{idx}</span>;
      },
    },
    {
      key: "player_name",
      header: "Player",
      width: "220px",
      render: (val: string, row: RAPMPlayer) => (
        <div
          className="flex items-center gap-2 cursor-pointer group"
          onClick={() => handleRowClick(row)}
        >
          <span className="font-bold text-white group-hover:text-accent transition truncate">
            {val}
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface border border-borderDark text-gray-400">
            {row.team_abbreviation}
          </span>
        </div>
      ),
    },
    {
      key: "possessions",
      header: "Possessions",
      width: "110px",
      align: "right" as const,
      render: (val: number) => (
        <span className="font-mono text-gray-300">{val.toLocaleString()}</span>
      ),
    },
    {
      key: "orapm",
      header: "ORAPM",
      width: "100px",
      align: "right" as const,
      render: (val: number) => (
        <span
          className={`font-mono font-bold ${val >= 0 ? "text-emerald-400" : "text-red-400"}`}
        >
          {val > 0 ? `+${val.toFixed(2)}` : val.toFixed(2)}
        </span>
      ),
    },
    {
      key: "orapm_percentile",
      header: "Off %ile",
      width: "100px",
      align: "center" as const,
      isPercentile: true,
    },
    {
      key: "drapm",
      header: "DRAPM",
      width: "100px",
      align: "right" as const,
      render: (val: number) => (
        <span
          className={`font-mono font-bold ${val >= 0 ? "text-emerald-400" : "text-red-400"}`}
        >
          {val > 0 ? `+${val.toFixed(2)}` : val.toFixed(2)}
        </span>
      ),
    },
    {
      key: "drapm_percentile",
      header: "Def %ile",
      width: "100px",
      align: "center" as const,
      isPercentile: true,
    },
    {
      key: "rapm",
      header: "Total RAPM",
      width: "110px",
      align: "right" as const,
      render: (val: number) => (
        <span
          className={`font-mono font-extrabold text-sm ${
            val >= 0 ? "text-emerald-400" : "text-red-400"
          }`}
        >
          {val > 0 ? `+${val.toFixed(2)}` : val.toFixed(2)}
        </span>
      ),
    },
    {
      key: "rapm_percentile",
      header: "Impact %ile",
      width: "110px",
      align: "center" as const,
      isPercentile: true,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Title & Diagnostic Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-2">
            <span>📈</span> Regularized Adjusted Plus-Minus (RAPM)
          </h1>
          <p className="text-sm text-gray-400 mt-1 font-mono">
            Compressed Lineup Stints (~32k/season) solved via <code>scipy.sparse.csc_matrix</code> with Bayesian Box/Tracking Priors.
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <div className="bg-surfaceCard px-3 py-1.5 rounded-lg border border-borderDark text-gray-300">
            Active Dataset: <strong className="text-accent">{players.length} Players</strong>
          </div>
        </div>
      </div>

      {/* Control Bar: Search, Filters, and Interactive Lambda Slider */}
      <div className="bg-surfaceCard border border-borderDark rounded-2xl p-5 shadow-lg space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search Input */}
          <div>
            <label className="block text-xs font-mono text-gray-400 mb-1.5">Search Player / Team</label>
            <input
              type="text"
              placeholder="e.g. Jokic, Curry, BOS..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-surface border border-borderDark rounded-xl px-3.5 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-accent"
            />
          </div>

          {/* Team Filter */}
          <div>
            <label className="block text-xs font-mono text-gray-400 mb-1.5">Filter Franchise</label>
            <select
              value={teamFilter}
              onChange={(e) => setTeamFilter(e.target.value)}
              className="w-full bg-surface border border-borderDark rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-accent font-mono"
            >
              <option value="ALL">All 30 Teams</option>
              {teams.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          {/* Min Possessions Filter */}
          <div>
            <div className="flex items-center justify-between text-xs font-mono text-gray-400 mb-1.5">
              <span>Min Possessions:</span>
              <span className="text-accent font-bold">{minPoss}</span>
            </div>
            <input
              type="range"
              min="0"
              max="500"
              step="25"
              value={minPoss}
              onChange={(e) => setMinPoss(Number(e.target.value))}
              className="w-full accent-accent cursor-pointer"
            />
          </div>

          {/* Lambda Ridge Slider */}
          <div>
            <div className="flex items-center justify-between text-xs font-mono text-gray-400 mb-1.5">
              <span>Ridge Regularization (&lambda;):</span>
              <span className="text-cyan-400 font-bold">{lambdaReg}</span>
            </div>
            <input
              type="range"
              min="400"
              max="2800"
              step="100"
              value={lambdaReg}
              onChange={(e) => setLambdaReg(Number(e.target.value))}
              className="w-full accent-cyan-400 cursor-pointer"
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-borderDark/40 text-xs text-gray-400 font-mono">
          <span>Showing {filtered.length} qualified players</span>
          <span className="text-gray-500">Click any player to inspect complete profile &amp; percentiles</span>
        </div>
      </div>

      {/* TanStack Virtualized Table */}
      <div className="bg-surfaceCard border border-borderDark rounded-2xl p-4 shadow-xl">
        {loading ? (
          <div className="py-24 text-center font-mono text-sm text-gray-400 animate-pulse">
            Solving sparse normal equations (X^T W X + &lambda; I)^(-1)...
          </div>
        ) : (
          <VirtualTable data={filtered} columns={columns} height="560px" rowHeight={44} />
        )}
      </div>

      {/* Slide-over Player Inspection Modal */}
      {selectedPlayer && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surfaceCard border border-borderDark rounded-2xl max-w-lg w-full p-6 shadow-2xl relative space-y-5 animate-in fade-in zoom-in-95 duration-200">
            {/* Close Button */}
            <button
              onClick={() => setSelectedPlayer(null)}
              className="absolute top-4 right-4 w-8 h-8 rounded-full bg-surface hover:bg-surfaceCard border border-borderDark flex items-center justify-center text-gray-400 hover:text-white transition"
            >
              &times;
            </button>

            {/* Header */}
            <div className="flex items-center gap-3">
              <span className="text-3xl">👤</span>
              <div>
                <h3 className="text-xl font-extrabold text-white">{selectedPlayer.full_name}</h3>
                <p className="text-xs font-mono text-gray-400">
                  {selectedPlayer.team_abbreviation} &middot; {selectedPlayer.gp} Games Played &middot; {selectedPlayer.min_per_game} MPG
                </p>
              </div>
            </div>

            {/* Per-Game Traditional Stats */}
            <div className="grid grid-cols-4 gap-2 text-center font-mono">
              <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                <span className="text-[10px] uppercase text-gray-400 block">PTS</span>
                <span className="text-base font-bold text-white">{selectedPlayer.pts}</span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                <span className="text-[10px] uppercase text-gray-400 block">REB</span>
                <span className="text-base font-bold text-white">{selectedPlayer.reb}</span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                <span className="text-[10px] uppercase text-gray-400 block">AST</span>
                <span className="text-base font-bold text-white">{selectedPlayer.ast}</span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                <span className="text-[10px] uppercase text-gray-400 block">TS%</span>
                <span className="text-base font-bold text-white">{(selectedPlayer.ts_pct * 100).toFixed(1)}%</span>
              </div>
            </div>

            {/* Percentile Rank Profile */}
            <div className="space-y-2.5 text-xs font-mono pt-2 border-t border-borderDark">
              <div className="flex items-center justify-between">
                <span className="text-gray-300">Total RAPM Impact:</span>
                <PercentileBadge value={selectedPlayer.rapm_percentile} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-300">Offensive RAPM:</span>
                <PercentileBadge value={selectedPlayer.orapm_percentile} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-300">Defensive RAPM:</span>
                <PercentileBadge value={selectedPlayer.drapm_percentile} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-300">Scoring Volume:</span>
                <PercentileBadge value={selectedPlayer.pts_percentile} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-300">Playmaking (AST):</span>
                <PercentileBadge value={selectedPlayer.ast_percentile} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-300">True Shooting Efficiency:</span>
                <PercentileBadge value={selectedPlayer.ts_percentile} />
              </div>
            </div>

            <button
              onClick={() => setSelectedPlayer(null)}
              className="w-full py-2 bg-surface hover:bg-surfaceCard border border-borderDark rounded-xl text-xs font-bold text-gray-300 hover:text-white transition"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
