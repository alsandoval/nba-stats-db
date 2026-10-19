"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import {
  DataService,
  Team,
  Player,
  NBANewsItem,
  SEASONS_10YR,
  DEFAULT_SEASON,
  APP_RELEASE_VERSION,
  APP_BUILD_TIMESTAMP,
} from "@/lib/data-service";
import { getTeamPalette } from "@/components/differential-candlestick-chart";

export default function OverviewPage() {
  const [season, setSeason] = useState<string>(DEFAULT_SEASON);
  const [teams, setTeams] = useState<Team[]>([]);
  const [players, setPlayers] = useState<Player[]>([]);
  const [news, setNews] = useState<NBANewsItem[]>([]);
  const [newsFilter, setNewsFilter] = useState<"ALL" | "ESPN" | "X / Twitter" | "Front-Office">("ALL");
  const [newsLoading, setNewsLoading] = useState<boolean>(true);
  const [conference, setConference] = useState<"ALL" | "Eastern" | "Western">("ALL");
  const [sortField, setSortField] = useState<keyof Team>("win_pct");
  const [sortAsc, setSortAsc] = useState<boolean>(false);
  const [search, setSearch] = useState<string>("");
  const [standingsView, setStandingsView] = useState<"TABLE" | "QUADRANT">("TABLE");
  const [selectedFranchise, setSelectedFranchise] = useState<Team | null>(null);

  useEffect(() => {
    DataService.getTeams(season).then(setTeams);
    DataService.getPlayers(season).then(setPlayers);
  }, [season]);

  const loadLiveNews = () => {
    setNewsLoading(true);
    DataService.getLiveNBANews()
      .then((items) => setNews(items))
      .finally(() => setNewsLoading(false));
  };

  useEffect(() => {
    loadLiveNews();
  }, []);

  const filteredNews = useMemo(() => {
    if (newsFilter === "ALL") return news.slice(0, 8);
    if (newsFilter === "ESPN") return news.filter((n) => n.source === "ESPN").slice(0, 8);
    if (newsFilter === "X / Twitter") return news.filter((n) => n.source === "X / Twitter").slice(0, 8);
    return news.filter((n) => n.source === "Front-Office Wire" || n.category === "Insider" || n.category === "Analytics").slice(0, 8);
  }, [news, newsFilter]);

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

  const formatRelativeTime = (iso: string) => {
    try {
      const diffMs = Date.now() - new Date(iso).getTime();
      const mins = Math.max(1, Math.floor(diffMs / 60000));
      if (mins < 60) return `${mins}m ago`;
      const hrs = Math.floor(mins / 60);
      if (hrs < 24) return `${hrs}h ago`;
      const days = Math.floor(hrs / 24);
      return `${days}d ago`;
    } catch {
      return "Live";
    }
  };

  return (
    <div className="space-y-14 pb-8">
      {/* =====================================================================
          HERO SECTION
      ===================================================================== */}
      <section className="relative rounded-3xl border border-borderDark bg-gradient-to-br from-[#0F172A] via-surfaceCard to-[#111827] p-7 md:p-10 shadow-2xl overflow-hidden">
        {/* Ambient Decorative Glows */}
        <div className="pointer-events-none absolute -top-24 -left-24 w-96 h-96 rounded-full bg-accent/15 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-24 -right-24 w-96 h-96 rounded-full bg-red-500/10 blur-3xl" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-8">
          <div className="max-w-3xl space-y-4">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-extrabold uppercase tracking-wider bg-red-500/15 text-red-400 border border-red-500/30">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                LIVE NBA INTELLIGENCE PLATFORM
              </span>
              <span className="px-3 py-1 rounded-full text-[11px] font-mono font-bold bg-accent/15 text-accent border border-accent/30">
                Release {APP_RELEASE_VERSION} • {DEFAULT_SEASON} Active
              </span>
              <span className="text-xs font-mono text-gray-400 hidden sm:inline">
                Press <kbd className="px-1.5 py-0.5 rounded bg-surface border border-borderDark text-white">⌘K</kbd> for Instant Search
              </span>
            </div>

            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-white leading-[1.12]">
              NBA Front-Office Analytics,{" "}
              <span className="bg-gradient-to-r from-blue-400 via-cyan-300 to-emerald-400 bg-clip-text text-transparent">
                Live Win-Prob Candlesticks
              </span>{" "}
              &amp; Insider Wire.
            </h1>

            <p className="text-sm sm:text-base text-gray-300 leading-relaxed max-w-2xl">
              Explore 10 complete NBA seasons (2015-16 through 2024-25) across all 30 modern franchises. Track live ESPN &amp; X/Twitter breaking news, minute-by-minute team-colored Win Probability OHLC candlesticks, Ridge RAPM player impact, and 2024 CBA Second-Apron capology.
            </p>

            {/* Primary CTAs */}
            <div className="pt-2 flex flex-wrap items-center gap-3">
              <Link
                href="/live"
                className="px-5 py-3 rounded-xl bg-red-600 hover:bg-red-500 text-white font-extrabold text-sm shadow-lg shadow-red-600/25 transition flex items-center gap-2"
              >
                <span>🔴 Launch Live Game Companion</span>
                <span>&rarr;</span>
              </Link>
              <Link
                href="/rapm"
                className="px-5 py-3 rounded-xl bg-accent hover:bg-accentHover text-white font-extrabold text-sm shadow-lg shadow-accent/20 transition flex items-center gap-2"
              >
                <span>⚡ 5,393-Player RAPM Leaderboard</span>
              </Link>
              <Link
                href="/predictions"
                className="px-4 py-3 rounded-xl bg-surface hover:bg-surface/80 border border-borderDark hover:border-gray-600 text-gray-200 font-bold text-sm transition"
              >
                🎯 12,729-Game Matchup Predictor
              </Link>
            </div>
          </div>

          {/* Right Panel: Global Season Switcher + Key Platform Telemetry */}
          <div className="lg:w-80 shrink-0 bg-surface/90 border border-borderDark rounded-2xl p-5 space-y-4 shadow-xl backdrop-blur-md">
            <div>
              <label className="block text-[10px] font-mono uppercase tracking-wider text-gray-400 font-bold mb-1.5">
                Active Telemetry Season (Default: {DEFAULT_SEASON})
              </label>
              <select
                value={season}
                onChange={(e) => setSeason(e.target.value)}
                className="w-full bg-surfaceCard border border-accent/50 rounded-xl px-3.5 py-2.5 text-sm font-mono font-extrabold text-white focus:outline-none focus:border-accent shadow-sm"
              >
                {SEASONS_10YR.map((s) => (
                  <option key={s} value={s}>
                    {s} NBA Season {s === DEFAULT_SEASON ? "(Latest)" : ""}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2.5 pt-1">
              <div className="p-3 rounded-xl bg-surfaceCard border border-borderDark">
                <div className="text-[10px] font-mono uppercase text-gray-400">Archive Games</div>
                <div className="text-lg font-black text-white font-mono mt-0.5">12,729</div>
                <div className="text-[10px] text-emerald-400 font-mono">10 Seasons</div>
              </div>
              <div className="p-3 rounded-xl bg-surfaceCard border border-borderDark">
                <div className="text-[10px] font-mono uppercase text-gray-400">Player-Seasons</div>
                <div className="text-lg font-black text-white font-mono mt-0.5">5,393</div>
                <div className="text-[10px] text-cyan-400 font-mono">Ridge RAPM</div>
              </div>
              <div className="p-3 rounded-xl bg-surfaceCard border border-borderDark">
                <div className="text-[10px] font-mono uppercase text-gray-400">5-Man Lineups</div>
                <div className="text-lg font-black text-white font-mono mt-0.5">1,141</div>
                <div className="text-[10px] text-amber-400 font-mono">WOWY Subsets</div>
              </div>
              <div className="p-3 rounded-xl bg-surfaceCard border border-borderDark">
                <div className="text-[10px] font-mono uppercase text-gray-400">CBA Contracts</div>
                <div className="text-lg font-black text-white font-mono mt-0.5">450</div>
                <div className="text-[10px] text-purple-400 font-mono">30 Franchises</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================================
          SECTION 01 // LIVE NBA NEWS, ESPN & X/TWITTER INSIDER WIRE
      ===================================================================== */}
      <section className="space-y-5 pt-4 border-t border-borderDark/70">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-extrabold uppercase tracking-widest bg-red-500/15 text-red-400 border border-red-500/30">
                SECTION 01 // LIVE WIRE
              </span>
              <span className="text-xs font-mono text-gray-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Real-Time Feed • ESPN API + X/Twitter NBA Insiders
              </span>
            </div>
            <h2 className="text-2xl font-extrabold text-white">
              Latest NBA News, X / Twitter Pulse &amp; Front-Office Wire
            </h2>
          </div>

          {/* Source Filter Tabs */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex bg-surfaceCard rounded-xl p-1 border border-borderDark text-xs font-mono">
              {(["ALL", "ESPN", "X / Twitter", "Front-Office"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setNewsFilter(tab)}
                  className={`px-3 py-1.5 rounded-lg transition ${
                    newsFilter === tab
                      ? "bg-accent text-white font-bold shadow-sm"
                      : "text-gray-400 hover:text-white"
                  }`}
                >
                  {tab === "ALL" ? "All Wire" : tab}
                </button>
              ))}
            </div>
            <button
              onClick={loadLiveNews}
              className="px-3 py-2 rounded-xl bg-surfaceCard hover:bg-surface border border-borderDark text-xs font-mono text-gray-300 hover:text-white transition"
              title="Refresh Live NBA News Feed"
            >
              ↻ Refresh
            </button>
          </div>
        </div>

        {/* News Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {newsLoading && news.length === 0 ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="bg-surfaceCard border border-borderDark rounded-2xl p-5 h-52 animate-pulse flex flex-col justify-between"
              >
                <div className="h-4 w-24 bg-surface rounded" />
                <div className="space-y-2">
                  <div className="h-4 w-full bg-surface rounded" />
                  <div className="h-4 w-4/5 bg-surface rounded" />
                </div>
                <div className="h-3 w-20 bg-surface rounded" />
              </div>
            ))
          ) : (
            filteredNews.map((item) => {
              const isESPN = item.source === "ESPN";
              const isTwitter = item.source === "X / Twitter";
              return (
                <a
                  key={item.id}
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-surfaceCard border border-borderDark hover:border-accent/60 rounded-2xl p-5 flex flex-col justify-between gap-3 transition group shadow-lg hover:shadow-xl"
                >
                  <div className="space-y-2.5">
                    {/* Source & Timestamp Header */}
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-extrabold uppercase tracking-wider border ${
                          isESPN
                            ? "bg-red-500/15 text-red-400 border-red-500/30"
                            : isTwitter
                            ? "bg-sky-500/15 text-sky-300 border-sky-500/30"
                            : "bg-purple-500/15 text-purple-300 border-purple-500/30"
                        }`}
                      >
                        {isTwitter ? "𝕏 / TWITTER" : item.source}
                      </span>
                      <span className="text-[11px] font-mono text-gray-400">
                        {formatRelativeTime(item.publishedAt)}
                      </span>
                    </div>

                    {/* Author / Handle if present */}
                    {(item.author || item.handle) && (
                      <div className="flex items-center gap-1.5 text-xs">
                        <span className="font-bold text-gray-200">{item.author}</span>
                        {item.handle && (
                          <span className="font-mono text-[11px] text-sky-400">{item.handle}</span>
                        )}
                      </div>
                    )}

                    {/* Headline */}
                    <h3 className="text-sm font-bold text-white group-hover:text-accent transition line-clamp-3 leading-snug">
                      {item.headline}
                    </h3>

                    {/* Summary */}
                    <p className="text-xs text-gray-400 line-clamp-3 leading-relaxed">
                      {item.summary}
                    </p>
                  </div>

                  {/* Footer Tags & Link Indicator */}
                  <div className="pt-3 border-t border-borderDark/60 flex items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-1">
                      <span className="text-[10px] font-mono text-gray-400 bg-surface px-2 py-0.5 rounded border border-borderDark">
                        {item.category}
                      </span>
                      {item.teamAbbr && (
                        <span
                          className="text-[10px] font-mono font-bold text-white px-1.5 py-0.5 rounded"
                          style={{ backgroundColor: getTeamPalette(item.teamAbbr).primary }}
                        >
                          {item.teamAbbr}
                        </span>
                      )}
                    </div>
                    <span className="text-xs font-mono text-accent group-hover:translate-x-0.5 transition">
                      Read &nearr;
                    </span>
                  </div>
                </a>
              );
            })
          )}
        </div>
      </section>

      {/* =====================================================================
          SECTION 02 // SEASON STATISTICAL LEADERS & MVP TRACKER
      ===================================================================== */}
      {seasonLeaders && (
        <section className="space-y-5 pt-6 border-t border-borderDark/70">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-extrabold uppercase tracking-widest bg-accent/15 text-accent border border-accent/30">
                  SECTION 02 // {season} SEASON LEADERS
                </span>
              </div>
              <h2 className="text-2xl font-extrabold text-white">
                {season} Individual Statistical &amp; Impact Leaders
              </h2>
            </div>
            <Link
              href="/rapm"
              className="text-xs font-mono font-bold text-accent hover:underline"
            >
              View Full 5,393-Player Leaderboard &rarr;
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Link
              href={`/rapm?player=${seasonLeaders.byPts?.player_id}`}
              className="bg-surfaceCard border border-borderDark hover:border-accent/50 rounded-2xl p-5 flex items-center justify-between transition group shadow-lg"
            >
              <div>
                <span className="text-[10px] font-mono uppercase text-gray-400 block">
                  {season} Scoring Leader
                </span>
                <span className="text-lg font-extrabold text-white group-hover:text-accent transition mt-0.5 block">
                  {seasonLeaders.byPts?.full_name}
                </span>
                <span className="text-xs font-mono text-gray-400 block mt-0.5">
                  {seasonLeaders.byPts?.team_abbreviation} • {seasonLeaders.byPts?.gp} GP
                </span>
              </div>
              <div className="text-right font-mono">
                <span className="text-3xl font-black text-accent">{seasonLeaders.byPts?.pts}</span>
                <span className="text-[10px] text-gray-400 block">PPG</span>
              </div>
            </Link>

            <Link
              href={`/rapm?player=${seasonLeaders.byReb?.player_id}`}
              className="bg-surfaceCard border border-borderDark hover:border-cyan-500/50 rounded-2xl p-5 flex items-center justify-between transition group shadow-lg"
            >
              <div>
                <span className="text-[10px] font-mono uppercase text-gray-400 block">
                  {season} Rebounding Leader
                </span>
                <span className="text-lg font-extrabold text-white group-hover:text-cyan-400 transition mt-0.5 block">
                  {seasonLeaders.byReb?.full_name}
                </span>
                <span className="text-xs font-mono text-gray-400 block mt-0.5">
                  {seasonLeaders.byReb?.team_abbreviation} • {seasonLeaders.byReb?.gp} GP
                </span>
              </div>
              <div className="text-right font-mono">
                <span className="text-3xl font-black text-cyan-400">{seasonLeaders.byReb?.reb}</span>
                <span className="text-[10px] text-gray-400 block">RPG</span>
              </div>
            </Link>

            <Link
              href={`/rapm?player=${seasonLeaders.byAst?.player_id}`}
              className="bg-surfaceCard border border-borderDark hover:border-emerald-500/50 rounded-2xl p-5 flex items-center justify-between transition group shadow-lg"
            >
              <div>
                <span className="text-[10px] font-mono uppercase text-gray-400 block">
                  {season} Assists Leader
                </span>
                <span className="text-lg font-extrabold text-white group-hover:text-emerald-400 transition mt-0.5 block">
                  {seasonLeaders.byAst?.full_name}
                </span>
                <span className="text-xs font-mono text-gray-400 block mt-0.5">
                  {seasonLeaders.byAst?.team_abbreviation} • {seasonLeaders.byAst?.gp} GP
                </span>
              </div>
              <div className="text-right font-mono">
                <span className="text-3xl font-black text-emerald-400">{seasonLeaders.byAst?.ast}</span>
                <span className="text-[10px] text-gray-400 block">APG</span>
              </div>
            </Link>

            <Link
              href={`/rapm?player=${seasonLeaders.byRapm?.player_id}`}
              className="bg-surfaceCard border border-borderDark hover:border-purple-500/50 rounded-2xl p-5 flex items-center justify-between transition group shadow-lg"
            >
              <div>
                <span className="text-[10px] font-mono uppercase text-gray-400 block">
                  {season} #1 Ridge RAPM
                </span>
                <span className="text-lg font-extrabold text-white group-hover:text-purple-400 transition mt-0.5 block">
                  {seasonLeaders.byRapm?.full_name}
                </span>
                <span className="text-xs font-mono text-gray-400 block mt-0.5">
                  {seasonLeaders.byRapm?.team_abbreviation} • {seasonLeaders.byRapm?.offensive_archetype}
                </span>
              </div>
              <div className="text-right font-mono">
                <span className="text-3xl font-black text-purple-400">
                  +{seasonLeaders.byRapm?.rapm.toFixed(2)}
                </span>
                <span className="text-[10px] text-gray-400 block">RAPM</span>
              </div>
            </Link>
          </div>
        </section>
      )}

      {/* =====================================================================
          SECTION 03 // 30-FRANCHISE STANDINGS & EFFICIENCY LANDSCAPE
      ===================================================================== */}
      <section className="space-y-5 pt-6 border-t border-borderDark/70">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-extrabold uppercase tracking-widest bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                SECTION 03 // 30-FRANCHISE TELEMETRY
              </span>
              <span className="text-xs font-mono text-gray-400">
                Click any franchise to inspect 10-Year War Room
              </span>
            </div>
            <h2 className="text-2xl font-extrabold text-white">
              {season} NBA Standings &amp; 4-Quadrant Efficiency Matrix
            </h2>
          </div>

          {/* Controls Bar */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* View Mode Toggle (Table vs Quadrant Map) */}
            <div className="flex bg-surfaceCard rounded-xl p-1 border border-borderDark text-xs font-mono">
              <button
                onClick={() => setStandingsView("TABLE")}
                className={`px-3 py-1.5 rounded-lg transition ${
                  standingsView === "TABLE"
                    ? "bg-accent text-white font-bold"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                📋 Standings Table
              </button>
              <button
                onClick={() => setStandingsView("QUADRANT")}
                className={`px-3 py-1.5 rounded-lg transition ${
                  standingsView === "QUADRANT"
                    ? "bg-accent text-white font-bold"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                🧭 4-Quadrant Map
              </button>
            </div>

            {/* Search */}
            <input
              type="text"
              placeholder="Filter franchise..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-surfaceCard border border-borderDark rounded-xl px-3 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-accent w-40"
            />

            {/* Conference Selector */}
            <div className="flex bg-surfaceCard rounded-xl p-1 border border-borderDark text-xs font-mono">
              {(["ALL", "Eastern", "Western"] as const).map((conf) => (
                <button
                  key={conf}
                  onClick={() => setConference(conf)}
                  className={`px-3 py-1.5 rounded-lg transition ${
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
              className="px-3 py-2 rounded-xl bg-surfaceCard hover:bg-accent/20 border border-borderDark hover:border-accent/50 text-xs font-mono text-gray-300 hover:text-white transition"
            >
              ⬇ CSV
            </button>
          </div>
        </div>

        {/* Conditional View: 4-Quadrant Efficiency Map */}
        {standingsView === "QUADRANT" && (
          <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <p className="text-xs font-mono text-gray-400">
                X-Axis: Offensive Rating (Higher Right &rarr;) &middot; Y-Axis: Defensive Rating (Better Defense Top &uarr;) &middot; Click any team node for 10-Yr War Room
              </p>
              <span className="text-xs font-mono text-gray-400">
                League Averages: ORtg {avgOffRtgNum.toFixed(1)} • Pace {avgPaceNum.toFixed(1)} • TS% {avgTs}%
              </span>
            </div>

            <div className="relative w-full h-[380px] bg-surface rounded-2xl border border-borderDark overflow-hidden p-4">
              <div className="absolute top-3 right-4 text-[10px] font-mono uppercase font-extrabold text-emerald-400/80 bg-emerald-950/40 px-2.5 py-1 rounded border border-emerald-500/30">
                🏆 Elite Contenders (+ORtg, +DRtg)
              </div>
              <div className="absolute top-3 left-4 text-[10px] font-mono uppercase font-bold text-cyan-400/80 bg-cyan-950/30 px-2.5 py-1 rounded border border-cyan-500/20">
                🛡️ Defensive Grinders (-ORtg, +DRtg)
              </div>
              <div className="absolute bottom-3 right-4 text-[10px] font-mono uppercase font-bold text-amber-400/80 bg-amber-950/30 px-2.5 py-1 rounded border border-amber-500/20">
                🔥 Glass Cannons (+ORtg, -DRtg)
              </div>
              <div className="absolute bottom-3 left-4 text-[10px] font-mono uppercase font-bold text-red-400/80 bg-red-950/30 px-2.5 py-1 rounded border border-red-500/20">
                📉 Lottery / Rebuild (-ORtg, -DRtg)
              </div>

              <div className="absolute inset-x-0 top-1/2 border-t border-dashed border-gray-600/60 pointer-events-none" />
              <div className="absolute inset-y-0 left-1/2 border-l border-dashed border-gray-600/60 pointer-events-none" />

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
        )}

        {/* Standings Table */}
        <div className="bg-surfaceCard rounded-2xl border border-borderDark shadow-xl overflow-hidden">
          <div className="px-5 py-3 bg-surface/60 border-b border-borderDark flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-gray-400">
            <span>
              Showing {filteredTeams.length} of 30 Modern NBA Franchises ({season})
            </span>
            <span>
              League Averages: Pace {avgPaceNum.toFixed(1)} &middot; ORtg {avgOffRtgNum.toFixed(1)} &middot; TS% {avgTs}%
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface text-gray-400 text-xs uppercase font-mono border-b border-borderDark">
                <tr>
                  <th className="py-3.5 px-4">#</th>
                  <th
                    className="py-3.5 px-4 cursor-pointer hover:text-white"
                    onClick={() => handleSort("full_name")}
                  >
                    Franchise {sortField === "full_name" && (sortAsc ? "▲" : "▼")}
                  </th>
                  <th
                    className="py-3.5 px-3 text-right cursor-pointer hover:text-white"
                    onClick={() => handleSort("wins")}
                  >
                    W-L {sortField === "wins" && (sortAsc ? "▲" : "▼")}
                  </th>
                  <th
                    className="py-3.5 px-3 text-right cursor-pointer hover:text-white"
                    onClick={() => handleSort("win_pct")}
                  >
                    Win% {sortField === "win_pct" && (sortAsc ? "▲" : "▼")}
                  </th>
                  <th className="py-3.5 px-3 text-center hidden md:table-cell">Home</th>
                  <th className="py-3.5 px-3 text-center hidden md:table-cell">Road</th>
                  <th className="py-3.5 px-3 text-center hidden lg:table-cell">L10</th>
                  <th
                    className="py-3.5 px-3 text-right cursor-pointer hover:text-white"
                    onClick={() => handleSort("off_rating")}
                  >
                    ORtg {sortField === "off_rating" && (sortAsc ? "▲" : "▼")}
                  </th>
                  <th
                    className="py-3.5 px-3 text-right cursor-pointer hover:text-white"
                    onClick={() => handleSort("def_rating")}
                  >
                    DRtg {sortField === "def_rating" && (sortAsc ? "▲" : "▼")}
                  </th>
                  <th
                    className="py-3.5 px-3 text-right cursor-pointer hover:text-white"
                    onClick={() => handleSort("net_rating")}
                  >
                    Net Rtg {sortField === "net_rating" && (sortAsc ? "▲" : "▼")}
                  </th>
                  <th
                    className="py-3.5 px-3 text-right cursor-pointer hover:text-white"
                    onClick={() => handleSort("pace")}
                  >
                    Pace {sortField === "pace" && (sortAsc ? "▲" : "▼")}
                  </th>
                  <th
                    className="py-3.5 px-3 text-right cursor-pointer hover:text-white"
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
                      <td className="py-3 px-4 font-mono text-xs text-gray-500 font-bold">
                        {idx + 1}
                      </td>
                      <td className="py-3 px-4">
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
                      <td className="py-3 px-3 text-right font-mono text-gray-200 font-semibold">
                        {t.wins}-{t.losses}
                      </td>
                      <td className="py-3 px-3 text-right font-mono text-gray-300">
                        {(t.win_pct * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 px-3 text-center font-mono text-xs text-gray-400 hidden md:table-cell">
                        {t.home_record || "-"}
                      </td>
                      <td className="py-3 px-3 text-center font-mono text-xs text-gray-400 hidden md:table-cell">
                        {t.road_record || "-"}
                      </td>
                      <td className="py-3 px-3 text-center font-mono text-xs text-gray-400 hidden lg:table-cell">
                        {t.l10 || "-"}
                      </td>
                      <td className="py-3 px-3 text-right font-mono text-gray-300">
                        {t.off_rating.toFixed(1)}
                      </td>
                      <td className="py-3 px-3 text-right font-mono text-gray-300">
                        {t.def_rating.toFixed(1)}
                      </td>
                      <td className="py-3 px-3 text-right font-mono font-bold">
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
                      <td className="py-3 px-3 text-right font-mono text-gray-400">
                        {t.pace.toFixed(1)}
                      </td>
                      <td className="py-3 px-3 text-right font-mono text-gray-400">
                        {(t.ts_pct * 100).toFixed(1)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* =====================================================================
          SECTION 04 // EXECUTIVE ANALYTICS SUITE DIRECTORY
      ===================================================================== */}
      <section className="space-y-5 pt-6 border-t border-borderDark/70">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-extrabold uppercase tracking-widest bg-purple-500/15 text-purple-300 border border-purple-500/30">
              SECTION 04 // ANALYTICS MODULES
            </span>
          </div>
          <h2 className="text-2xl font-extrabold text-white">
            Executive Intelligence &amp; Simulation Modules
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            href="/live"
            className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg hover:border-red-500/50 transition group"
          >
            <span className="text-xs uppercase font-mono text-red-400 font-bold">Live Game Center</span>
            <h3 className="text-xl font-extrabold text-white mt-1 group-hover:text-red-400 transition">
              Win-Prob Candlesticks
            </h3>
            <p className="text-xs text-gray-400 mt-1.5 leading-relaxed">
              Team-colored minute-by-minute OHLC win probability candlesticks, live ESPN scoreboard, and court shot maps.
            </p>
          </Link>

          <Link
            href="/rapm"
            className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg hover:border-cyan-500/50 transition group"
          >
            <span className="text-xs uppercase font-mono text-cyan-400 font-bold">Player Impact</span>
            <h3 className="text-xl font-extrabold text-white mt-1 group-hover:text-cyan-400 transition">
              Ridge RAPM &amp; LEBRON
            </h3>
            <p className="text-xs text-gray-400 mt-1.5 leading-relaxed">
              5,393 player-seasons of Ridge-regularized RAPM, Wins Added, role archetypes, and 10-year career curves.
            </p>
          </Link>

          <Link
            href="/scouting"
            className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg hover:border-emerald-500/50 transition group"
          >
            <span className="text-xs uppercase font-mono text-emerald-400 font-bold">Scouting &amp; Draft</span>
            <h3 className="text-xl font-extrabold text-white mt-1 group-hover:text-emerald-400 transition">
              Clutch, Hustle &amp; VOPE
            </h3>
            <p className="text-xs text-gray-400 mt-1.5 leading-relaxed">
              469 clutch profiles, 567 hustle/deflection trackers, defensive FG% suppression, and 600-pick Draft VOPE.
            </p>
          </Link>

          <Link
            href="/cba"
            className="bg-surfaceCard p-5 rounded-2xl border border-borderDark shadow-lg hover:border-purple-500/50 transition group"
          >
            <span className="text-xs uppercase font-mono text-purple-400 font-bold">Front-Office Capology</span>
            <h3 className="text-xl font-extrabold text-white mt-1 group-hover:text-purple-400 transition">
              CBA Aprons &amp; Trade Machine
            </h3>
            <p className="text-xs text-gray-400 mt-1.5 leading-relaxed">
              All 30 team cap sheets, 450 active contracts, 1st/2nd Apron trade legality, and projected win deltas.
            </p>
          </Link>
        </div>
      </section>

      {/* =====================================================================
          RELEASE VERSION & DEPLOYMENT TELEMETRY FOOTER CALLOUT
      ===================================================================== */}
      <div className="rounded-2xl bg-surfaceCard/80 border border-borderDark px-5 py-3.5 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs font-mono text-gray-400">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="px-2.5 py-0.5 rounded-md bg-accent/20 text-accent border border-accent/40 font-extrabold">
            RELEASE {APP_RELEASE_VERSION}
          </span>
          <span>{APP_BUILD_TIMESTAMP}</span>
          <span>•</span>
          <span className="text-emerald-400">Default Season: {DEFAULT_SEASON}</span>
        </div>
        <div>
          All 30 Franchises Normalized to Current Official NBA Team Names
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
