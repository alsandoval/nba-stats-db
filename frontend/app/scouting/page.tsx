"use client";

import React, { useState, useMemo } from "react";
import { DataService } from "@/lib/data-service";

type MainTab = "clutch" | "hustle" | "defense" | "draft";

export default function ScoutingAndClutchPage() {
  const dataset = useMemo(() => DataService.getScoutingDataset() as any, []);

  const [activeTab, setActiveTab] = useState<MainTab>("clutch");
  const [entityMode, setEntityMode] = useState<"players" | "teams">("players");
  const [draftMode, setDraftMode] = useState<"vope" | "combine">("vope");

  const [search, setSearch] = useState<string>("");
  const [teamFilter, setTeamFilter] = useState<string>("ALL");
  const [draftYearFilter, setDraftYearFilter] = useState<string>("ALL");
  const [minGp, setMinGp] = useState<number>(10);
  const [sortCol, setSortCol] = useState<string>("default");
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  const clutchPlayers: any[] = dataset?.clutch_players || [];
  const clutchTeams: any[] = dataset?.clutch_teams || [];
  const hustlePlayers: any[] = dataset?.hustle_players || [];
  const hustleTeams: any[] = dataset?.hustle_teams || [];
  const defensePlayers: any[] = dataset?.defense_tracking || [];
  const draftPicks: any[] = dataset?.draft_picks || [];
  const combineAthletes: any[] = dataset?.combine_athletes || [];

  const allTeams = useMemo(() => {
    const set = new Set<string>();
    hustlePlayers.forEach((p) => {
      if (p.team_abbreviation) set.add(p.team_abbreviation);
    });
    return Array.from(set).sort();
  }, [hustlePlayers]);

  const draftYears = useMemo(() => {
    const set = new Set<string>();
    draftPicks.forEach((d) => {
      if (d.draft_year) set.add(String(d.draft_year));
    });
    return Array.from(set).sort((a, b) => Number(b) - Number(a));
  }, [draftPicks]);

  const toggleSort = (col: string) => {
    if (sortCol === col) {
      setSortAsc(!sortAsc);
    } else {
      setSortCol(col);
      setSortAsc(col === "pct_plusminus" || col === "d_fg_pct" || col === "overall_pick");
    }
  };

  // Filtered datasets
  const filteredClutchPlayers = useMemo(() => {
    return clutchPlayers
      .filter((p) => p.gp >= Math.min(minGp, 25))
      .filter((p) => (teamFilter === "ALL" ? true : p.team_abbreviation === teamFilter))
      .filter((p) =>
        search
          ? p.player_name.toLowerCase().includes(search.toLowerCase()) ||
            p.team_abbreviation.toLowerCase().includes(search.toLowerCase())
          : true
      )
      .sort((a, b) => {
        const key = sortCol === "default" ? "pts" : sortCol;
        const vA = Number(a[key] ?? 0);
        const vB = Number(b[key] ?? 0);
        return sortAsc ? vA - vB : vB - vA;
      });
  }, [clutchPlayers, minGp, teamFilter, search, sortCol, sortAsc]);

  const filteredHustlePlayers = useMemo(() => {
    return hustlePlayers
      .filter((p) => p.gp >= minGp)
      .filter((p) => (teamFilter === "ALL" ? true : p.team_abbreviation === teamFilter))
      .filter((p) =>
        search
          ? p.player_name.toLowerCase().includes(search.toLowerCase()) ||
            p.team_abbreviation.toLowerCase().includes(search.toLowerCase())
          : true
      )
      .sort((a, b) => {
        const key = sortCol === "default" ? "deflections" : sortCol;
        const vA = Number(a[key] ?? 0);
        const vB = Number(b[key] ?? 0);
        return sortAsc ? vA - vB : vB - vA;
      });
  }, [hustlePlayers, minGp, teamFilter, search, sortCol, sortAsc]);

  const filteredDefensePlayers = useMemo(() => {
    return defensePlayers
      .filter((p) => p.gp >= minGp && p.d_fga >= 120)
      .filter((p) => (teamFilter === "ALL" ? true : p.team_abbreviation === teamFilter))
      .filter((p) =>
        search
          ? p.player_name.toLowerCase().includes(search.toLowerCase()) ||
            p.team_abbreviation.toLowerCase().includes(search.toLowerCase()) ||
            p.position.toLowerCase().includes(search.toLowerCase())
          : true
      )
      .sort((a, b) => {
        const key = sortCol === "default" ? "pct_plusminus" : sortCol;
        const vA = Number(a[key] ?? 0);
        const vB = Number(b[key] ?? 0);
        if (sortCol === "default") return vA - vB; // lower DFG% diff is better
        return sortAsc ? vA - vB : vB - vA;
      });
  }, [defensePlayers, minGp, teamFilter, search, sortCol, sortAsc]);

  const filteredDraftPicks = useMemo(() => {
    return draftPicks
      .filter((d) => (draftYearFilter === "ALL" ? d.gp > 0 : d.draft_year === draftYearFilter))
      .filter((d) => (teamFilter === "ALL" ? true : d.team === teamFilter))
      .filter((d) =>
        search
          ? d.player_name.toLowerCase().includes(search.toLowerCase()) ||
            (d.organization || "").toLowerCase().includes(search.toLowerCase()) ||
            d.team.toLowerCase().includes(search.toLowerCase())
          : true
      )
      .sort((a, b) => {
        const key = sortCol === "default" ? "vope" : sortCol;
        const vA = Number(a[key] ?? 0);
        const vB = Number(b[key] ?? 0);
        return sortAsc ? vA - vB : vB - vA;
      });
  }, [draftPicks, draftYearFilter, teamFilter, search, sortCol, sortAsc]);

  const filteredCombine = useMemo(() => {
    return combineAthletes
      .filter((c) =>
        search
          ? c.player_name.toLowerCase().includes(search.toLowerCase()) ||
            c.position.toLowerCase().includes(search.toLowerCase())
          : true
      )
      .sort((a, b) => {
        const key = sortCol === "default" ? "wingspan_inches" : sortCol;
        const vA = Number(a[key] ?? 0);
        const vB = Number(b[key] ?? 0);
        return sortAsc ? vA - vB : vB - vA;
      });
  }, [combineAthletes, search, sortCol, sortAsc]);

  // Top KPI leaders
  const topClutchScorer = useMemo(
    () => [...clutchPlayers].sort((a, b) => b.pts - a.pts)[0],
    [clutchPlayers]
  );
  const topDeflector = useMemo(
    () => [...hustlePlayers].sort((a, b) => b.deflections - a.deflections)[0],
    [hustlePlayers]
  );
  const topRimDefender = useMemo(
    () =>
      [...defensePlayers]
        .filter((d) => d.d_fga >= 300)
        .sort((a, b) => a.pct_plusminus - b.pct_plusminus)[0],
    [defensePlayers]
  );
  const topDraftSteal = useMemo(
    () => [...draftPicks].sort((a, b) => b.vope - a.vope)[0],
    [draftPicks]
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-extrabold uppercase bg-accent/20 text-accent border border-accent/40">
              Official NBA Tracking &amp; Front-Office Scouting Lab
            </span>
          </div>
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-2">
            <span>🔬</span> Clutch Time, Hustle, Rim Protection &amp; Draft Combine Lab
          </h1>
          <p className="text-xs sm:text-sm text-gray-400 font-mono mt-1">
            469 Clutch Profiles &middot; 567 Hustle Trackers &middot; 569 Closest Defender Rim/Perimeter Contest &middot; 2014–2025 Draft Value &amp; Combine
          </p>
        </div>

        {/* Main 4-Tab Switcher */}
        <div className="flex flex-wrap bg-surfaceCard rounded-xl p-1 border border-borderDark text-xs font-mono gap-1">
          {[
            { id: "clutch", label: "⏱️ Clutch Time (469)", resetSort: "pts" },
            { id: "hustle", label: "🔥 Hustle & Dirty Work (567)", resetSort: "deflections" },
            { id: "defense", label: "🛡️ Defender Contest (569)", resetSort: "pct_plusminus" },
            { id: "draft", label: "🎓 Draft Value & Combine", resetSort: "vope" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => {
                setActiveTab(t.id as MainTab);
                setSortCol("default");
                setSortAsc(false);
              }}
              className={`px-3.5 py-2 rounded-lg transition font-bold ${
                activeTab === t.id
                  ? "bg-accent text-white shadow-sm"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Executive Scouting Spotlight Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          onClick={() => setActiveTab("clutch")}
          className="bg-surfaceCard p-4 rounded-2xl border border-borderDark hover:border-amber-500/50 cursor-pointer transition"
        >
          <span className="text-[10px] font-mono uppercase text-amber-400 font-bold">
            ⏱️ #1 Clutch Scorer (Last 5m ≤5 pts)
          </span>
          <div className="text-lg font-extrabold text-white mt-1">
            {topClutchScorer?.player_name || "Stephen Curry"}
          </div>
          <div className="text-xs font-mono text-gray-400 mt-0.5">
            <strong className="text-amber-300">{topClutchScorer?.pts} Clutch PTS</strong> •{" "}
            {topClutchScorer?.w}-{topClutchScorer?.l} W-L •{" "}
            {((topClutchScorer?.fg_pct || 0) * 100).toFixed(1)}% FG
          </div>
        </div>

        <div
          onClick={() => setActiveTab("hustle")}
          className="bg-surfaceCard p-4 rounded-2xl border border-borderDark hover:border-cyan-500/50 cursor-pointer transition"
        >
          <span className="text-[10px] font-mono uppercase text-cyan-400 font-bold">
            🔥 #1 Deflections &amp; Disruption
          </span>
          <div className="text-lg font-extrabold text-white mt-1">
            {topDeflector?.player_name || "Shai Gilgeous-Alexander"}
          </div>
          <div className="text-xs font-mono text-gray-400 mt-0.5">
            <strong className="text-cyan-300">{topDeflector?.deflections} Deflections</strong> •{" "}
            {topDeflector?.contested_shots} Contested • {topDeflector?.loose_balls} Loose Balls
          </div>
        </div>

        <div
          onClick={() => setActiveTab("defense")}
          className="bg-surfaceCard p-4 rounded-2xl border border-borderDark hover:border-emerald-500/50 cursor-pointer transition"
        >
          <span className="text-[10px] font-mono uppercase text-emerald-400 font-bold">
            🛡️ #1 Shot Contest Lockdown (≥300 DFGA)
          </span>
          <div className="text-lg font-extrabold text-white mt-1">
            {topRimDefender?.player_name || "Rudy Gobert"}
          </div>
          <div className="text-xs font-mono text-gray-400 mt-0.5">
            <strong className="text-emerald-400">
              {((topRimDefender?.pct_plusminus || 0) * 100).toFixed(1)}% DFG% Diff
            </strong>{" "}
            • {topRimDefender?.d_fga} DFGA
          </div>
        </div>

        <div
          onClick={() => setActiveTab("draft")}
          className="bg-surfaceCard p-4 rounded-2xl border border-borderDark hover:border-purple-500/50 cursor-pointer transition"
        >
          <span className="text-[10px] font-mono uppercase text-purple-400 font-bold">
            🎓 #1 Draft Value Over Pick Expectation
          </span>
          <div className="text-lg font-extrabold text-white mt-1">
            {topDraftSteal?.player_name || "Nikola Jokic"}
          </div>
          <div className="text-xs font-mono text-gray-400 mt-0.5">
            Pick #{topDraftSteal?.overall_pick} ({topDraftSteal?.draft_year}) •{" "}
            <strong className="text-purple-300">+{topDraftSteal?.vope} VOPE Wins</strong>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-surfaceCard border border-borderDark rounded-2xl p-4 shadow-lg flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search player, franchise, college, or position..."
            className="bg-surface border border-borderDark rounded-xl px-3.5 py-2 text-xs font-mono text-white placeholder-gray-500 focus:outline-none focus:border-accent w-64"
          />

          <select
            value={teamFilter}
            onChange={(e) => setTeamFilter(e.target.value)}
            className="bg-surface border border-borderDark rounded-xl px-3 py-2 text-xs font-mono text-white"
          >
            <option value="ALL">All 30 Franchises</option>
            {allTeams.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>

          {(activeTab === "clutch" || activeTab === "hustle" || activeTab === "defense") && (
            <div className="flex items-center gap-2 text-xs font-mono bg-surface px-3 py-1.5 rounded-xl border border-borderDark">
              <span className="text-gray-400">Min GP:</span>
              <input
                type="range"
                min="1"
                max="50"
                value={minGp}
                onChange={(e) => setMinGp(Number(e.target.value))}
                className="w-24 accent-accent cursor-pointer"
              />
              <span className="text-accent font-bold w-6">{minGp}</span>
            </div>
          )}

          {activeTab === "draft" && (
            <select
              value={draftYearFilter}
              onChange={(e) => setDraftYearFilter(e.target.value)}
              className="bg-surface border border-accent/50 rounded-xl px-3 py-2 text-xs font-mono font-bold text-white"
            >
              <option value="ALL">All Draft Classes (2014–2025)</option>
              {draftYears.map((yr) => (
                <option key={yr} value={yr}>
                  {yr} NBA Draft Class
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Sub-mode toggles */}
        {(activeTab === "clutch" || activeTab === "hustle") && (
          <div className="flex bg-surface rounded-xl p-0.5 border border-borderDark text-xs font-mono">
            <button
              onClick={() => setEntityMode("players")}
              className={`px-3 py-1.5 rounded-lg transition ${
                entityMode === "players" ? "bg-accent text-white font-bold" : "text-gray-400"
              }`}
            >
              Individual Players
            </button>
            <button
              onClick={() => setEntityMode("teams")}
              className={`px-3 py-1.5 rounded-lg transition ${
                entityMode === "teams" ? "bg-accent text-white font-bold" : "text-gray-400"
              }`}
            >
              All 30 Franchises
            </button>
          </div>
        )}

        {activeTab === "draft" && (
          <div className="flex bg-surface rounded-xl p-0.5 border border-borderDark text-xs font-mono">
            <button
              onClick={() => setDraftMode("vope")}
              className={`px-3 py-1.5 rounded-lg transition ${
                draftMode === "vope" ? "bg-accent text-white font-bold" : "text-gray-400"
              }`}
            >
              Draft Value Over Pick (VOPE)
            </button>
            <button
              onClick={() => setDraftMode("combine")}
              className={`px-3 py-1.5 rounded-lg transition ${
                draftMode === "combine" ? "bg-accent text-white font-bold" : "text-gray-400"
              }`}
            >
              Combine Anthropometrics ({combineAthletes.length})
            </button>
          </div>
        )}
      </div>

      {/* TAB 1: CLUTCH TIME */}
      {activeTab === "clutch" && (
        <div className="bg-surfaceCard border border-borderDark rounded-2xl shadow-xl overflow-hidden">
          <div className="p-4 border-b border-borderDark flex items-center justify-between">
            <div>
              <h2 className="text-base font-extrabold text-white">
                ⏱️ Official NBA Clutch Time Leaderboard (Last 5 Min, Score Margin &le; 5 Pts)
              </h2>
              <p className="text-xs font-mono text-gray-400">
                Click any column header to sort &middot; Showing{" "}
                {entityMode === "players" ? filteredClutchPlayers.length : clutchTeams.length}{" "}
                {entityMode}
              </p>
            </div>
          </div>

          <div className="overflow-x-auto max-h-[580px] overflow-y-auto">
            {entityMode === "players" ? (
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-surface text-gray-400 uppercase border-b border-borderDark sticky top-0 z-10">
                  <tr>
                    <th className="py-3 px-3">#</th>
                    <th className="py-3 px-3">Player</th>
                    <th className="py-3 px-3">Team</th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("gp")}
                    >
                      Clutch GP
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("w_pct")}
                    >
                      Clutch W-L (%)
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("pts")}
                    >
                      Total PTS
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("pts_pg")}
                    >
                      PTS/G
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("fg_pct")}
                    >
                      FG%
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("fg3_pct")}
                    >
                      3P%
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("ft_pct")}
                    >
                      FT%
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("plus_minus")}
                    >
                      Clutch +/-
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-borderDark/40">
                  {filteredClutchPlayers.slice(0, 150).map((p, i) => (
                    <tr key={p.player_id} className="hover:bg-surface/60 transition">
                      <td className="py-2.5 px-3 text-gray-500">{i + 1}</td>
                      <td className="py-2.5 px-3 font-bold text-white font-sans">{p.player_name}</td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded bg-surface border border-borderDark text-accent font-bold">
                          {p.team_abbreviation}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">{p.gp}</td>
                      <td className="py-2.5 px-3 text-right text-gray-200">
                        {p.w}-{p.l} ({(p.w_pct * 100).toFixed(1)}%)
                      </td>
                      <td className="py-2.5 px-3 text-right font-extrabold text-amber-300">
                        {p.pts}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-white">
                        {p.pts_pg.toFixed(1)}
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">
                        {(p.fg_pct * 100).toFixed(1)}% ({p.fgm}/{p.fga})
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">
                        {(p.fg3_pct * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">
                        {(p.ft_pct * 100).toFixed(1)}%
                      </td>
                      <td
                        className={`py-2.5 px-3 text-right font-extrabold ${
                          p.plus_minus >= 0 ? "text-emerald-400" : "text-red-400"
                        }`}
                      >
                        {p.plus_minus >= 0 ? `+${p.plus_minus}` : p.plus_minus}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-surface text-gray-400 uppercase border-b border-borderDark sticky top-0">
                  <tr>
                    <th className="py-3 px-4">#</th>
                    <th className="py-3 px-4">Franchise</th>
                    <th className="py-3 px-3 text-right">Clutch GP</th>
                    <th className="py-3 px-3 text-right">Clutch W-L</th>
                    <th className="py-3 px-3 text-right">Clutch Win%</th>
                    <th className="py-3 px-3 text-right">Clutch PTS</th>
                    <th className="py-3 px-3 text-right">FG%</th>
                    <th className="py-3 px-3 text-right">3P%</th>
                    <th className="py-3 px-3 text-right">FT%</th>
                    <th className="py-3 px-3 text-right">Clutch +/-</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-borderDark/40">
                  {clutchTeams.map((t, i) => (
                    <tr key={t.team_id} className="hover:bg-surface/60 transition">
                      <td className="py-2.5 px-4 text-gray-500">{i + 1}</td>
                      <td className="py-2.5 px-4 font-bold text-white font-sans">
                        <span className="px-2 py-0.5 rounded bg-surface border border-borderDark text-accent font-mono mr-2">
                          {t.team_abbreviation}
                        </span>
                        {t.team_name}
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">{t.gp}</td>
                      <td className="py-2.5 px-3 text-right font-bold text-white">
                        {t.w}-{t.l}
                      </td>
                      <td className="py-2.5 px-3 text-right font-extrabold text-amber-300">
                        {(t.w_pct * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-200">{t.pts}</td>
                      <td className="py-2.5 px-3 text-right text-gray-300">
                        {(t.fg_pct * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">
                        {(t.fg3_pct * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">
                        {(t.ft_pct * 100).toFixed(1)}%
                      </td>
                      <td
                        className={`py-2.5 px-3 text-right font-extrabold ${
                          t.plus_minus >= 0 ? "text-emerald-400" : "text-red-400"
                        }`}
                      >
                        {t.plus_minus >= 0 ? `+${t.plus_minus}` : t.plus_minus}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: HUSTLE STATS */}
      {activeTab === "hustle" && (
        <div className="bg-surfaceCard border border-borderDark rounded-2xl shadow-xl overflow-hidden">
          <div className="p-4 border-b border-borderDark">
            <h2 className="text-base font-extrabold text-white">
              🔥 Official NBA Hustle &amp; Disruption Tracking (Deflections, Contested Shots, Screen Assists, Box Outs)
            </h2>
            <p className="text-xs font-mono text-gray-400">
              Click any column header to sort &middot; Tracking every possession hustle event
            </p>
          </div>

          <div className="overflow-x-auto max-h-[580px] overflow-y-auto">
            {entityMode === "players" ? (
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-surface text-gray-400 uppercase border-b border-borderDark sticky top-0 z-10">
                  <tr>
                    <th className="py-3 px-3">#</th>
                    <th className="py-3 px-3">Player</th>
                    <th className="py-3 px-3">Team</th>
                    <th className="py-3 px-3 text-right">GP</th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("deflections")}
                    >
                      Deflections
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("deflections_pg")}
                    >
                      Defl/G
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("contested_shots")}
                    >
                      Contested Shots
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("contested_3pt")}
                    >
                      3PT Contests
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("screen_assists")}
                    >
                      Screen AST (Pts)
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("charges_drawn")}
                    >
                      Charges
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("loose_balls")}
                    >
                      Loose Balls
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("box_outs")}
                    >
                      Box Outs
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-borderDark/40">
                  {filteredHustlePlayers.slice(0, 150).map((p, i) => (
                    <tr key={p.player_id} className="hover:bg-surface/60 transition">
                      <td className="py-2.5 px-3 text-gray-500">{i + 1}</td>
                      <td className="py-2.5 px-3 font-bold text-white font-sans">{p.player_name}</td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded bg-surface border border-borderDark text-accent font-bold">
                          {p.team_abbreviation}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-400">{p.gp}</td>
                      <td className="py-2.5 px-3 text-right font-extrabold text-cyan-300">
                        {p.deflections}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-white">
                        {p.deflections_pg.toFixed(1)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-emerald-400">
                        {p.contested_shots}
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">{p.contested_3pt}</td>
                      <td className="py-2.5 px-3 text-right text-amber-300">
                        {p.screen_assists} ({p.screen_ast_pts} pts)
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">{p.charges_drawn}</td>
                      <td className="py-2.5 px-3 text-right text-gray-300">{p.loose_balls}</td>
                      <td className="py-2.5 px-3 text-right text-gray-300">{p.box_outs}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-surface text-gray-400 uppercase border-b border-borderDark sticky top-0">
                  <tr>
                    <th className="py-3 px-4">#</th>
                    <th className="py-3 px-4">Franchise</th>
                    <th className="py-3 px-3 text-right">Deflections</th>
                    <th className="py-3 px-3 text-right">Contested Shots</th>
                    <th className="py-3 px-3 text-right">2PT Contests</th>
                    <th className="py-3 px-3 text-right">3PT Contests</th>
                    <th className="py-3 px-3 text-right">Screen Assists (Pts)</th>
                    <th className="py-3 px-3 text-right">Charges Drawn</th>
                    <th className="py-3 px-3 text-right">Loose Balls</th>
                    <th className="py-3 px-3 text-right">Box Outs</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-borderDark/40">
                  {hustleTeams.map((t, i) => (
                    <tr key={t.team_id} className="hover:bg-surface/60 transition">
                      <td className="py-2.5 px-4 text-gray-500">{i + 1}</td>
                      <td className="py-2.5 px-4 font-bold text-white font-sans">
                        <span className="px-2 py-0.5 rounded bg-surface border border-borderDark text-accent font-mono mr-2">
                          {t.team_abbreviation}
                        </span>
                        {t.team_name}
                      </td>
                      <td className="py-2.5 px-3 text-right font-extrabold text-cyan-300">
                        {t.deflections}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-emerald-400">
                        {t.contested_shots}
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">{t.contested_2pt}</td>
                      <td className="py-2.5 px-3 text-right text-gray-300">{t.contested_3pt}</td>
                      <td className="py-2.5 px-3 text-right text-amber-300">
                        {t.screen_assists} ({t.screen_ast_pts} pts)
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">{t.charges_drawn}</td>
                      <td className="py-2.5 px-3 text-right text-gray-300">{t.loose_balls}</td>
                      <td className="py-2.5 px-3 text-right text-gray-300">{t.box_outs}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: CLOSEST DEFENDER & RIM/PERIMETER TRACKING */}
      {activeTab === "defense" && (
        <div className="bg-surfaceCard border border-borderDark rounded-2xl shadow-xl overflow-hidden">
          <div className="p-4 border-b border-borderDark">
            <h2 className="text-base font-extrabold text-white">
              🛡️ Closest Defender Tracking: Opponent FG% vs Expected Normal FG% (DFG% Differential)
            </h2>
            <p className="text-xs font-mono text-gray-400">
              Negative DFG% Diff (Green) indicates the defender forces opponents to shoot worse than their normal expected FG%.
            </p>
          </div>

          <div className="overflow-x-auto max-h-[580px] overflow-y-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-surface text-gray-400 uppercase border-b border-borderDark sticky top-0 z-10">
                <tr>
                  <th className="py-3 px-3">#</th>
                  <th className="py-3 px-3">Defender</th>
                  <th className="py-3 px-3">Team / Pos</th>
                  <th
                    className="py-3 px-3 text-right cursor-pointer hover:text-white"
                    onClick={() => toggleSort("gp")}
                  >
                    GP
                  </th>
                  <th
                    className="py-3 px-3 text-right cursor-pointer hover:text-white"
                    onClick={() => toggleSort("d_fga")}
                  >
                    Defended FGA
                  </th>
                  <th
                    className="py-3 px-3 text-right cursor-pointer hover:text-white"
                    onClick={() => toggleSort("d_fga_pg")}
                  >
                    DFGA / G
                  </th>
                  <th
                    className="py-3 px-3 text-right cursor-pointer hover:text-white"
                    onClick={() => toggleSort("d_fg_pct")}
                  >
                    Opponent FG%
                  </th>
                  <th
                    className="py-3 px-3 text-right cursor-pointer hover:text-white"
                    onClick={() => toggleSort("normal_fg_pct")}
                  >
                    Expected FG%
                  </th>
                  <th
                    className="py-3 px-3 text-right cursor-pointer hover:text-white"
                    onClick={() => toggleSort("pct_plusminus")}
                  >
                    DFG% Differential
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borderDark/40">
                {filteredDefensePlayers.slice(0, 150).map((d, i) => {
                  const diffPct = d.pct_plusminus * 100;
                  return (
                    <tr key={d.player_id} className="hover:bg-surface/60 transition">
                      <td className="py-2.5 px-3 text-gray-500">{i + 1}</td>
                      <td className="py-2.5 px-3 font-bold text-white font-sans">{d.player_name}</td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded bg-surface border border-borderDark text-accent font-bold mr-1.5">
                          {d.team_abbreviation}
                        </span>
                        <span className="text-gray-400">{d.position}</span>
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-400">{d.gp}</td>
                      <td className="py-2.5 px-3 text-right text-gray-200">
                        {d.d_fgm} / {d.d_fga}
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">{d.d_fga_pg}</td>
                      <td className="py-2.5 px-3 text-right font-bold text-white">
                        {(d.d_fg_pct * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-400">
                        {(d.normal_fg_pct * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <span
                          className={`px-2 py-0.5 rounded font-extrabold ${
                            diffPct <= -2.0
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                              : diffPct < 0
                              ? "text-emerald-400"
                              : "text-red-400"
                          }`}
                        >
                          {diffPct > 0 ? `+${diffPct.toFixed(1)}%` : `${diffPct.toFixed(1)}%`}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: NBA DRAFT VALUE OVER EXPECTATION & COMBINE */}
      {activeTab === "draft" && (
        <div className="bg-surfaceCard border border-borderDark rounded-2xl shadow-xl overflow-hidden">
          <div className="p-4 border-b border-borderDark">
            <h2 className="text-base font-extrabold text-white">
              {draftMode === "vope"
                ? "🎓 NBA Draft Value Over Pick Expectation (VOPE: Actual Career Wins Added vs Pick Slot Curve)"
                : "📏 Official NBA Draft Combine Anthropometrics & Athletic Testing"}
            </h2>
            <p className="text-xs font-mono text-gray-400">
              {draftMode === "vope"
                ? "Evaluates every draft pick (2014–2025) against the expected Wins Added decay curve E[WA] = 26 * exp(-0.052 * (pick - 1))"
                : "Official barefoot height, wingspan, wingspan differential, standing reach, vertical leap, and lane agility."}
            </p>
          </div>

          <div className="overflow-x-auto max-h-[580px] overflow-y-auto">
            {draftMode === "vope" ? (
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-surface text-gray-400 uppercase border-b border-borderDark sticky top-0 z-10">
                  <tr>
                    <th className="py-3 px-3">#</th>
                    <th
                      className="py-3 px-3 cursor-pointer hover:text-white"
                      onClick={() => toggleSort("overall_pick")}
                    >
                      Draft / Pick
                    </th>
                    <th className="py-3 px-3">Player</th>
                    <th className="py-3 px-3">Draft Team / College</th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("gp")}
                    >
                      NBA GP
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("peak_ppg")}
                    >
                      Peak PPG
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("peak_rapm")}
                    >
                      Peak RAPM
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("wins_added")}
                    >
                      Actual Wins Added
                    </th>
                    <th className="py-3 px-3 text-right">Pick Exp Wins</th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("vope")}
                    >
                      VOPE (Steal / Bust)
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-borderDark/40">
                  {filteredDraftPicks.slice(0, 150).map((d, i) => (
                    <tr key={`${d.draft_year}-${d.overall_pick}-${d.player_id}`} className="hover:bg-surface/60 transition">
                      <td className="py-2.5 px-3 text-gray-500">{i + 1}</td>
                      <td className="py-2.5 px-3">
                        <span className="font-bold text-white">{d.draft_year}</span>{" "}
                        <span className="text-accent font-extrabold">#{d.overall_pick}</span>
                      </td>
                      <td className="py-2.5 px-3 font-bold text-white font-sans">{d.player_name}</td>
                      <td className="py-2.5 px-3 text-gray-300">
                        <span className="px-1.5 py-0.5 rounded bg-surface border border-borderDark text-accent font-bold mr-1.5">
                          {d.team}
                        </span>
                        <span className="text-gray-400 text-[11px]">{d.organization}</span>
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">{d.gp}</td>
                      <td className="py-2.5 px-3 text-right text-white font-bold">{d.peak_ppg}</td>
                      <td
                        className={`py-2.5 px-3 text-right font-bold ${
                          d.peak_rapm >= 0 ? "text-emerald-400" : "text-gray-400"
                        }`}
                      >
                        {d.peak_rapm > 0 ? `+${d.peak_rapm}` : d.peak_rapm}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-amber-300">
                        {d.wins_added.toFixed(1)}
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-400">
                        {d.expected_wins_added.toFixed(1)}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <span
                          className={`px-2 py-0.5 rounded font-extrabold ${
                            d.vope >= 15
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                              : d.vope >= 0
                              ? "text-emerald-400"
                              : "text-red-400"
                          }`}
                        >
                          {d.vope > 0 ? `+${d.vope.toFixed(1)}` : d.vope.toFixed(1)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-surface text-gray-400 uppercase border-b border-borderDark sticky top-0 z-10">
                  <tr>
                    <th className="py-3 px-3">#</th>
                    <th className="py-3 px-3">Prospect</th>
                    <th className="py-3 px-3">Pos</th>
                    <th className="py-3 px-3 text-right">Height (Barefoot)</th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("wingspan_inches")}
                    >
                      Wingspan
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("wingspan_diff")}
                    >
                      Wingspan +Diff
                    </th>
                    <th className="py-3 px-3 text-right">Standing Reach</th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("max_vertical")}
                    >
                      Max Vert
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("lane_agility")}
                    >
                      Lane Agility
                    </th>
                    <th
                      className="py-3 px-3 text-right cursor-pointer hover:text-white"
                      onClick={() => toggleSort("sprint_3q")}
                    >
                      3/4 Sprint
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-borderDark/40">
                  {filteredCombine.map((c, i) => (
                    <tr key={`${c.player_id}-${i}`} className="hover:bg-surface/60 transition">
                      <td className="py-2.5 px-3 text-gray-500">{i + 1}</td>
                      <td className="py-2.5 px-3 font-bold text-white font-sans">{c.player_name}</td>
                      <td className="py-2.5 px-3 text-accent font-bold">{c.position}</td>
                      <td className="py-2.5 px-3 text-right text-gray-200">{c.height_ft_in || "-"}</td>
                      <td className="py-2.5 px-3 text-right font-extrabold text-cyan-300">
                        {c.wingspan_ft_in || "-"}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-emerald-400">
                        {c.wingspan_diff > 0 ? `+${c.wingspan_diff}"` : `${c.wingspan_diff}"`}
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">
                        {c.standing_reach || "-"}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-amber-300">
                        {c.max_vertical > 0 ? `${c.max_vertical}"` : "-"}
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">
                        {c.lane_agility > 0 ? `${c.lane_agility}s` : "-"}
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-300">
                        {c.sprint_3q > 0 ? `${c.sprint_3q}s` : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
