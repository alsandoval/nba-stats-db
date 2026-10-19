"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { CourtSVG } from "@/components/court-svg";
import { DataService, ShotResult, ShotProfileEntity } from "@/lib/data-service";

export default function ShotsPage() {
  const allPlayers = useMemo(() => DataService.getAllShotPlayers(), []);
  const allTeams = useMemo(() => DataService.getAllShotTeams(), []);

  const [activeTab, setActiveTab] = useState<"player" | "team" | "simulator">("player");
  const [courtViewMode, setCourtViewMode] = useState<"both" | "zones" | "dots">("both");
  const [shotFilter, setShotFilter] = useState<"all" | "made" | "missed" | "3pt">("all");
  const [teamFilter, setTeamFilter] = useState<string>("ALL");
  const [playerSearch, setPlayerSearch] = useState<string>("");
  const [selectedPlayerId, setSelectedPlayerId] = useState<number>(
    allPlayers.find((p) => p.id === 1628983)?.id || allPlayers[0]?.id || 2544
  );
  const [selectedTeamAbbr, setSelectedTeamAbbr] = useState<string>(allTeams[0]?.abbr || "BOS");
  const [profile, setProfile] = useState<ShotProfileEntity | null>(null);
  const [clickedShot, setClickedShot] = useState<ShotResult | null>(null);

  // Deep-link URL query parameter support (?player=203999 or ?team=BOS)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const pParam = params.get("player");
    const tParam = params.get("team");
    if (pParam) {
      const pid = Number(pParam);
      if (allPlayers.some((p) => p.id === pid)) {
        setActiveTab("player");
        setTeamFilter("ALL");
        setPlayerSearch("");
        setSelectedPlayerId(pid);
      }
    } else if (tParam) {
      const abbr = tParam.toUpperCase();
      if (allTeams.some((t) => t.abbr.toUpperCase() === abbr)) {
        setActiveTab("team");
        setSelectedTeamAbbr(abbr);
      }
    }
  }, [allPlayers, allTeams]);

  const uniqueTeams = useMemo(
    () => Array.from(new Set(allPlayers.map((p) => p.team).filter(Boolean))).sort(),
    [allPlayers]
  );

  const filteredPlayers = useMemo(() => {
    return allPlayers.filter((p) => {
      if (teamFilter !== "ALL" && p.team !== teamFilter) return false;
      if (playerSearch) {
        const q = playerSearch.toLowerCase();
        if (!p.name.toLowerCase().includes(q) && !p.team.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [allPlayers, teamFilter, playerSearch]);

  useEffect(() => {
    if (filteredPlayers.length > 0 && !filteredPlayers.some((p) => p.id === selectedPlayerId)) {
      setSelectedPlayerId(filteredPlayers[0].id);
    }
  }, [filteredPlayers, selectedPlayerId]);

  useEffect(() => {
    if (activeTab === "team") {
      setProfile(DataService.getShotProfile(selectedTeamAbbr));
    } else {
      setProfile(DataService.getShotProfile(selectedPlayerId));
    }
  }, [activeTab, selectedPlayerId, selectedTeamAbbr]);

  const handleCourtClick = (x: number, y: number) => {
    const evalResult = DataService.evaluateShot(x, y, 1, 360.0);
    setClickedShot(evalResult);
  };

  const summary = profile?.summary;
  const zones = profile?.zones || {};

  const displayedShots = useMemo(() => {
    const raw = profile?.shots || [];
    if (shotFilter === "made") return raw.filter((s) => s.made === 1);
    if (shotFilter === "missed") return raw.filter((s) => s.made === 0);
    if (shotFilter === "3pt") return raw.filter((s) => s.is_3pt === 1);
    return raw;
  }, [profile, shotFilter]);

  return (
    <div className="space-y-6">
      {/* Title & Diagnostic Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-2">
            <span>🎯</span> Spatial Shot Quality, 6-Zone Heatmap &amp; SMOE Atlas
          </h1>
          <p className="text-sm text-gray-400 mt-1 font-mono">
            Complete NBA Court Zone Tracking across All {allPlayers.length} Players &amp; All{" "}
            {allTeams.length} Franchises (Restricted Area, Paint, Mid-Range, Corner 3, ATB 3)
          </p>
        </div>

        {/* View Mode Tabs */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex bg-surfaceCard rounded-xl p-0.5 border border-borderDark text-xs font-mono">
            <button
              onClick={() => setActiveTab("player")}
              className={`px-3 py-1.5 rounded-lg transition ${
                activeTab === "player"
                  ? "bg-accent text-white font-bold shadow-glow"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              All {allPlayers.length} Players
            </button>
            <button
              onClick={() => setActiveTab("team")}
              className={`px-3 py-1.5 rounded-lg transition ${
                activeTab === "team"
                  ? "bg-accent text-white font-bold shadow-glow"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              All {allTeams.length} Teams
            </button>
            <button
              onClick={() => setActiveTab("simulator")}
              className={`px-3 py-1.5 rounded-lg transition ${
                activeTab === "simulator"
                  ? "bg-accent text-white font-bold shadow-glow"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Interactive Click Court
            </button>
          </div>
        </div>
      </div>

      {/* Player / Team Filter & Selector Bar */}
      {activeTab !== "simulator" && (
        <div className="bg-surfaceCard border border-borderDark rounded-2xl p-4 shadow-lg">
          {activeTab === "player" ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
              <div>
                <label className="block text-xs font-mono text-gray-400 mb-1">
                  Search Any NBA Player ({filteredPlayers.length} matching)
                </label>
                <input
                  type="text"
                  placeholder="Type player name (e.g. Curry, Wemby, Brunson)..."
                  value={playerSearch}
                  onChange={(e) => setPlayerSearch(e.target.value)}
                  className="w-full bg-surface border border-borderDark rounded-xl px-3.5 py-2 text-xs font-mono text-white placeholder-gray-500 focus:outline-none focus:border-accent"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-gray-400 mb-1">Filter by Team</label>
                <select
                  value={teamFilter}
                  onChange={(e) => setTeamFilter(e.target.value)}
                  className="w-full bg-surface border border-borderDark rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-accent"
                >
                  <option value="ALL">All 30 NBA Franchises</option>
                  {uniqueTeams.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-gray-400 mb-1">
                  Select Player Profile
                </label>
                <select
                  value={selectedPlayerId}
                  onChange={(e) => setSelectedPlayerId(Number(e.target.value))}
                  className="w-full bg-surface border border-accent/50 rounded-xl px-3.5 py-2 text-xs font-mono font-bold text-white focus:outline-none focus:border-accent"
                >
                  {filteredPlayers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.team} • {p.fga} FGA • SMOE{" "}
                      {p.smoe >= 0 ? `+${(p.smoe * 100).toFixed(1)}%` : `${(p.smoe * 100).toFixed(1)}%`})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ) : (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <span className="text-xs font-mono text-gray-400 block">
                  Franchise Spatial Shot Distribution (All 30 Teams)
                </span>
                <h3 className="text-base font-bold text-white">
                  Select any NBA team to inspect team-wide court zone shooting splits &amp; SMOE
                </h3>
              </div>
              <select
                value={selectedTeamAbbr}
                onChange={(e) => setSelectedTeamAbbr(e.target.value)}
                className="bg-surface border border-accent/50 rounded-xl px-4 py-2 text-xs font-mono font-bold text-white focus:outline-none focus:border-accent min-w-[280px]"
              >
                {allTeams.map((t) => (
                  <option key={t.abbr} value={t.abbr}>
                    {t.name} ({t.abbr} • {t.fga.toLocaleString()} FGA • SMOE{" "}
                    {t.smoe >= 0 ? `+${(t.smoe * 100).toFixed(1)}%` : `${(t.smoe * 100).toFixed(1)}%`})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {/* Main Interactive Stage */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Interactive Court SVG Visualizer */}
        <div className="lg:col-span-2 bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl flex flex-col items-center">
          <div className="w-full flex flex-wrap items-center justify-between gap-3 mb-4 text-xs font-mono text-gray-400">
            <span className="font-bold text-white">
              {activeTab === "simulator"
                ? "Click anywhere on the court to simulate shot expectation"
                : `${profile?.name} Spatial Shot Distribution (${summary?.shots_analyzed.toLocaleString()} Total FGA)`}
            </span>

            {activeTab !== "simulator" && (
              <div className="flex flex-wrap items-center gap-2">
                {/* Court Layer Toggle */}
                <div className="flex bg-surface rounded-lg p-0.5 border border-borderDark text-[11px]">
                  {(
                    [
                      { id: "both", label: "💎 Heatmap + Dots" },
                      { id: "zones", label: "🔥 Zone Heatmap" },
                      { id: "dots", label: "🎯 Shot Dots" },
                    ] as const
                  ).map((m) => (
                    <button
                      key={m.id}
                      onClick={() => setCourtViewMode(m.id)}
                      className={`px-2 py-1 rounded transition ${
                        courtViewMode === m.id
                          ? "bg-accent text-white font-bold"
                          : "text-gray-400 hover:text-white"
                      }`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>

                {/* Shot Outcome Filter */}
                {courtViewMode !== "zones" && (
                  <div className="flex bg-surface rounded-lg p-0.5 border border-borderDark text-[11px]">
                    {(
                      [
                        { id: "all", label: "All" },
                        { id: "made", label: "Made" },
                        { id: "missed", label: "Miss" },
                        { id: "3pt", label: "3PT" },
                      ] as const
                    ).map((f) => (
                      <button
                        key={f.id}
                        onClick={() => setShotFilter(f.id)}
                        className={`px-2 py-1 rounded transition ${
                          shotFilter === f.id
                            ? "bg-surfaceCard text-accent font-bold border border-accent/40"
                            : "text-gray-400 hover:text-white"
                        }`}
                      >
                        {f.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Court Component */}
          <div className="w-full max-w-[650px] aspect-[50/47] rounded-xl overflow-hidden bg-surface border border-borderDark/60 shadow-inner p-2">
            <CourtSVG
              shots={activeTab !== "simulator" ? displayedShots : []}
              zones={activeTab !== "simulator" ? zones : undefined}
              viewMode={activeTab !== "simulator" ? courtViewMode : "dots"}
              onCourtClick={handleCourtClick}
              clickedPoint={
                clickedShot ? { x: clickedShot.shot_x, y: clickedShot.shot_y } : undefined
              }
            />
          </div>

          <div className="w-full flex flex-wrap items-center justify-between gap-2 mt-3 text-[11px] font-mono text-gray-500">
            <span>
              Standard NBA Dimensions: 50ft width &middot; 47ft half-court &middot; 23.75ft 3PT arc &middot; 22ft corners
            </span>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1 text-emerald-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400" /> Made / Hot Zone
              </span>
              <span className="flex items-center gap-1 text-red-400">
                <span className="w-2 h-2 rounded-full bg-red-400" /> Missed / Cold Zone
              </span>
            </div>
          </div>
        </div>

        {/* Analytics & Zone Splits Card */}
        <div className="space-y-6">
          {activeTab === "simulator" ? (
            <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-5">
              <h3 className="font-bold text-white text-base flex items-center gap-2">
                <span>📍</span> Spatial Shot Evaluator
              </h3>

              {clickedShot ? (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-surface border border-borderDark text-center">
                    <span className="text-[10px] uppercase font-mono text-gray-400">
                      Make Probability (p̂)
                    </span>
                    <div className="text-4xl font-extrabold font-mono text-emerald-400 mt-1">
                      {(clickedShot.make_probability * 100).toFixed(1)}%
                    </div>
                    <span className="text-xs text-gray-400 font-mono mt-1 block">
                      {clickedShot.shot_dist >= 23.75 ||
                      (Math.abs(clickedShot.shot_x) >= 22 && clickedShot.shot_y <= 14)
                        ? "3-Point Attempt"
                        : "2-Point Attempt"}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                    <div className="p-3 rounded-xl bg-surface border border-borderDark">
                      <span className="text-gray-400 block text-[10px]">Shot Distance</span>
                      <span className="text-base font-bold text-white">
                        {clickedShot.shot_dist} ft
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-surface border border-borderDark">
                      <span className="text-gray-400 block text-[10px]">Expected Points</span>
                      <span className="text-base font-bold text-cyan-400">
                        {clickedShot.expected_points.toFixed(2)} pts
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-surface border border-borderDark">
                      <span className="text-gray-400 block text-[10px]">Expected eFG%</span>
                      <span className="text-base font-bold text-white">
                        {(clickedShot.x_efg_pct * 100).toFixed(1)}%
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-surface border border-borderDark">
                      <span className="text-gray-400 block text-[10px]">Shot Angle</span>
                      <span className="text-base font-bold text-white">
                        {clickedShot.shot_angle}&deg;
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="py-16 text-center text-xs font-mono text-gray-500 border border-dashed border-borderDark rounded-xl p-4">
                  Click any location on the court to inspect expected conversion probability and point value.
                </div>
              )}
            </div>
          ) : (
            <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-5">
              <div className="flex items-center justify-between border-b border-borderDark pb-3">
                <div>
                  <h3 className="font-bold text-white text-base">{profile?.name}</h3>
                  <span className="text-xs font-mono text-gray-400">
                    {summary?.total_fgm?.toLocaleString() || 0} /{" "}
                    {summary?.total_fga?.toLocaleString() || summary?.shots_analyzed} FGM-FGA •{" "}
                    {summary?.total_3pm?.toLocaleString() || 0} 3PM
                  </span>
                </div>
                <span className="text-xs font-mono px-2.5 py-1 rounded bg-surface border border-borderDark text-accent font-bold">
                  {profile?.team || profile?.abbreviation}
                </span>
              </div>

              {summary && (
                <div className="space-y-4">
                  {/* SMOE Metric Highlight */}
                  <div className="p-4 rounded-xl bg-gradient-to-br from-surface to-surfaceCard border border-borderDark text-center">
                    <span className="text-[10px] uppercase font-mono text-gray-400">
                      Shot-Making Over Expected (SMOE)
                    </span>
                    <div
                      className={`text-3xl font-extrabold font-mono mt-1 ${
                        summary.smoe >= 0 ? "text-emerald-400" : "text-red-400"
                      }`}
                    >
                      {summary.smoe > 0
                        ? `+${(summary.smoe * 100).toFixed(1)}%`
                        : `${(summary.smoe * 100).toFixed(1)}%`}
                    </div>
                    <span className="text-[11px] text-gray-400 font-mono mt-1 block">
                      Actual eFG% vs Zone-Weighted Expected eFG%
                    </span>
                  </div>

                  {/* Summary Grid */}
                  <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                    <div className="p-3 rounded-xl bg-surface border border-borderDark">
                      <span className="text-gray-400 block text-[10px]">Actual eFG%</span>
                      <span className="text-base font-bold text-white">
                        {(summary.actual_efg_pct * 100).toFixed(1)}%
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-surface border border-borderDark">
                      <span className="text-gray-400 block text-[10px]">Expected eFG%</span>
                      <span className="text-base font-bold text-cyan-400">
                        {(summary.x_efg_pct * 100).toFixed(1)}%
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-surface border border-borderDark">
                      <span className="text-gray-400 block text-[10px]">Actual Pts / Shot</span>
                      <span className="text-base font-bold text-white">
                        {summary.actual_points_per_shot.toFixed(2)}
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-surface border border-borderDark">
                      <span className="text-gray-400 block text-[10px]">Exp Pts / Shot</span>
                      <span className="text-base font-bold text-white">
                        {summary.expected_points_per_shot.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* 6-Zone Real NBA Shooting Breakdown */}
              {Object.keys(zones).length > 0 && (
                <div className="pt-2 border-t border-borderDark space-y-2">
                  <h4 className="text-xs font-mono uppercase text-gray-400 font-bold">
                    Official NBA Court Zone Splits
                  </h4>
                  <div className="space-y-1.5 text-xs font-mono">
                    {[
                      "Restricted Area",
                      "In The Paint (Non-RA)",
                      "Mid-Range",
                      "Left Corner 3",
                      "Right Corner 3",
                      "Above the Break 3",
                    ].map((zName) => {
                      const z = zones[zName];
                      if (!z) return null;
                      const diff = (z.fg_pct - z.exp_pct) * 100;
                      const fgaShare =
                        summary?.total_fga && summary.total_fga > 0
                          ? ((z.fga / summary.total_fga) * 100).toFixed(1)
                          : "0.0";
                      return (
                        <div
                          key={zName}
                          className="p-2.5 rounded-xl bg-surface border border-borderDark/70 space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <span className="text-gray-200 font-semibold block text-[11px]">
                                {zName}
                              </span>
                              <span className="text-[10px] text-gray-500">
                                {z.fgm} / {z.fga} FGA ({fgaShare}% freq)
                              </span>
                            </div>
                            <div className="text-right">
                              <span className="font-bold text-white block">
                                {(z.fg_pct * 100).toFixed(1)}%
                              </span>
                              <span
                                className={`text-[10px] font-bold ${
                                  diff >= 0 ? "text-emerald-400" : "text-red-400"
                                }`}
                              >
                                {diff >= 0 ? `+${diff.toFixed(1)}%` : `${diff.toFixed(1)}%`} vs Avg
                              </span>
                            </div>
                          </div>
                          <div className="w-full h-1.5 bg-surfaceCard rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                diff >= 0 ? "bg-emerald-500" : "bg-red-500"
                              }`}
                              style={{ width: `${Math.min(100, Number(fgaShare) * 1.8)}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {activeTab === "player" && selectedPlayerId && (
                <div className="pt-2 border-t border-borderDark flex items-center gap-2 text-xs font-mono">
                  <Link
                    href={`/rapm?player=${selectedPlayerId}`}
                    className="flex-1 py-2 text-center rounded-xl bg-surface hover:bg-surfaceElevated border border-borderDark text-gray-300 hover:text-white font-bold transition"
                  >
                    📈 RAPM Dossier
                  </Link>
                  <Link
                    href={`/compare?p1=${selectedPlayerId}`}
                    className="flex-1 py-2 text-center rounded-xl bg-accent/20 hover:bg-accent/30 border border-accent/40 text-accent font-bold transition"
                  >
                    ⚔️ Compare Player
                  </Link>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
