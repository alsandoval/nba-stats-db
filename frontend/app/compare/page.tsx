"use client";

import React, { useEffect, useState, useMemo } from "react";
import { DataService, Player, SEASONS_10YR } from "@/lib/data-service";
import { PercentileBadge } from "@/components/virtual-table";

const PRESETS = [
  { name: "'24 Jokic vs '24 Luka", seasonA: "2023-24", idA: 203999, seasonB: "2023-24", idB: 1629029 },
  { name: "'16 Curry vs '24 Jokic", seasonA: "2015-16", idA: 201939, seasonB: "2023-24", idB: 203999 },
  { name: "'16 LeBron vs '24 Tatum", seasonA: "2015-16", idA: 2544, seasonB: "2023-24", idB: 1628369 },
  { name: "'24 Giannis vs '24 SGA", seasonA: "2023-24", idA: 203507, seasonB: "2023-24", idB: 1628983 },
];

export default function ComparePage() {
  const [seasonA, setSeasonA] = useState<string>("2023-24");
  const [seasonB, setSeasonB] = useState<string>("2023-24");
  const [playersA, setPlayersA] = useState<Player[]>([]);
  const [playersB, setPlayersB] = useState<Player[]>([]);
  const [searchA, setSearchA] = useState<string>("");
  const [searchB, setSearchB] = useState<string>("");
  const [playerAId, setPlayerAId] = useState<number>(203999); // Jokic
  const [playerBId, setPlayerBId] = useState<number>(1629029); // Luka

  useEffect(() => {
    DataService.getPlayers(seasonA).then(setPlayersA);
  }, [seasonA]);

  useEffect(() => {
    DataService.getPlayers(seasonB).then(setPlayersB);
  }, [seasonB]);

  const filteredA = useMemo(() => {
    if (!searchA) return playersA;
    const q = searchA.toLowerCase();
    return playersA.filter(
      (p) =>
        p.full_name.toLowerCase().includes(q) ||
        p.team_abbreviation.toLowerCase().includes(q)
    );
  }, [playersA, searchA]);

  const filteredB = useMemo(() => {
    if (!searchB) return playersB;
    const q = searchB.toLowerCase();
    return playersB.filter(
      (p) =>
        p.full_name.toLowerCase().includes(q) ||
        p.team_abbreviation.toLowerCase().includes(q)
    );
  }, [playersB, searchB]);

  const playerA = playersA.find((p) => p.player_id === playerAId) || filteredA[0] || playersA[0];
  const playerB = playersB.find((p) => p.player_id === playerBId) || filteredB[0] || playersB[1];

  const shotA = useMemo(
    () => (playerA ? DataService.getShotProfile(playerA.player_id) : null),
    [playerA]
  );
  const shotB = useMemo(
    () => (playerB ? DataService.getShotProfile(playerB.player_id) : null),
    [playerB]
  );

  const renderComparisonBar = (
    label: string,
    valA: number,
    valB: number,
    isPct: boolean = false,
    decimals: number = 1
  ) => {
    const isAWinner = valA > valB;
    const isBWinner = valB > valA;
    const maxVal = Math.max(Math.abs(valA), Math.abs(valB), 0.01) * 1.15;
    const widthA = Math.min(100, Math.max(8, (Math.abs(valA) / maxVal) * 100));
    const widthB = Math.min(100, Math.max(8, (Math.abs(valB) / maxVal) * 100));

    const fmt = (v: number) =>
      isPct ? `${(v * 100).toFixed(decimals)}%` : v.toFixed(decimals);

    return (
      <div className="space-y-1.5 py-2.5 border-b border-borderDark/40">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className={`font-bold ${isAWinner ? "text-emerald-400" : "text-gray-300"}`}>
            {fmt(valA)}
          </span>
          <span className="text-gray-400 font-bold uppercase text-[11px] tracking-wider">
            {label}
          </span>
          <span className={`font-bold ${isBWinner ? "text-emerald-400" : "text-gray-300"}`}>
            {fmt(valB)}
          </span>
        </div>

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
            <span>👥</span> 10-Season Cross-Era Player Comparison Studio
          </h1>
          <p className="text-sm text-gray-400 mt-1 font-mono">
            Compare any two player-seasons from 2015-16 through 2024-25 across RAPM, LEBRON, Archetypes &amp; Zone Shooting.
          </p>
        </div>

        {/* Presets */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-mono text-gray-400 mr-1">Marquee Matchups:</span>
          {PRESETS.map((pr) => (
            <button
              key={pr.name}
              onClick={() => {
                setSeasonA(pr.seasonA);
                setPlayerAId(pr.idA);
                setSeasonB(pr.seasonB);
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
        <div className="p-5 bg-surfaceCard border border-borderDark rounded-2xl shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-accent font-extrabold">
              Player A ({playersA.length} in {seasonA})
            </span>
            <select
              value={seasonA}
              onChange={(e) => setSeasonA(e.target.value)}
              className="bg-surface border border-accent/50 rounded-lg px-2.5 py-1 text-xs font-mono font-bold text-white"
            >
              {SEASONS_10YR.map((s) => (
                <option key={s} value={s}>
                  {s} Season
                </option>
              ))}
            </select>
          </div>
          <input
            type="text"
            placeholder="Filter Player A by name or team..."
            value={searchA}
            onChange={(e) => setSearchA(e.target.value)}
            className="w-full bg-surface border border-borderDark rounded-xl px-3 py-1.5 text-xs font-mono text-white placeholder-gray-500"
          />
          <select
            value={playerA?.player_id || playerAId}
            onChange={(e) => setPlayerAId(Number(e.target.value))}
            className="w-full bg-surface border border-borderDark rounded-xl p-2.5 text-sm font-bold text-white focus:outline-none focus:border-accent"
          >
            {filteredA.map((p) => (
              <option key={p.player_id} value={p.player_id}>
                {p.full_name} ({p.team_abbreviation} • {p.pts} PPG • RAPM{" "}
                {p.rapm >= 0 ? `+${p.rapm}` : p.rapm})
              </option>
            ))}
          </select>
        </div>

        {/* Player B Selector */}
        <div className="p-5 bg-surfaceCard border border-borderDark rounded-2xl shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-cyan-400 font-extrabold">
              Player B ({playersB.length} in {seasonB})
            </span>
            <select
              value={seasonB}
              onChange={(e) => setSeasonB(e.target.value)}
              className="bg-surface border border-cyan-400/50 rounded-lg px-2.5 py-1 text-xs font-mono font-bold text-white"
            >
              {SEASONS_10YR.map((s) => (
                <option key={s} value={s}>
                  {s} Season
                </option>
              ))}
            </select>
          </div>
          <input
            type="text"
            placeholder="Filter Player B by name or team..."
            value={searchB}
            onChange={(e) => setSearchB(e.target.value)}
            className="w-full bg-surface border border-borderDark rounded-xl px-3 py-1.5 text-xs font-mono text-white placeholder-gray-500"
          />
          <select
            value={playerB?.player_id || playerBId}
            onChange={(e) => setPlayerBId(Number(e.target.value))}
            className="w-full bg-surface border border-borderDark rounded-xl p-2.5 text-sm font-bold text-white focus:outline-none focus:border-cyan-400"
          >
            {filteredB.map((p) => (
              <option key={p.player_id} value={p.player_id}>
                {p.full_name} ({p.team_abbreviation} • {p.pts} PPG • RAPM{" "}
                {p.rapm >= 0 ? `+${p.rapm}` : p.rapm})
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
            <div className="space-y-1.5">
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-accent/20 text-accent border border-accent/40 font-bold">
                {seasonA} • {playerA.team_abbreviation}
              </span>
              <h3 className="text-xl font-extrabold text-white">{playerA.full_name}</h3>
              <p className="text-xs font-mono text-gray-400">
                {playerA.gp} GP &middot; {playerA.min_per_game} MPG &middot;{" "}
                {playerA.offensive_archetype}
              </p>
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-cyan-400/20 text-cyan-400 border border-cyan-400/40 font-bold">
                {seasonB} • {playerB.team_abbreviation}
              </span>
              <h3 className="text-xl font-extrabold text-white">{playerB.full_name}</h3>
              <p className="text-xs font-mono text-gray-400">
                {playerB.gp} GP &middot; {playerB.min_per_game} MPG &middot;{" "}
                {playerB.offensive_archetype}
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
            {renderComparisonBar("Usage Rate (USG%)", playerA.usg_pct || 20, playerB.usg_pct || 20)}
            {renderComparisonBar("Field Goal %", playerA.fg_pct, playerB.fg_pct, true)}
            {renderComparisonBar("3-Point %", playerA.fg3_pct, playerB.fg3_pct, true)}
            {renderComparisonBar("On-Court Net Rating", playerA.net_rating, playerB.net_rating)}
            {renderComparisonBar("Offensive RAPM (ORAPM)", playerA.orapm, playerB.orapm, false, 2)}
            {renderComparisonBar("Defensive RAPM (DRAPM)", playerA.drapm, playerB.drapm, false, 2)}
            {renderComparisonBar("Total RAPM Impact", playerA.rapm, playerB.rapm, false, 2)}
            {renderComparisonBar(
              "Wins Added",
              playerA.wins_added || 0,
              playerB.wins_added || 0,
              false,
              1
            )}
            {shotA?.zones && shotB?.zones && (
              <>
                {renderComparisonBar(
                  "Restricted Area FG%",
                  shotA.zones["Restricted Area"]?.fg_pct || 0,
                  shotB.zones["Restricted Area"]?.fg_pct || 0,
                  true
                )}
                {renderComparisonBar(
                  "Mid-Range FG%",
                  shotA.zones["Mid-Range"]?.fg_pct || 0,
                  shotB.zones["Mid-Range"]?.fg_pct || 0,
                  true
                )}
                {renderComparisonBar(
                  "Above the Break 3 FG%",
                  shotA.zones["Above the Break 3"]?.fg_pct || 0,
                  shotB.zones["Above the Break 3"]?.fg_pct || 0,
                  true
                )}
              </>
            )}
          </div>

          {/* Percentile Badges Comparison */}
          <div className="max-w-2xl mx-auto pt-6 border-t border-borderDark space-y-3 font-mono text-xs">
            <h4 className="text-center font-bold text-gray-300 uppercase text-[11px] tracking-wider mb-3">
              Within-Season Percentile Rankings (0 - 100)
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
