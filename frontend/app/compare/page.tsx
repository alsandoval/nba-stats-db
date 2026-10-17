"use client";

import React, { useEffect, useState } from "react";
import { DataService, Player } from "@/lib/data-service";
import { PercentileBadge } from "@/components/virtual-table";

const PRESETS = [
  { name: "Jokic vs Doncic", idA: 203999, idB: 1629029 },
  { name: "Curry vs LeBron", idA: 201939, idB: 2544 },
  { name: "Tatum vs Edwards", idA: 1628369, idB: 1630162 },
  { name: "Giannis vs SGA", idA: 203507, idB: 1628983 },
];

export default function ComparePage() {
  const [players, setPlayers] = useState<Player[]>([]);
  const [playerAId, setPlayerAId] = useState<number>(203999); // Jokic
  const [playerBId, setPlayerBId] = useState<number>(1629029); // Luka

  useEffect(() => {
    DataService.getPlayers().then(setPlayers);
  }, []);

  const playerA = players.find((p) => p.player_id === playerAId) || players[0];
  const playerB = players.find((p) => p.player_id === playerBId) || players[1];

  const renderComparisonBar = (label: string, valA: number, valB: number, isPct: boolean = false) => {
    const higherIsBetter = true;
    const isAWinner = higherIsBetter ? valA > valB : valA < valB;
    const isBWinner = higherIsBetter ? valB > valA : valB < valA;
    const maxVal = Math.max(Math.abs(valA), Math.abs(valB), 0.01) * 1.15;
    const widthA = Math.min(100, Math.max(8, (Math.abs(valA) / maxVal) * 100));
    const widthB = Math.min(100, Math.max(8, (Math.abs(valB) / maxVal) * 100));

    const fmt = (v: number) => (isPct ? `${(v * 100).toFixed(1)}%` : v.toFixed(1));

    return (
      <div className="space-y-1.5 py-2.5 border-b border-borderDark/40">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className={`font-bold ${isAWinner ? "text-emerald-400" : "text-gray-300"}`}>
            {fmt(valA)}
          </span>
          <span className="text-gray-400 font-bold uppercase text-[11px] tracking-wider">{label}</span>
          <span className={`font-bold ${isBWinner ? "text-emerald-400" : "text-gray-300"}`}>
            {fmt(valB)}
          </span>
        </div>

        {/* Dual Bar Graphic */}
        <div className="grid grid-cols-2 gap-3 h-2.5">
          <div className="flex justify-end bg-surface rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                isAWinner ? "bg-accent" : "bg-gray-600"
              }`}
              style={{ width: `${widthA}%` }}
            />
          </div>
          <div className="flex justify-start bg-surface rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                isBWinner ? "bg-cyan-400" : "bg-gray-600"
              }`}
              style={{ width: `${widthB}%` }}
            />
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-8">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-2">
            <span>👥</span> Head-to-Head Player Comparison
          </h1>
          <p className="text-sm text-gray-400 mt-1 font-mono">
            Side-by-side analytical radar comparing per-game production, shooting efficiency, and RAPM impact.
          </p>
        </div>

        {/* Presets */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-mono text-gray-400 mr-1">Rivalries:</span>
          {PRESETS.map((pr) => (
            <button
              key={pr.name}
              onClick={() => {
                setPlayerAId(pr.idA);
                setPlayerBId(pr.idB);
              }}
              className="px-3 py-1 bg-surfaceCard hover:bg-surface border border-borderDark rounded-lg text-xs font-semibold text-gray-300 hover:text-white transition"
            >
              {pr.name}
            </button>
          ))}
        </div>
      </div>

      {/* Selectors Bar */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Player A Selector */}
        <div className="p-4 bg-surfaceCard border border-borderDark rounded-2xl shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-accent font-bold">Player A</span>
            {playerA && (
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-surface border border-borderDark text-gray-300">
                {playerA.team_abbreviation}
              </span>
            )}
          </div>
          <select
            value={playerAId}
            onChange={(e) => setPlayerAId(Number(e.target.value))}
            className="w-full bg-surface border border-borderDark rounded-xl p-2.5 text-sm font-bold text-white focus:outline-none focus:border-accent"
          >
            {players.map((p) => (
              <option key={p.player_id} value={p.player_id}>
                {p.full_name} ({p.team_abbreviation} &middot; {p.pts} PPG)
              </option>
            ))}
          </select>
        </div>

        {/* Player B Selector */}
        <div className="p-4 bg-surfaceCard border border-borderDark rounded-2xl shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-cyan-400 font-bold">Player B</span>
            {playerB && (
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-surface border border-borderDark text-gray-300">
                {playerB.team_abbreviation}
              </span>
            )}
          </div>
          <select
            value={playerBId}
            onChange={(e) => setPlayerBId(Number(e.target.value))}
            className="w-full bg-surface border border-borderDark rounded-xl p-2.5 text-sm font-bold text-white focus:outline-none focus:border-cyan-400"
          >
            {players.map((p) => (
              <option key={p.player_id} value={p.player_id}>
                {p.full_name} ({p.team_abbreviation} &middot; {p.pts} PPG)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Comparison Grid */}
      {playerA && playerB && (
        <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-6">
          {/* Top Banner Cards */}
          <div className="grid grid-cols-2 gap-6 text-center border-b border-borderDark pb-6">
            <div className="space-y-1">
              <span className="text-4xl block">🌟</span>
              <h3 className="text-xl font-extrabold text-white">{playerA.full_name}</h3>
              <p className="text-xs font-mono text-accent">
                {playerA.team_abbreviation} &middot; {playerA.gp} GP &middot; {playerA.min_per_game} MPG
              </p>
            </div>

            <div className="space-y-1">
              <span className="text-4xl block">⚡</span>
              <h3 className="text-xl font-extrabold text-white">{playerB.full_name}</h3>
              <p className="text-xs font-mono text-cyan-400">
                {playerB.team_abbreviation} &middot; {playerB.gp} GP &middot; {playerB.min_per_game} MPG
              </p>
            </div>
          </div>

          {/* Metric Comparison Bars */}
          <div className="space-y-1 max-w-3xl mx-auto">
            {renderComparisonBar("Points Per Game", playerA.pts, playerB.pts)}
            {renderComparisonBar("Rebounds Per Game", playerA.reb, playerB.reb)}
            {renderComparisonBar("Assists Per Game", playerA.ast, playerB.ast)}
            {renderComparisonBar("Steals Per Game", playerA.stl, playerB.stl)}
            {renderComparisonBar("Blocks Per Game", playerA.blk, playerB.blk)}
            {renderComparisonBar("True Shooting (TS%)", playerA.ts_pct, playerB.ts_pct, true)}
            {renderComparisonBar("Field Goal %", playerA.fg_pct, playerB.fg_pct, true)}
            {renderComparisonBar("3-Point %", playerA.fg3_pct, playerB.fg3_pct, true)}
            {renderComparisonBar("On-Court Net Rating", playerA.net_rating, playerB.net_rating)}
            {renderComparisonBar("Offensive RAPM (ORAPM)", playerA.orapm, playerB.orapm)}
            {renderComparisonBar("Defensive RAPM (DRAPM)", playerA.drapm, playerB.drapm)}
            {renderComparisonBar("Total RAPM Impact", playerA.rapm, playerB.rapm)}
          </div>

          {/* Percentile Badges Comparison */}
          <div className="max-w-2xl mx-auto pt-6 border-t border-borderDark space-y-3 font-mono text-xs">
            <h4 className="text-center font-bold text-gray-300 uppercase text-[11px] tracking-wider mb-3">
              Percentile Rankings (0 - 100)
            </h4>
            <div className="flex items-center justify-between">
              <PercentileBadge value={playerA.rapm_percentile} />
              <span className="text-gray-400">Total RAPM Impact</span>
              <PercentileBadge value={playerB.rapm_percentile} />
            </div>
            <div className="flex items-center justify-between">
              <PercentileBadge value={playerA.orapm_percentile} />
              <span className="text-gray-400">Offensive Impact</span>
              <PercentileBadge value={playerB.orapm_percentile} />
            </div>
            <div className="flex items-center justify-between">
              <PercentileBadge value={playerA.drapm_percentile} />
              <span className="text-gray-400">Defensive Impact</span>
              <PercentileBadge value={playerB.drapm_percentile} />
            </div>
            <div className="flex items-center justify-between">
              <PercentileBadge value={playerA.pts_percentile} />
              <span className="text-gray-400">Scoring Volume</span>
              <PercentileBadge value={playerB.pts_percentile} />
            </div>
            <div className="flex items-center justify-between">
              <PercentileBadge value={playerA.ts_percentile} />
              <span className="text-gray-400">True Shooting</span>
              <PercentileBadge value={playerB.ts_percentile} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
