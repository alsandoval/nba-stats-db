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
  const [careerA, setCareerA] = useState<Player[]>([]);
  const [careerB, setCareerB] = useState<Player[]>([]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const p1 = params.get("p1");
      const s1 = params.get("s1");
      const p2 = params.get("p2");
      const s2 = params.get("s2");
      if (s1 && SEASONS_10YR.includes(s1 as any)) setSeasonA(s1);
      if (p1 && !isNaN(Number(p1))) setPlayerAId(Number(p1));
      if (s2 && SEASONS_10YR.includes(s2 as any)) setSeasonB(s2);
      if (p2 && !isNaN(Number(p2))) setPlayerBId(Number(p2));
    }
  }, []);

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

  useEffect(() => {
    if (playerA) {
      setCareerA(DataService.getPlayerCareerHistory(playerA.player_id));
    }
  }, [playerA]);

  useEffect(() => {
    if (playerB) {
      setCareerB(DataService.getPlayerCareerHistory(playerB.player_id));
    }
  }, [playerB]);

  const shotA = useMemo(
    () => (playerA ? DataService.getShotProfile(playerA.player_id) : null),
    [playerA]
  );
  const shotB = useMemo(
    () => (playerB ? DataService.getShotProfile(playerB.player_id) : null),
    [playerB]
  );

  // 6-Axis Radar Polygon helper
  const radarAxes = useMemo(() => {
    if (!playerA || !playerB) return [];
    return [
      { label: "Scoring", a: playerA.pts_percentile ?? 50, b: playerB.pts_percentile ?? 50 },
      { label: "Playmaking", a: playerA.ast_percentile ?? 50, b: playerB.ast_percentile ?? 50 },
      { label: "True Shooting", a: playerA.ts_percentile ?? 50, b: playerB.ts_percentile ?? 50 },
      { label: "Off. RAPM", a: playerA.orapm_percentile ?? 50, b: playerB.orapm_percentile ?? 50 },
      { label: "Def. RAPM", a: playerA.drapm_percentile ?? 50, b: playerB.drapm_percentile ?? 50 },
      { label: "Total Impact", a: playerA.rapm_percentile ?? 50, b: playerB.rapm_percentile ?? 50 },
    ];
  }, [playerA, playerB]);

  const renderRadarSVG = () => {
    if (!radarAxes.length) return null;
    const cx = 150;
    const cy = 140;
    const maxR = 95;
    const levels = [25, 50, 75, 100];

    const pointFor = (idx: number, pct: number) => {
      const angle = (Math.PI * 2 * idx) / radarAxes.length - Math.PI / 2;
      const r = (Math.max(5, Math.min(100, pct)) / 100) * maxR;
      return {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
      };
    };

    const polyA = radarAxes
      .map((ax, i) => {
        const pt = pointFor(i, ax.a);
        return `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`;
      })
      .join(" ");

    const polyB = radarAxes
      .map((ax, i) => {
        const pt = pointFor(i, ax.b);
        return `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`;
      })
      .join(" ");

    return (
      <svg viewBox="0 0 300 280" className="w-full max-w-[320px] mx-auto select-none">
        {/* Hexagonal Grid Rings */}
        {levels.map((lvl) => {
          const pts = radarAxes
            .map((_, i) => {
              const p = pointFor(i, lvl);
              return `${p.x.toFixed(1)},${p.y.toFixed(1)}`;
            })
            .join(" ");
          return (
            <polygon
              key={lvl}
              points={pts}
              fill="none"
              stroke="#1e293b"
              strokeWidth={lvl === 100 ? "1.5" : "1"}
              strokeDasharray={lvl === 50 ? "3 3" : undefined}
            />
          );
        })}

        {/* Axis Spokes & Labels */}
        {radarAxes.map((ax, i) => {
          const outer = pointFor(i, 100);
          const lbl = pointFor(i, 122);
          return (
            <g key={ax.label}>
              <line
                x1={cx}
                y1={cy}
                x2={outer.x}
                y2={outer.y}
                stroke="#1e293b"
                strokeWidth="1"
              />
              <text
                x={lbl.x}
                y={lbl.y + 3}
                textAnchor="middle"
                fill="#94a3b8"
                fontSize="9.5"
                fontWeight="700"
                className="font-mono"
              >
                {ax.label}
              </text>
            </g>
          );
        })}

        {/* Player B Polygon (Cyan) */}
        <polygon
          points={polyB}
          fill="rgba(34, 211, 238, 0.22)"
          stroke="#22d3ee"
          strokeWidth="2.2"
        />
        {/* Player A Polygon (Accent Blue/Indigo) */}
        <polygon
          points={polyA}
          fill="rgba(59, 130, 246, 0.28)"
          stroke="#3b82f6"
          strokeWidth="2.4"
        />

        {/* Vertex Dots */}
        {radarAxes.map((ax, i) => {
          const ptA = pointFor(i, ax.a);
          const ptB = pointFor(i, ax.b);
          return (
            <g key={`dots-${i}`}>
              <circle cx={ptB.x} cy={ptB.y} r="3.5" fill="#22d3ee" />
              <circle cx={ptA.x} cy={ptA.y} r="3.5" fill="#3b82f6" />
            </g>
          );
        })}
      </svg>
    );
  };

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
            <span>👥</span> 10-Season Cross-Era Player Comparison &amp; Radar Studio
          </h1>
          <p className="text-sm text-gray-400 mt-1 font-mono">
            Compare any two player-seasons (2015-16 to 2024-25) across 6-Axis Radar Percentiles, RAPM, Hustle, Clutch &amp; 10-Yr Career Arcs.
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
          {/* Top Banner Cards + 6-Axis Radar Chart */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center border-b border-borderDark pb-6">
            <div className="space-y-2 text-center lg:text-left p-4 rounded-xl bg-surface border border-accent/40">
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-accent/20 text-accent border border-accent/40 font-bold">
                {seasonA} • {playerA.team_abbreviation}
              </span>
              <h3 className="text-xl font-extrabold text-white">{playerA.full_name}</h3>
              <p className="text-xs font-mono text-gray-400">
                {playerA.height || "6-7"} &middot; {playerA.weight ? `${playerA.weight} lbs` : "220 lbs"} &middot;{" "}
                {playerA.gp} GP &middot; {playerA.min_per_game} MPG
              </p>
              <div className="flex flex-wrap gap-1.5 justify-center lg:justify-start pt-1">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surfaceCard border border-borderDark text-cyan-300">
                  {playerA.offensive_archetype}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surfaceCard border border-borderDark text-emerald-300">
                  {playerA.defensive_archetype}
                </span>
              </div>
            </div>

            {/* Center 6-Axis Radar Polygon Overlay */}
            <div className="flex flex-col items-center">
              <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400 mb-1">
                6-Axis Percentile Radar Overlay
              </span>
              {renderRadarSVG()}
              <div className="flex items-center gap-4 text-[11px] font-mono mt-1">
                <span className="flex items-center gap-1.5 text-accent font-bold">
                  <span className="w-2.5 h-2.5 rounded-full bg-accent inline-block" />
                  {playerA.full_name} ({seasonA})
                </span>
                <span className="flex items-center gap-1.5 text-cyan-400 font-bold">
                  <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 inline-block" />
                  {playerB.full_name} ({seasonB})
                </span>
              </div>
            </div>

            <div className="space-y-2 text-center lg:text-right p-4 rounded-xl bg-surface border border-cyan-400/40">
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-cyan-400/20 text-cyan-400 border border-cyan-400/40 font-bold">
                {seasonB} • {playerB.team_abbreviation}
              </span>
              <h3 className="text-xl font-extrabold text-white">{playerB.full_name}</h3>
              <p className="text-xs font-mono text-gray-400">
                {playerB.height || "6-7"} &middot; {playerB.weight ? `${playerB.weight} lbs` : "220 lbs"} &middot;{" "}
                {playerB.gp} GP &middot; {playerB.min_per_game} MPG
              </p>
              <div className="flex flex-wrap gap-1.5 justify-center lg:justify-end pt-1">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surfaceCard border border-borderDark text-cyan-300">
                  {playerB.offensive_archetype}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surfaceCard border border-borderDark text-emerald-300">
                  {playerB.defensive_archetype}
                </span>
              </div>
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
            {renderComparisonBar(
              "Deflections Per Game",
              playerA.deflections_pg || 1.2,
              playerB.deflections_pg || 1.2,
              false,
              1
            )}
            {renderComparisonBar(
              "Contested Shots Per Game",
              playerA.contested_pg || 4.5,
              playerB.contested_pg || 4.5,
              false,
              1
            )}
            {renderComparisonBar(
              "Clutch Time Points",
              playerA.clutch_pts || 0,
              playerB.clutch_pts || 0,
              false,
              0
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

          {/* 10-Season Career Trajectory Side-by-Side */}
          <div className="pt-6 border-t border-borderDark grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-2">
              <h4 className="text-xs font-mono uppercase tracking-wider text-accent font-bold">
                📅 {playerA.full_name} 10-Yr Career Arc ({careerA.length} Seasons)
              </h4>
              <div className="overflow-x-auto max-h-48 overflow-y-auto rounded-xl border border-borderDark">
                <table className="w-full text-left font-mono text-[11px]">
                  <thead className="bg-surface text-gray-400 uppercase border-b border-borderDark sticky top-0">
                    <tr>
                      <th className="py-1.5 px-2">Season</th>
                      <th className="py-1.5 px-2">Tm</th>
                      <th className="py-1.5 px-2 text-right">PPG</th>
                      <th className="py-1.5 px-2 text-right">APG</th>
                      <th className="py-1.5 px-2 text-right">TS%</th>
                      <th className="py-1.5 px-2 text-right">RAPM</th>
                      <th className="py-1.5 px-2 text-right">Wins</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-borderDark/40">
                    {careerA.map((c) => (
                      <tr
                        key={`${c.season}-${c.team_abbreviation}`}
                        onClick={() => setSeasonA(c.season || "2023-24")}
                        className={`cursor-pointer transition ${
                          c.season === seasonA ? "bg-accent/15 text-white font-bold" : "hover:bg-surface/60 text-gray-300"
                        }`}
                      >
                        <td className="py-1 px-2 text-accent font-bold">{c.season}</td>
                        <td className="py-1 px-2">{c.team_abbreviation}</td>
                        <td className="py-1 px-2 text-right">{c.pts}</td>
                        <td className="py-1 px-2 text-right">{c.ast}</td>
                        <td className="py-1 px-2 text-right">{(c.ts_pct * 100).toFixed(1)}%</td>
                        <td className={`py-1 px-2 text-right ${c.rapm >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                          {c.rapm >= 0 ? `+${c.rapm.toFixed(2)}` : c.rapm.toFixed(2)}
                        </td>
                        <td className="py-1 px-2 text-right text-amber-300">{(c.wins_added ?? 0).toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-mono uppercase tracking-wider text-cyan-400 font-bold">
                📅 {playerB.full_name} 10-Yr Career Arc ({careerB.length} Seasons)
              </h4>
              <div className="overflow-x-auto max-h-48 overflow-y-auto rounded-xl border border-borderDark">
                <table className="w-full text-left font-mono text-[11px]">
                  <thead className="bg-surface text-gray-400 uppercase border-b border-borderDark sticky top-0">
                    <tr>
                      <th className="py-1.5 px-2">Season</th>
                      <th className="py-1.5 px-2">Tm</th>
                      <th className="py-1.5 px-2 text-right">PPG</th>
                      <th className="py-1.5 px-2 text-right">APG</th>
                      <th className="py-1.5 px-2 text-right">TS%</th>
                      <th className="py-1.5 px-2 text-right">RAPM</th>
                      <th className="py-1.5 px-2 text-right">Wins</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-borderDark/40">
                    {careerB.map((c) => (
                      <tr
                        key={`${c.season}-${c.team_abbreviation}`}
                        onClick={() => setSeasonB(c.season || "2023-24")}
                        className={`cursor-pointer transition ${
                          c.season === seasonB ? "bg-cyan-400/15 text-white font-bold" : "hover:bg-surface/60 text-gray-300"
                        }`}
                      >
                        <td className="py-1 px-2 text-cyan-400 font-bold">{c.season}</td>
                        <td className="py-1 px-2">{c.team_abbreviation}</td>
                        <td className="py-1 px-2 text-right">{c.pts}</td>
                        <td className="py-1 px-2 text-right">{c.ast}</td>
                        <td className="py-1 px-2 text-right">{(c.ts_pct * 100).toFixed(1)}%</td>
                        <td className={`py-1 px-2 text-right ${c.rapm >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                          {c.rapm >= 0 ? `+${c.rapm.toFixed(2)}` : c.rapm.toFixed(2)}
                        </td>
                        <td className="py-1 px-2 text-right text-amber-300">{(c.wins_added ?? 0).toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
