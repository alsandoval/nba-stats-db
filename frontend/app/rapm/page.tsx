"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { VirtualTable, PercentileBadge } from "@/components/virtual-table";
import { DataService, RAPMPlayer, Player, SEASONS_10YR } from "@/lib/data-service";

const ARCHETYPE_COLORS: Record<string, string> = {
  "Primary Ballhandler": "#38bdf8",
  "Shot Creator": "#f59e0b",
  "Movement Shooter": "#10b981",
  "Off-Ball Finisher": "#a855f7",
  "Post Scorer": "#f43f5e",
  "Stretch Big": "#2dd4bf",
  "Roll & Cut Big": "#fb923c",
  "Connector / Wing": "#60a5fa",
};

export default function RAPMPage() {
  const [season, setSeason] = useState<string>("2023-24");
  const [viewMode, setViewMode] = useState<"table" | "galaxy">("table");
  const [galaxyAxes, setGalaxyAxes] = useState<"rapm" | "tsne">("rapm");
  const [players, setPlayers] = useState<RAPMPlayer[]>([]);
  const [allPlayersData, setAllPlayersData] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [teamFilter, setTeamFilter] = useState("ALL");
  const [archetypeFilter, setArchetypeFilter] = useState("ALL");
  const [lambdaReg, setLambdaReg] = useState(1200);
  const [minPoss, setMinPoss] = useState(0);
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [careerHistory, setCareerHistory] = useState<Player[]>([]);
  const [hoveredDot, setHoveredDot] = useState<Player | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      DataService.getRAPMLeaderboard(lambdaReg, season),
      DataService.getPlayers(season),
    ]).then(([rapmData, fullData]) => {
      setPlayers(rapmData);
      setAllPlayersData(fullData);
      setLoading(false);

      if (typeof window !== "undefined") {
        const params = new URLSearchParams(window.location.search);
        const qParam = params.get("q");
        const pParam = params.get("player");
        if (qParam) {
          setSearch(qParam);
          const match = fullData.find((p) =>
            p.full_name.toLowerCase().includes(qParam.toLowerCase())
          );
          if (match) setSelectedPlayer(match);
        } else if (pParam) {
          const pid = Number(pParam);
          const match = fullData.find((p) => p.player_id === pid);
          if (match) setSelectedPlayer(match);
        }
      }
    });
  }, [lambdaReg, season]);

  useEffect(() => {
    if (selectedPlayer) {
      setCareerHistory(DataService.getPlayerCareerHistory(selectedPlayer.player_id));
    } else {
      setCareerHistory([]);
    }
  }, [selectedPlayer]);

  const teams = useMemo(
    () => Array.from(new Set(players.map((p) => p.team_abbreviation).filter(Boolean))).sort(),
    [players]
  );

  const archetypes = useMemo(
    () =>
      Array.from(
        new Set(players.map((p) => p.offensive_archetype).filter(Boolean) as string[])
      ).sort(),
    [players]
  );

  const filtered = useMemo(() => {
    return players
      .filter((p) => p.possessions >= minPoss)
      .filter((p) => (teamFilter === "ALL" ? true : p.team_abbreviation === teamFilter))
      .filter((p) =>
        archetypeFilter === "ALL" ? true : p.offensive_archetype === archetypeFilter
      )
      .filter(
        (p) =>
          p.player_name.toLowerCase().includes(search.toLowerCase()) ||
          p.team_abbreviation.toLowerCase().includes(search.toLowerCase()) ||
          (p.offensive_archetype || "").toLowerCase().includes(search.toLowerCase())
      );
  }, [players, minPoss, teamFilter, archetypeFilter, search]);

  const filteredFullPlayers = useMemo(() => {
    const idSet = new Set(filtered.map((f) => `${f.player_id}-${f.season || season}`));
    return allPlayersData
      .filter((p) => idSet.has(`${p.player_id}-${p.season || season}`))
      .slice(0, 350);
  }, [allPlayersData, filtered, season]);

  const handleRowClick = (row: RAPMPlayer) => {
    const fullProfile = allPlayersData.find(
      (p) => p.player_id === row.player_id && (!row.season || p.season === row.season)
    );
    if (fullProfile) {
      setSelectedPlayer(fullProfile);
    }
  };

  const exportRAPMCSV = () => {
    const headers = [
      "Rank",
      "Season",
      "Player",
      "Team",
      "Archetype",
      "Possessions",
      "ORAPM",
      "DRAPM",
      "Total_RAPM",
      "Wins_Added",
      "Impact_Percentile",
    ];
    const rows = filtered.map((p, i) => [
      i + 1,
      p.season || season,
      `"${p.player_name}"`,
      p.team_abbreviation,
      `"${p.offensive_archetype || "All-Around"}"`,
      p.possessions,
      p.orapm.toFixed(2),
      p.drapm.toFixed(2),
      p.rapm.toFixed(2),
      (p.wins_added ?? 0).toFixed(2),
      p.rapm_percentile,
    ]);
    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `nba_rapm_${season}_lambda${lambdaReg}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const columns = [
    {
      key: "rank",
      header: "#",
      width: "52px",
      flex: 0,
      sortable: false,
      align: "center" as const,
      render: (val: number) => (
        <span className="font-mono text-xs text-gray-500 font-bold">{val}</span>
      ),
    },
    {
      key: "season",
      header: "Season",
      width: "85px",
      align: "center" as const,
      render: (val: string) => (
        <span className="font-mono text-[11px] text-gray-400">{val || season}</span>
      ),
    },
    {
      key: "player_name",
      header: "Player",
      width: "215px",
      flex: 1.7,
      render: (val: string, row: RAPMPlayer) => (
        <div className="flex items-center gap-2 group">
          <span className="font-bold text-white group-hover:text-accent transition truncate">
            {val}
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface border border-borderDark text-accent font-bold">
            {row.team_abbreviation}
          </span>
        </div>
      ),
    },
    {
      key: "offensive_archetype",
      header: "Offensive Archetype",
      width: "165px",
      flex: 1.3,
      render: (val: string) => (
        <span className="text-[11px] font-mono text-cyan-300 bg-cyan-950/30 border border-cyan-800/40 px-2 py-0.5 rounded truncate inline-block max-w-[165px]">
          {val || "All-Around"}
        </span>
      ),
    },
    {
      key: "possessions",
      header: "Poss",
      width: "85px",
      align: "right" as const,
      render: (val: number) => (
        <span className="font-mono text-xs text-gray-300">{val.toLocaleString()}</span>
      ),
    },
    {
      key: "orapm",
      header: "ORAPM",
      width: "85px",
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
      key: "drapm",
      header: "DRAPM",
      width: "85px",
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
      key: "rapm",
      header: "Total RAPM",
      width: "105px",
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
      key: "wins_added",
      header: "Wins Added",
      width: "100px",
      align: "right" as const,
      render: (val: number) => {
        const w = typeof val === "number" ? val : 0;
        return (
          <span className={`font-mono font-bold text-xs ${w >= 0 ? "text-amber-300" : "text-gray-400"}`}>
            {w > 0 ? `+${w.toFixed(1)}` : w.toFixed(1)}
          </span>
        );
      },
    },
    {
      key: "rapm_percentile",
      header: "Impact %ile",
      width: "120px",
      align: "center" as const,
      isPercentile: true,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Title & Diagnostic Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-2">
            <span>📈</span> 10-Season RAPM, LEBRON &amp; 3D Cluster Impact Hub
          </h1>
          <p className="text-sm text-gray-400 mt-1 font-mono">
            All 5,393 NBA Player-Seasons (2015-16 to 2024-25) with Sortable Virtual Grid, ORAPM&times;DRAPM Galaxy &amp; 10-Yr Career Arcs.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 text-xs font-mono">
          {/* View Mode Toggle: Table vs Galaxy Scatter */}
          <div className="flex bg-surfaceCard rounded-xl p-0.5 border border-borderDark">
            <button
              onClick={() => setViewMode("table")}
              className={`px-3 py-1.5 rounded-lg font-bold transition ${
                viewMode === "table"
                  ? "bg-accent text-white shadow-glow"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              📊 Virtual Grid ({filtered.length.toLocaleString()})
            </button>
            <button
              onClick={() => setViewMode("galaxy")}
              className={`px-3 py-1.5 rounded-lg font-bold transition ${
                viewMode === "galaxy"
                  ? "bg-accent text-white shadow-glow"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              🌌 Impact &amp; t-SNE Galaxy
            </button>
          </div>

          <select
            value={season}
            onChange={(e) => setSeason(e.target.value)}
            className="bg-surfaceCard border border-accent/50 rounded-xl px-3.5 py-1.5 text-xs font-mono font-extrabold text-white focus:outline-none focus:border-accent"
          >
            {SEASONS_10YR.map((s) => (
              <option key={s} value={s}>
                {s} Season
              </option>
            ))}
            <option value="ALL">ALL 10 Seasons (2015-16 to 2024-25 • 5,393 Rows)</option>
          </select>

          <button
            onClick={exportRAPMCSV}
            className="px-3.5 py-1.5 rounded-xl bg-surfaceCard hover:bg-surface border border-borderDark text-gray-300 hover:text-white font-bold transition"
          >
            ⬇ Export CSV
          </button>
        </div>
      </div>

      {/* Control Bar: Search, Filters, and Interactive Lambda Slider */}
      <div className="bg-surfaceCard border border-borderDark rounded-2xl p-5 shadow-lg space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Search Input */}
          <div>
            <label className="block text-xs font-mono text-gray-400 mb-1.5">
              Search Player / Team / Role
            </label>
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
              <option value="ALL">All Franchises</option>
              {teams.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          {/* Archetype Filter */}
          <div>
            <label className="block text-xs font-mono text-gray-400 mb-1.5">
              Offensive Archetype
            </label>
            <select
              value={archetypeFilter}
              onChange={(e) => setArchetypeFilter(e.target.value)}
              className="w-full bg-surface border border-borderDark rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-accent font-mono"
            >
              <option value="ALL">All Archetypes</option>
              {archetypes.map((arch) => (
                <option key={arch} value={arch}>
                  {arch}
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
              max="1500"
              step="50"
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

        <div className="flex flex-wrap items-center justify-between pt-2 border-t border-borderDark/40 text-xs text-gray-400 font-mono">
          <span>
            Showing <strong className="text-white">{filtered.length.toLocaleString()}</strong> players in{" "}
            <strong className="text-accent">{season === "ALL" ? "2015-16 to 2024-25" : season}</strong>
          </span>
          <span className="text-gray-400">
            💡 Click any column header to sort &middot; Click any player row or galaxy node to open 10-Yr Dossier
          </span>
        </div>
      </div>

      {/* Main Content Area: Virtualized Sortable Table OR Interactive Galaxy Scatter */}
      {viewMode === "table" ? (
        <div className="bg-surfaceCard border border-borderDark rounded-2xl p-4 shadow-xl">
          {loading ? (
            <div className="py-24 text-center font-mono text-sm text-gray-400 animate-pulse">
              Solving sparse normal equations (X^T W X + &lambda; I)^(-1)...
            </div>
          ) : (
            <VirtualTable
              data={filtered}
              columns={columns}
              height="600px"
              rowHeight={46}
              onRowClick={handleRowClick}
            />
          )}
        </div>
      ) : (
        <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-extrabold text-white flex items-center gap-2">
                <span>🌌</span>{" "}
                {galaxyAxes === "rapm"
                  ? "Two-Way Player Impact Quadrant Map (ORAPM vs DRAPM)"
                  : "3D t-SNE Position & Archetype Manifold Projection (t-SNE X vs Y)"}
              </h3>
              <p className="text-xs font-mono text-gray-400">
                Node size scales with Wins Added &middot; Colored by Offensive Archetype &middot; Click any player node for full dossier
              </p>
            </div>
            <div className="flex bg-surface rounded-xl p-0.5 border border-borderDark text-xs font-mono">
              <button
                onClick={() => setGalaxyAxes("rapm")}
                className={`px-3 py-1.5 rounded-lg font-bold transition ${
                  galaxyAxes === "rapm" ? "bg-accent text-white" : "text-gray-400 hover:text-white"
                }`}
              >
                ORAPM &times; DRAPM Quadrants
              </button>
              <button
                onClick={() => setGalaxyAxes("tsne")}
                className={`px-3 py-1.5 rounded-lg font-bold transition ${
                  galaxyAxes === "tsne" ? "bg-accent text-white" : "text-gray-400 hover:text-white"
                }`}
              >
                t-SNE Manifold Clusters
              </button>
            </div>
          </div>

          <div className="relative w-full h-[500px] bg-surface rounded-2xl border border-borderDark overflow-hidden">
            {galaxyAxes === "rapm" && (
              <>
                <div className="absolute top-3 right-4 text-[10px] font-mono uppercase font-extrabold text-emerald-400 bg-emerald-950/50 px-2.5 py-1 rounded border border-emerald-500/30">
                  🏆 Two-Way Superstars (+ORAPM, +DRAPM)
                </div>
                <div className="absolute top-3 left-4 text-[10px] font-mono uppercase font-bold text-cyan-400 bg-cyan-950/40 px-2.5 py-1 rounded border border-cyan-500/30">
                  🛡️ Defensive Stoppers (-ORAPM, +DRAPM)
                </div>
                <div className="absolute bottom-3 right-4 text-[10px] font-mono uppercase font-bold text-amber-400 bg-amber-950/40 px-2.5 py-1 rounded border border-amber-500/30">
                  🔥 Offensive Specialists (+ORAPM, -DRAPM)
                </div>
                <div className="absolute inset-x-0 top-1/2 border-t border-dashed border-gray-700/60 pointer-events-none" />
                <div className="absolute inset-y-0 left-1/2 border-l border-dashed border-gray-700/60 pointer-events-none" />
              </>
            )}

            <svg viewBox="0 0 800 500" className="w-full h-full select-none">
              {filteredFullPlayers.map((p) => {
                let cx = 400;
                let cy = 250;
                if (galaxyAxes === "rapm") {
                  cx = Math.max(30, Math.min(770, 400 + (p.orapm / 6.0) * 340));
                  cy = Math.max(30, Math.min(470, 250 - (p.drapm / 5.0) * 200));
                } else {
                  const tx = p.tsne_x ?? (p.orapm * 12);
                  const ty = p.tsne_y ?? (p.drapm * 12);
                  cx = Math.max(35, Math.min(765, 400 + (tx / 45.0) * 330));
                  cy = Math.max(35, Math.min(465, 250 - (ty / 45.0) * 200));
                }
                const col = ARCHETYPE_COLORS[p.offensive_archetype || ""] || "#38bdf8";
                const rad = Math.max(4.5, Math.min(11, 4.5 + Math.max(0, p.wins_added || 0) * 0.45));
                const isTopStar = p.rapm >= 3.2 || (p.wins_added || 0) >= 8.5;

                return (
                  <g
                    key={`${p.player_id}-${p.season}`}
                    onClick={() => setSelectedPlayer(p)}
                    onMouseEnter={() => setHoveredDot(p)}
                    onMouseLeave={() => setHoveredDot(null)}
                    className="cursor-pointer group"
                  >
                    <circle
                      cx={cx}
                      cy={cy}
                      r={rad}
                      fill={col}
                      fillOpacity={0.82}
                      stroke="#ffffff"
                      strokeWidth={isTopStar ? "1.4" : "0.5"}
                    />
                    {isTopStar && (
                      <text
                        x={cx}
                        y={cy - rad - 3}
                        textAnchor="middle"
                        fill="#f8fafc"
                        fontSize="9.5"
                        fontWeight="700"
                        className="font-mono pointer-events-none"
                      >
                        {p.full_name.split(" ").pop()}
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>

            {/* Hover Tooltip */}
            {hoveredDot && (
              <div className="absolute bottom-3 left-4 bg-surfaceCard/95 backdrop-blur-md border border-accent/50 rounded-xl px-3.5 py-2 text-xs font-mono text-white shadow-2xl pointer-events-none flex items-center gap-3">
                <span className="px-2 py-0.5 rounded bg-accent/20 text-accent font-bold">
                  {hoveredDot.team_abbreviation}
                </span>
                <span className="font-bold font-sans">{hoveredDot.full_name}</span>
                <span className="text-gray-400">{hoveredDot.offensive_archetype}</span>
                <span className="text-emerald-400 font-bold">
                  RAPM: {hoveredDot.rapm >= 0 ? `+${hoveredDot.rapm}` : hoveredDot.rapm}
                </span>
                <span className="text-amber-300 font-bold">
                  +{hoveredDot.wins_added ?? 0} Wins
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Slide-over Player Dossier & 10-Season Career Modal */}
      {selectedPlayer && (
        <div
          className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto"
          onClick={() => setSelectedPlayer(null)}
        >
          <div
            className="bg-surfaceCard border border-borderDark rounded-2xl max-w-3xl w-full p-6 shadow-2xl relative space-y-5 my-8 max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setSelectedPlayer(null)}
              className="absolute top-4 right-4 w-8 h-8 rounded-full bg-surface hover:bg-surfaceCard border border-borderDark flex items-center justify-center text-gray-400 hover:text-white transition"
            >
              &times;
            </button>

            {/* Header & Biometrics */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-borderDark pb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-accent/15 border border-accent/40 flex items-center justify-center text-2xl">
                  👤
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-xl font-extrabold text-white">{selectedPlayer.full_name}</h3>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-accent/20 text-accent border border-accent/40 font-bold">
                      {selectedPlayer.season || season}
                    </span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-surface border border-borderDark text-gray-300 font-bold">
                      {selectedPlayer.team_abbreviation}
                    </span>
                  </div>
                  <p className="text-xs font-mono text-gray-400 mt-1">
                    {selectedPlayer.position || "G-F"} &middot; {selectedPlayer.height || "6-6"} &middot;{" "}
                    {selectedPlayer.weight ? `${selectedPlayer.weight} lbs` : "215 lbs"} &middot; Age{" "}
                    {selectedPlayer.age || 26} &middot; {selectedPlayer.college || selectedPlayer.country || "NBA"}
                    {selectedPlayer.draft_year && selectedPlayer.draft_year !== "Undrafted"
                      ? ` • Draft: ${selectedPlayer.draft_year} (#${selectedPlayer.draft_number})`
                      : ""}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 font-mono text-xs pr-8">
                <Link
                  href={`/shots?player=${selectedPlayer.player_id}`}
                  className="px-3 py-1.5 rounded-xl bg-surface hover:bg-surfaceCard border border-borderDark text-cyan-300 font-bold transition"
                >
                  🎯 Shot Chart
                </Link>
                <Link
                  href={`/compare?p1=${selectedPlayer.player_id}&s1=${selectedPlayer.season || season}`}
                  className="px-3 py-1.5 rounded-xl bg-accent/20 hover:bg-accent/30 border border-accent/40 text-accent font-bold transition"
                >
                  ⚔️ Compare
                </Link>
              </div>
            </div>

            {/* Archetype & 3D Cluster Badges */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs font-mono">
              <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                <span className="text-[10px] uppercase text-gray-400 block">Offensive Archetype</span>
                <span className="font-bold text-cyan-300">{selectedPlayer.offensive_archetype}</span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                <span className="text-[10px] uppercase text-gray-400 block">Defensive Archetype</span>
                <span className="font-bold text-emerald-300">{selectedPlayer.defensive_archetype}</span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                <span className="text-[10px] uppercase text-gray-400 block">3D t-SNE Cluster</span>
                <span className="font-bold text-purple-300">{selectedPlayer.cluster_name}</span>
              </div>
            </div>

            {/* Per-Game Traditional & Impact Stats */}
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-center font-mono">
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
                <span className="text-base font-bold text-white">
                  {(selectedPlayer.ts_pct * 100).toFixed(1)}%
                </span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                <span className="text-[10px] uppercase text-gray-400 block">USG%</span>
                <span className="text-base font-bold text-cyan-400">
                  {selectedPlayer.usg_pct ?? 20.0}%
                </span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                <span className="text-[10px] uppercase text-gray-400 block">WINS ADDED</span>
                <span className="text-base font-bold text-amber-300">
                  {selectedPlayer.wins_added ?? 0}
                </span>
              </div>
            </div>

            {/* Hustle, Rim Contest & Clutch Tracking Row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center font-mono text-xs">
              <div className="p-2.5 rounded-xl bg-surface/80 border border-borderDark">
                <span className="text-[10px] uppercase text-gray-500 block">Deflections / G</span>
                <span className="font-bold text-cyan-300">
                  {selectedPlayer.deflections_pg !== undefined ? selectedPlayer.deflections_pg.toFixed(1) : "1.4"}
                </span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface/80 border border-borderDark">
                <span className="text-[10px] uppercase text-gray-500 block">Contested Shots / G</span>
                <span className="font-bold text-white">
                  {selectedPlayer.contested_pg !== undefined ? selectedPlayer.contested_pg.toFixed(1) : "5.2"}
                </span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface/80 border border-borderDark">
                <span className="text-[10px] uppercase text-gray-500 block">DFG% Diff (Contest)</span>
                <span
                  className={`font-bold ${
                    (selectedPlayer.dfg_diff ?? 0) <= 0 ? "text-emerald-400" : "text-red-400"
                  }`}
                >
                  {(selectedPlayer.dfg_diff ?? 0) > 0
                    ? `+${(selectedPlayer.dfg_diff ?? 0).toFixed(1)}%`
                    : `${(selectedPlayer.dfg_diff ?? 0).toFixed(1)}%`}
                </span>
              </div>
              <div className="p-2.5 rounded-xl bg-surface/80 border border-borderDark">
                <span className="text-[10px] uppercase text-gray-500 block">Clutch PTS (+/-)</span>
                <span className="font-bold text-amber-300">
                  {selectedPlayer.clutch_pts ?? 0} pts (
                  {(selectedPlayer.clutch_plus_minus ?? 0) >= 0
                    ? `+${selectedPlayer.clutch_plus_minus ?? 0}`
                    : selectedPlayer.clutch_plus_minus ?? 0}
                  )
                </span>
              </div>
            </div>

            {/* Percentile Rank Profile */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-xs font-mono pt-2 border-t border-borderDark">
              <div className="flex items-center justify-between">
                <span className="text-gray-300">
                  Total RAPM ({selectedPlayer.rapm > 0 ? `+${selectedPlayer.rapm}` : selectedPlayer.rapm}):
                </span>
                <PercentileBadge value={selectedPlayer.rapm_percentile} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-300">
                  Offensive RAPM ({selectedPlayer.orapm > 0 ? `+${selectedPlayer.orapm}` : selectedPlayer.orapm}):
                </span>
                <PercentileBadge value={selectedPlayer.orapm_percentile} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-300">
                  Defensive RAPM ({selectedPlayer.drapm > 0 ? `+${selectedPlayer.drapm}` : selectedPlayer.drapm}):
                </span>
                <PercentileBadge value={selectedPlayer.drapm_percentile} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-300">Scoring Volume ({selectedPlayer.pts} PPG):</span>
                <PercentileBadge value={selectedPlayer.pts_percentile} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-300">Playmaking ({selectedPlayer.ast} APG):</span>
                <PercentileBadge value={selectedPlayer.ast_percentile} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-300">
                  True Shooting ({(selectedPlayer.ts_pct * 100).toFixed(1)}%):
                </span>
                <PercentileBadge value={selectedPlayer.ts_percentile} />
              </div>
            </div>

            {/* 10-Season Career Trajectory Table */}
            {careerHistory.length > 1 && (
              <div className="pt-3 border-t border-borderDark space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-gray-300 font-bold">
                    📅 10-Season Career Trajectory ({careerHistory.length} Seasons)
                  </h4>
                  <span className="text-[10px] font-mono text-gray-500">Click any season to switch dossier</span>
                </div>
                <div className="overflow-x-auto max-h-48 overflow-y-auto rounded-xl border border-borderDark">
                  <table className="w-full text-left font-mono text-[11px]">
                    <thead className="bg-surface text-gray-400 uppercase border-b border-borderDark sticky top-0">
                      <tr>
                        <th className="py-1.5 px-2.5">Season</th>
                        <th className="py-1.5 px-2">Tm</th>
                        <th className="py-1.5 px-2 text-right">GP</th>
                        <th className="py-1.5 px-2 text-right">PPG</th>
                        <th className="py-1.5 px-2 text-right">RPG</th>
                        <th className="py-1.5 px-2 text-right">APG</th>
                        <th className="py-1.5 px-2 text-right">TS%</th>
                        <th className="py-1.5 px-2 text-right">RAPM</th>
                        <th className="py-1.5 px-2.5 text-right">Wins</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-borderDark/40">
                      {careerHistory.map((ch) => {
                        const isCur = ch.season === selectedPlayer.season;
                        return (
                          <tr
                            key={`${ch.season}-${ch.team_abbreviation}`}
                            onClick={() => setSelectedPlayer(ch)}
                            className={`cursor-pointer transition ${
                              isCur ? "bg-accent/15 text-white font-bold" : "hover:bg-surface/60 text-gray-300"
                            }`}
                          >
                            <td className="py-1.5 px-2.5 text-accent font-bold">{ch.season}</td>
                            <td className="py-1.5 px-2">{ch.team_abbreviation}</td>
                            <td className="py-1.5 px-2 text-right">{ch.gp}</td>
                            <td className="py-1.5 px-2 text-right">{ch.pts}</td>
                            <td className="py-1.5 px-2 text-right">{ch.reb}</td>
                            <td className="py-1.5 px-2 text-right">{ch.ast}</td>
                            <td className="py-1.5 px-2 text-right">{(ch.ts_pct * 100).toFixed(1)}%</td>
                            <td
                              className={`py-1.5 px-2 text-right font-bold ${
                                ch.rapm >= 0 ? "text-emerald-400" : "text-red-400"
                              }`}
                            >
                              {ch.rapm >= 0 ? `+${ch.rapm.toFixed(2)}` : ch.rapm.toFixed(2)}
                            </td>
                            <td className="py-1.5 px-2.5 text-right text-amber-300 font-bold">
                              {(ch.wins_added ?? 0).toFixed(1)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <button
              onClick={() => setSelectedPlayer(null)}
              className="w-full py-2 bg-surface hover:bg-surfaceCard border border-borderDark rounded-xl text-xs font-bold text-gray-300 hover:text-white transition"
            >
              Close Profile
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
