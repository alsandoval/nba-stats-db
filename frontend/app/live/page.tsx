"use client";

import React, { useState, useEffect, useMemo, useRef, useCallback } from "react";
import {
  dataService,
  LiveGameFeed,
  LiveScoreboard,
  LivePlayerStat,
} from "@/lib/data-service";
import {
  DifferentialCandlestickChart,
  resolveMatchupTeamColors,
} from "@/components/differential-candlestick-chart";
import { CourtSVG } from "@/components/court-svg";

export default function LiveGameCompanionPage() {
  const [scoreboard, setScoreboard] = useState<LiveScoreboard | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [selectedGameId, setSelectedGameId] = useState<string>("");
  const [gameFeed, setGameFeed] = useState<LiveGameFeed | null>(null);
  const [loadingScoreboard, setLoadingScoreboard] = useState<boolean>(true);
  const [loadingGame, setLoadingGame] = useState<boolean>(true);
  const [lastRefreshed, setLastRefreshed] = useState<string>("");

  // Playback / Replay state
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(2); // 1x, 2x, 5x, 10x
  const [currentMinute, setCurrentMinute] = useState<number>(48);
  const [pbpFilter, setPbpFilter] = useState<"all" | "scoring" | "clutch" | "shots">("all");
  const [leftTab, setLeftTab] = useState<"floor" | "boxscore" | "shotmap">("floor");

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const pbpScrollRef = useRef<HTMLDivElement | null>(null);

  // Load scoreboard (either latest active slate or specific date)
  const loadScoreboard = useCallback(async (dateOverride?: string) => {
    setLoadingScoreboard(true);
    const sb = await dataService.getLiveScoreboard(dateOverride);
    setScoreboard(sb);
    if (sb.activeDate) {
      setSelectedDate(sb.activeDate);
    }
    if (sb.games && sb.games.length > 0) {
      setSelectedGameId((prev) => {
        const exists = sb.games.some((g) => g.gameId === prev);
        return exists ? prev : sb.games[0].gameId;
      });
    }
    setLastRefreshed(new Date().toLocaleTimeString());
    setLoadingScoreboard(false);
  }, []);

  // Initial scoreboard load
  useEffect(() => {
    loadScoreboard();
  }, [loadScoreboard]);

  // Load selected game's play-by-play, candlesticks, and boxscore
  const loadGameFeed = useCallback(async (gid: string, keepMinute = false) => {
    if (!gid) return;
    setLoadingGame(true);
    const feed = await dataService.getLiveGameFeed(gid);
    setGameFeed(feed);
    if (!keepMinute) {
      setCurrentMinute(feed.candlesticks?.length || 48);
      setIsPlaying(false);
    }
    setLastRefreshed(new Date().toLocaleTimeString());
    setLoadingGame(false);
  }, []);

  useEffect(() => {
    if (selectedGameId) {
      loadGameFeed(selectedGameId, false);
    }
  }, [selectedGameId, loadGameFeed]);

  // Auto-poll every 15 seconds if the currently selected game is LIVE in-progress
  useEffect(() => {
    if (!gameFeed || gameFeed.gameStatus !== 2 || !selectedGameId) return;
    const poll = setInterval(() => {
      loadScoreboard(selectedDate || undefined);
      loadGameFeed(selectedGameId, true);
    }, 15000);
    return () => clearInterval(poll);
  }, [gameFeed, selectedGameId, selectedDate, loadScoreboard, loadGameFeed]);

  const maxMinutes = gameFeed?.candlesticks?.length || 48;

  // Playback timer loop
  useEffect(() => {
    if (isPlaying) {
      const intervalMs = Math.max(180, Math.floor(1100 / playbackSpeed));
      timerRef.current = setInterval(() => {
        setCurrentMinute((prev) => {
          if (prev >= maxMinutes) {
            setIsPlaying(false);
            return maxMinutes;
          }
          return prev + 1;
        });
      }, intervalMs);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, playbackSpeed, maxMinutes]);

  // Shift date helper (-1 or +1 day)
  const shiftDate = (daysDelta: number) => {
    const base = selectedDate ? new Date(`${selectedDate}T12:00:00`) : new Date();
    base.setDate(base.getDate() + daysDelta);
    const y = base.getFullYear();
    const m = String(base.getMonth() + 1).padStart(2, "0");
    const d = String(base.getDate()).padStart(2, "0");
    const nextIso = `${y}-${m}-${d}`;
    setSelectedDate(nextIso);
    loadScoreboard(nextIso);
  };

  // Current minute's play-by-play events (up to current minute)
  const activePlays = useMemo(() => {
    if (!gameFeed) return [];
    return gameFeed.playByPlay.filter((p) => p.minute <= currentMinute);
  }, [gameFeed, currentMinute]);

  // Latest play at current minute
  const latestPlay = useMemo(() => {
    if (activePlays.length === 0) return null;
    return activePlays[activePlays.length - 1];
  }, [activePlays]);

  // Filtered plays for display in feed
  const displayPlays = useMemo(() => {
    if (!activePlays) return [];
    let list = [...activePlays];
    if (pbpFilter === "scoring") {
      list = list.filter(
        (p) => p.shotResult === "Made" || p.actionType.includes("pt") || p.actionType.includes("freethrow")
      );
    } else if (pbpFilter === "clutch") {
      list = list.filter((p) => Math.abs(p.wpa || 0) >= 0.035 || (p.minute >= 44 && p.shotResult === "Made"));
    } else if (pbpFilter === "shots") {
      list = list.filter((p) => p.xeFG !== null && p.xeFG !== undefined);
    }
    return list.reverse(); // Newest first
  }, [activePlays, pbpFilter]);

  // Current score at current playback minute
  const currentHomeScore = latestPlay ? latestPlay.scoreHome : gameFeed?.homeTeam.score || 0;
  const currentAwayScore = latestPlay ? latestPlay.scoreAway : gameFeed?.awayTeam.score || 0;
  const currentMargin = currentHomeScore - currentAwayScore;
  const currentWinProb = latestPlay ? latestPlay.homeWinProb : 0.5;

  // Dynamic Lead Changes, Times Tied, Biggest Lead from actual candlesticks/plays
  const gameSwingMetrics = useMemo(() => {
    if (!gameFeed || gameFeed.playByPlay.length === 0) {
      return { leadChanges: 0, timesTied: 0, biggestLeadStr: "Even" };
    }
    let leadChanges = 0;
    let timesTied = 0;
    let prevSign = 0;
    let maxHomeLead = 0;
    let maxAwayLead = 0;
    let prevMargin = 0;

    for (const ev of gameFeed.playByPlay) {
      const m = ev.scoreMargin;
      const sign = m > 0 ? 1 : m < 0 ? -1 : 0;
      if (sign !== 0 && prevSign !== 0 && sign !== prevSign) {
        leadChanges++;
      }
      if (m === 0 && prevMargin !== 0) {
        timesTied++;
      }
      if (m > maxHomeLead) maxHomeLead = m;
      if (-m > maxAwayLead) maxAwayLead = -m;
      if (sign !== 0) prevSign = sign;
      prevMargin = m;
    }

    const biggestLeadStr =
      maxHomeLead >= maxAwayLead
        ? `${gameFeed.homeTeam.tricode} +${maxHomeLead}`
        : `${gameFeed.awayTeam.tricode} +${maxAwayLead}`;

    return { leadChanges, timesTied, biggestLeadStr };
  }, [gameFeed]);

  // Active 5 players on floor for each team at current minute
  const { currentHomeLineup, currentAwayLineup } = useMemo(() => {
    if (!gameFeed) return { currentHomeLineup: [], currentAwayLineup: [] };
    const homePlayerIds = latestPlay?.homeLineup || gameFeed.homeTeam.starters;
    const awayPlayerIds = latestPlay?.awayLineup || gameFeed.awayTeam.starters;

    const hList = gameFeed.homeTeam.players.filter((p) => homePlayerIds.includes(p.personId));
    const aList = gameFeed.awayTeam.players.filter((p) => awayPlayerIds.includes(p.personId));

    return {
      currentHomeLineup: hList.length >= 5 ? hList.slice(0, 5) : gameFeed.homeTeam.players.slice(0, 5),
      currentAwayLineup: aList.length >= 5 ? aList.slice(0, 5) : gameFeed.awayTeam.players.slice(0, 5),
    };
  }, [gameFeed, latestPlay]);

  // Top Performer for each team (dynamically computed from real boxscore)
  const { homeLeader, awayLeader } = useMemo(() => {
    const pickBest = (players: LivePlayerStat[]): LivePlayerStat | null => {
      if (!players || players.length === 0) return null;
      return [...players].sort(
        (a, b) =>
          b.points + b.rebounds * 1.2 + b.assists * 1.5 - (a.points + a.rebounds * 1.2 + a.assists * 1.5)
      )[0];
    };
    return {
      homeLeader: pickBest(gameFeed?.homeTeam.players || []),
      awayLeader: pickBest(gameFeed?.awayTeam.players || []),
    };
  }, [gameFeed]);

  // Jump to decisive clutch plays (Minute 44+)
  const jumpToClutch = () => {
    setCurrentMinute(Math.min(maxMinutes, 44));
    setIsPlaying(true);
  };

  // Top 5 Game-Changing Win Probability Swings (WPA)
  const topWpaSwings = useMemo(() => {
    if (!gameFeed || !gameFeed.playByPlay) return [];
    return [...gameFeed.playByPlay]
      .filter((p) => Math.abs(p.wpa || 0) >= 0.03)
      .sort((a, b) => Math.abs(b.wpa || 0) - Math.abs(a.wpa || 0))
      .slice(0, 5);
  }, [gameFeed]);

  // Synthesize live spatial court coordinates for all field goal attempts up to currentMinute
  const liveCourtShots = useMemo(() => {
    if (!activePlays.length) return [];
    const shotEvents = activePlays.filter(
      (p) => p.shotResult === "Made" || p.shotResult === "Missed"
    );
    return shotEvents.map((ev, i) => {
      const dist = ev.shotDistance ?? (ev.actionType === "3pt" ? 25 : 8);
      const seed = (ev.actionNumber * 9301 + 49297) % 233280;
      const frac = seed / 233280.0;
      const angle = Math.PI * (0.12 + frac * 0.76);
      const x = Number((dist * Math.cos(angle)).toFixed(1));
      const y = Number(Math.max(1.5, dist * Math.sin(angle)).toFixed(1));
      return {
        x,
        y,
        dist,
        made: ev.shotResult === "Made" ? 1 : 0,
        is_3pt: ev.actionType === "3pt" ? 1 : 0,
        p_hat: ev.xeFG || 0.5,
      };
    });
  }, [activePlays]);

  const resolvedColors = useMemo(
    () =>
      resolveMatchupTeamColors(
        gameFeed?.homeTeam.tricode || "BOS",
        gameFeed?.awayTeam.tricode || "LAL",
        gameFeed?.homeTeam.color,
        gameFeed?.awayTeam.color
      ),
    [gameFeed]
  );

  if ((loadingScoreboard && !scoreboard) || (!gameFeed && loadingGame)) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center text-white">
        <div className="w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin mb-4" />
        <p className="font-mono text-sm text-gray-400">
          Connecting to Live NBA Scoreboard &amp; Play-by-Play Stream...
        </p>
      </div>
    );
  }

  if (!gameFeed) return null;

  const { homeTeam, awayTeam, candlesticks } = gameFeed;

  return (
    <div className="min-h-screen bg-background text-gray-100 flex flex-col pb-16">
      {/* 1. TOP LIVE SCOREBOARD TICKER & DATE PICKER */}
      <section className="bg-surface/95 border-b border-borderDark px-4 py-2.5 sticky top-[57px] z-40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto flex flex-col gap-2.5">
          {/* Row 1: Date Picker, Quick Slates & Live Refresh */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-borderDark/50 pb-2">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] font-mono text-gray-400 uppercase tracking-wider font-bold mr-1">
                NBA Date:
              </span>
              <button
                onClick={() => shiftDate(-1)}
                className="px-2 py-1 rounded bg-surfaceCard hover:bg-surface border border-borderDark text-xs font-mono text-gray-300 hover:text-white transition"
                title="Previous Day"
              >
                ◀ Prev
              </button>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => {
                  setSelectedDate(e.target.value);
                  if (e.target.value) loadScoreboard(e.target.value);
                }}
                className="bg-surfaceCard border border-borderDark rounded px-2.5 py-1 text-xs font-mono text-white focus:outline-none focus:border-accent"
              />
              <button
                onClick={() => shiftDate(1)}
                className="px-2 py-1 rounded bg-surfaceCard hover:bg-surface border border-borderDark text-xs font-mono text-gray-300 hover:text-white transition"
                title="Next Day"
              >
                Next ▶
              </button>

              <button
                onClick={() => loadScoreboard()}
                className="ml-1 px-2.5 py-1 rounded bg-accent/20 hover:bg-accent/30 border border-accent/40 text-accent text-xs font-mono font-bold transition"
              >
                🔥 Latest Active Slate
              </button>
            </div>

            {/* Live Status & Refresh */}
            <div className="flex items-center gap-2 text-xs font-mono">
              <button
                onClick={() => {
                  loadScoreboard(selectedDate || undefined);
                  if (selectedGameId) loadGameFeed(selectedGameId, true);
                }}
                className="px-2.5 py-1 rounded bg-surfaceCard hover:bg-surface border border-borderDark text-gray-300 hover:text-white transition flex items-center gap-1"
              >
                <span>🔄 Refresh</span>
                {lastRefreshed && <span className="text-[10px] text-gray-500">({lastRefreshed})</span>}
              </button>
              <div className="flex items-center gap-1.5 bg-emerald-950/50 text-emerald-400 border border-emerald-800/50 px-2.5 py-1 rounded-full">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="font-bold tracking-wider text-[11px]">
                  {gameFeed.isLiveRealData ? "REAL NBA LIVE API" : "SNAPSHOT FEED"}
                </span>
              </div>
            </div>
          </div>

          {/* Row 2: Scrollable Game Switcher Cards for Selected Date */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin scrollbar-thumb-borderDark">
            <span className="text-[11px] font-mono text-gray-400 uppercase tracking-wider font-bold whitespace-nowrap">
              {scoreboard?.games.length || 0} Games:
            </span>
            {scoreboard?.games.map((g) => {
              const active = g.gameId === selectedGameId;
              return (
                <button
                  key={g.gameId}
                  onClick={() => setSelectedGameId(g.gameId)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono transition flex items-center gap-2.5 border whitespace-nowrap ${
                    active
                      ? "bg-accent/20 border-accent text-white shadow-sm font-bold"
                      : "bg-surfaceCard/80 border-borderDark text-gray-300 hover:text-white hover:bg-surfaceCard"
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      g.gameStatus === 2
                        ? "bg-red-500 animate-ping"
                        : g.gameStatus === 1
                        ? "bg-amber-400"
                        : "bg-emerald-400"
                    }`}
                  />
                  <span>
                    {g.awayTeam.tricode} <strong className="text-white">{g.awayTeam.score}</strong> @{" "}
                    {g.homeTeam.tricode} <strong className="text-white">{g.homeTeam.score}</strong>
                  </span>
                  <span className="text-[10px] text-gray-400 font-normal px-1.5 py-0.5 bg-surface rounded">
                    {g.gameStatusText}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* 2. MARQUEE GAME BANNER & DIGITAL SCOREBOARD */}
      <section className="max-w-7xl mx-auto w-full px-4 pt-5 relative">
        {loadingGame && (
          <div className="absolute inset-0 z-30 bg-background/60 backdrop-blur-xs flex items-center justify-center rounded-2xl">
            <div className="bg-surfaceCard border border-borderDark px-4 py-2 rounded-xl text-xs font-mono text-white flex items-center gap-2 shadow-xl">
              <span className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              Loading Play-by-Play &amp; Candlesticks...
            </div>
          </div>
        )}

        <div className="bg-gradient-to-r from-surfaceCard via-surface to-surfaceCard border border-borderDark rounded-2xl p-5 md:p-6 shadow-2xl relative overflow-hidden">
          <div className="absolute inset-0 opacity-5 pointer-events-none bg-[radial-gradient(#3b82f6_1px,transparent_1px)] [background-size:16px_16px]" />

          <div className="relative z-10 grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
            {/* Away Team Card */}
            <div className="md:col-span-4 flex items-center gap-4">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center font-black text-xl text-white shadow-lg border border-white/10 overflow-hidden shrink-0"
                style={{ backgroundColor: resolvedColors.awayColor }}
              >
                {awayTeam.logo ? (
                  <img src={awayTeam.logo} alt={awayTeam.tricode} className="w-11 h-11 object-contain" />
                ) : (
                  awayTeam.tricode
                )}
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-mono text-gray-400 uppercase tracking-widest">
                  {awayTeam.city || "Away"}
                </span>
                <h2 className="text-xl md:text-2xl font-black text-white">{awayTeam.name}</h2>
                <span className="text-xs text-gray-400 font-mono">
                  {awayTeam.record ? `${awayTeam.record} • Road` : awayTeam.tricode}
                </span>
              </div>
              <div className="ml-auto text-right">
                <span className="text-4xl md:text-5xl font-black text-white tracking-tight">
                  {currentAwayScore}
                </span>
                <div className="text-[10px] text-gray-400 font-mono mt-0.5">
                  Final: {awayTeam.score}
                </div>
              </div>
            </div>

            {/* Center: Live Game Clock, Period, and Possession Indicator */}
            <div className="md:col-span-4 flex flex-col items-center justify-center text-center px-2 py-3 bg-surface/80 rounded-xl border border-borderDark/80">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-bold text-accent tracking-wider font-mono bg-accent/10 px-2 py-0.5 rounded border border-accent/20">
                  {currentMinute >= maxMinutes
                    ? gameFeed.gameStatusText
                    : latestPlay
                    ? `${latestPlay.period <= 4 ? `Q${latestPlay.period}` : `OT${latestPlay.period - 4}`} • MIN ${currentMinute}`
                    : `MIN ${currentMinute}`}
                </span>
                <span className="text-xs text-gray-400 font-mono truncate max-w-[180px]">
                  • {gameFeed.arena}
                </span>
              </div>

              {/* Game Clock Display */}
              <div className="text-2xl md:text-3xl font-black font-mono tracking-wider text-white">
                {latestPlay?.clock
                  ? latestPlay.clock.replace("PT", "").replace(".00S", "").replace("M", ":")
                  : "00:00"}
              </div>

              {/* Possession Arrow Indicator */}
              <div className="flex items-center gap-2 mt-1.5 text-xs font-mono">
                <span className="text-gray-400">Active Ball:</span>
                <span className="flex items-center gap-1 font-bold text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded border border-amber-400/30 animate-pulse">
                  🏀 {latestPlay?.teamTricode || homeTeam.tricode}
                </span>
              </div>

              {/* Live Margin & Win Probability Badges */}
              <div className="flex items-center gap-2 mt-2 font-mono text-xs">
                <span
                  className="px-2 py-0.5 rounded font-bold text-white border"
                  style={{
                    backgroundColor:
                      currentMargin > 0
                        ? `${resolvedColors.homeColor}33`
                        : currentMargin < 0
                        ? `${resolvedColors.awayColor}33`
                        : "#1f2937",
                    borderColor:
                      currentMargin > 0
                        ? resolvedColors.homeColor
                        : currentMargin < 0
                        ? resolvedColors.awayColor
                        : "#374151",
                  }}
                >
                  {currentMargin > 0
                    ? `+${currentMargin} ${homeTeam.tricode}`
                    : currentMargin < 0
                    ? `+${Math.abs(currentMargin)} ${awayTeam.tricode}`
                    : "TIED"}
                </span>

                <span
                  className="px-2 py-0.5 rounded font-bold text-white border"
                  style={{
                    backgroundColor:
                      currentWinProb >= 0.5
                        ? `${resolvedColors.homeColor}33`
                        : `${resolvedColors.awayColor}33`,
                    borderColor:
                      currentWinProb >= 0.5 ? resolvedColors.homeColor : resolvedColors.awayColor,
                  }}
                >
                  {currentWinProb >= 0.5
                    ? `${(currentWinProb * 100).toFixed(1)}% ${homeTeam.tricode} WP`
                    : `${((1 - currentWinProb) * 100).toFixed(1)}% ${awayTeam.tricode} WP`}
                </span>
              </div>
            </div>

            {/* Home Team Card */}
            <div className="md:col-span-4 flex items-center justify-end gap-4">
              <div className="mr-auto text-left md:order-1">
                <span className="text-4xl md:text-5xl font-black text-white tracking-tight">
                  {currentHomeScore}
                </span>
                <div className="text-[10px] text-gray-400 font-mono mt-0.5">
                  Final: {homeTeam.score}
                </div>
              </div>
              <div className="flex flex-col text-right md:order-2">
                <span className="text-xs font-mono text-gray-400 uppercase tracking-widest">
                  {homeTeam.city || "Home"}
                </span>
                <h2 className="text-xl md:text-2xl font-black text-white">{homeTeam.name}</h2>
                <span className="text-xs text-gray-400 font-mono">
                  {homeTeam.record ? `${homeTeam.record} • Home` : homeTeam.tricode}
                </span>
              </div>
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center font-black text-xl text-white shadow-lg border border-white/10 overflow-hidden shrink-0 md:order-3"
                style={{ backgroundColor: resolvedColors.homeColor }}
              >
                {homeTeam.logo ? (
                  <img src={homeTeam.logo} alt={homeTeam.tricode} className="w-11 h-11 object-contain" />
                ) : (
                  homeTeam.tricode
                )}
              </div>
            </div>
          </div>

          {/* Dynamic Quarter-by-Quarter Linescore Mini-Table */}
          <div className="mt-5 pt-4 border-t border-borderDark/60 flex flex-wrap items-center justify-between text-xs font-mono gap-4">
            <div className="flex flex-wrap items-center gap-4">
              <span className="text-gray-400 font-bold">Linescore:</span>
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-gray-300">
                  <strong style={{ color: resolvedColors.awayColor }}>{awayTeam.tricode}:</strong>{" "}
                  {awayTeam.periods.map((p) => p.score).join(" | ")} ={" "}
                  <strong className="text-white">{awayTeam.score}</strong>
                </span>
                <span className="text-gray-500">vs</span>
                <span className="text-gray-300">
                  <strong style={{ color: resolvedColors.homeColor }}>{homeTeam.tricode}:</strong>{" "}
                  {homeTeam.periods.map((p) => p.score).join(" | ")} ={" "}
                  <strong className="text-white">{homeTeam.score}</strong>
                </span>
              </div>
            </div>
            <div className="flex items-center gap-4 text-[11px] text-gray-400">
              <span>
                Lead Changes: <strong className="text-white">{gameSwingMetrics.leadChanges}</strong>
              </span>
              <span>
                Times Tied: <strong className="text-white">{gameSwingMetrics.timesTied}</strong>
              </span>
              <span>
                Biggest Lead: <strong className="text-white">{gameSwingMetrics.biggestLeadStr}</strong>
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. INTERACTIVE REPLAY & SIMULATION DECK */}
      <section className="max-w-7xl mx-auto w-full px-4 pt-4">
        <div className="bg-surfaceCard border border-borderDark rounded-xl p-3 md:p-4 shadow-card flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (currentMinute >= maxMinutes) setCurrentMinute(1);
                setIsPlaying(!isPlaying);
              }}
              className={`px-4 py-2 rounded-lg font-bold text-xs flex items-center gap-2 transition ${
                isPlaying
                  ? "bg-amber-500 text-black shadow-lg shadow-amber-500/20"
                  : "bg-accent hover:bg-accentHover text-white shadow-lg shadow-accent/20"
              }`}
            >
              <span>{isPlaying ? "⏸ PAUSE" : "▶ PLAY REPLAY"}</span>
            </button>

            <button
              onClick={() => {
                setCurrentMinute(1);
                setIsPlaying(false);
              }}
              className="p-2 bg-surface hover:bg-surface/80 border border-borderDark rounded-lg text-gray-300 hover:text-white text-xs font-mono"
              title="Reset to Tip-off (Minute 1)"
            >
              ⏮ Tip-off
            </button>

            <button
              onClick={jumpToClutch}
              className="px-3 py-1.5 bg-gradient-to-r from-amber-500/20 to-orange-500/20 hover:from-amber-500/30 hover:to-orange-500/30 border border-amber-500/40 text-amber-300 rounded-lg text-xs font-bold transition flex items-center gap-1.5"
            >
              ⚡ Jump to Clutch (Q4)
            </button>
          </div>

          {/* Timeline Scrubber Slider */}
          <div className="flex-1 max-w-xl w-full flex items-center gap-3">
            <span className="text-xs font-mono text-gray-400 whitespace-nowrap">Q1 12:00</span>
            <input
              type="range"
              min="1"
              max={maxMinutes}
              value={currentMinute}
              onChange={(e) => {
                setCurrentMinute(parseInt(e.target.value, 10));
              }}
              className="w-full h-2 bg-surface rounded-lg appearance-none cursor-pointer accent-accent"
            />
            <span className="text-xs font-mono text-gray-400 whitespace-nowrap">
              {maxMinutes > 48 ? "OT 00:00" : "Q4 00:00"}
            </span>
            <span className="bg-surface border border-borderDark px-2.5 py-1 rounded text-xs font-bold font-mono text-white min-w-[54px] text-center">
              m{currentMinute}
            </span>
          </div>

          {/* Replay Speed Buttons */}
          <div className="flex items-center bg-surface border border-borderDark rounded-lg p-0.5 text-xs font-mono">
            {[1, 2, 5, 10].map((spd) => (
              <button
                key={`spd-${spd}`}
                onClick={() => setPlaybackSpeed(spd)}
                className={`px-2 py-1 rounded transition ${
                  playbackSpeed === spd
                    ? "bg-accent text-white font-bold"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                {spd}x
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 4. FINANCIAL-GRADE CANDLESTICK & VOLUME ENGINE */}
      <section className="max-w-7xl mx-auto w-full px-4 pt-4">
        <DifferentialCandlestickChart
          candlesticks={candlesticks}
          currentMinute={currentMinute}
          onSelectMinute={(m) => setCurrentMinute(m)}
          homeTricode={homeTeam.tricode}
          awayTricode={awayTeam.tricode}
          homeColor={homeTeam.color}
          awayColor={awayTeam.color}
        />

        {/* NEW: TOP 5 DECISIVE WIN PROBABILITY SWING ALERTS (CLICK TO JUMP) */}
        {topWpaSwings.length > 0 && (
          <div className="mt-3 bg-surfaceCard border border-borderDark rounded-xl p-3 flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-mono uppercase text-amber-400 font-extrabold whitespace-nowrap mr-1">
              ⚡ Key Momentum Swings (Click to Jump):
            </span>
            {topWpaSwings.map((sw, idx) => {
              const isHomeSwing = (sw.wpa || 0) > 0;
              const swColor = isHomeSwing ? resolvedColors.homeColor : resolvedColors.awayColor;
              return (
                <button
                  key={`wpa-swing-${idx}`}
                  onClick={() => setCurrentMinute(sw.minute)}
                  style={{ borderColor: `${swColor}66` }}
                  className="px-2.5 py-1 rounded-lg bg-surface hover:bg-surfaceCard border text-[11px] font-mono text-left transition flex items-center gap-2 max-w-xs truncate"
                  title={sw.description}
                >
                  <span
                    className="font-extrabold px-1.5 py-0.2 rounded text-[10px] text-white"
                    style={{ backgroundColor: swColor }}
                  >
                    m{sw.minute} ({sw.wpa > 0 ? `+${(sw.wpa * 100).toFixed(1)}%` : `${(sw.wpa * 100).toFixed(1)}%`} WP)
                  </span>
                  <span className="text-gray-300 truncate">{sw.description}</span>
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* 5. SPLIT VIEW: ON-COURT LINEUPS / FULL BOXSCORE / LIVE SHOT MAP & LIVE QUANT PLAY-BY-PLAY */}
      <section className="max-w-7xl mx-auto w-full px-4 pt-4 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: ACTIVE 10 PLAYERS, BOXSCORE OR LIVE SHOT MAP (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <div className="bg-surfaceCard border border-borderDark rounded-xl p-4 shadow-card">
            <div className="flex items-center justify-between border-b border-borderDark/60 pb-2.5 mb-3">
              <div className="flex items-center gap-1 bg-surface border border-borderDark rounded-lg p-0.5 text-xs font-mono">
                <button
                  onClick={() => setLeftTab("floor")}
                  className={`px-2.5 py-1 rounded transition ${
                    leftTab === "floor" ? "bg-accent text-white font-bold" : "text-gray-400 hover:text-white"
                  }`}
                >
                  🛡️ On-Court 10
                </button>
                <button
                  onClick={() => setLeftTab("boxscore")}
                  className={`px-2.5 py-1 rounded transition ${
                    leftTab === "boxscore" ? "bg-accent text-white font-bold" : "text-gray-400 hover:text-white"
                  }`}
                >
                  📋 Boxscore
                </button>
                <button
                  onClick={() => setLeftTab("shotmap")}
                  className={`px-2.5 py-1 rounded transition ${
                    leftTab === "shotmap" ? "bg-accent text-white font-bold" : "text-gray-400 hover:text-white"
                  }`}
                >
                  🎯 Live Shot Map
                </button>
              </div>
              <span className="text-[11px] font-mono text-gray-400">
                m{currentMinute}
              </span>
            </div>

            {leftTab === "floor" ? (
              <>
                {/* Home 5-Man On Court */}
                <div className="mb-4">
                  <div className="flex items-center justify-between text-xs font-bold text-gray-300 mb-2">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: resolvedColors.homeColor }} />
                      {homeTeam.name} On Floor ({homeTeam.tricode})
                    </span>
                    <span className="font-mono" style={{ color: resolvedColors.homeColor }}>
                      {currentMargin >= 0 ? `Lead: +${currentMargin}` : `Deficit: ${currentMargin}`}
                    </span>
                  </div>

                  <div className="space-y-1.5">
                    {currentHomeLineup.map((p) => (
                      <div
                        key={`home-lineup-${p.personId}`}
                        className="flex items-center justify-between bg-surface/70 border border-borderDark/50 rounded-lg px-3 py-1.5 text-xs font-mono"
                      >
                        <div className="flex items-center gap-2 truncate">
                          <span className="text-gray-400 font-bold w-5">{p.jerseyNum}</span>
                          <span className="text-white font-medium truncate">{p.name}</span>
                          <span className="text-[10px] text-gray-400">({p.position})</span>
                        </div>
                        <div className="flex items-center gap-2.5 text-[11px] shrink-0">
                          <span>{p.points} PTS</span>
                          <span className="text-gray-400">{p.rebounds} REB</span>
                          <span className="text-gray-400">{p.assists} AST</span>
                          <span className={`font-bold ${p.plusMinus >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                            {p.plusMinus >= 0 ? `+${p.plusMinus}` : p.plusMinus}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Away 5-Man On Court */}
                <div>
                  <div className="flex items-center justify-between text-xs font-bold text-gray-300 mb-2">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: resolvedColors.awayColor }} />
                      {awayTeam.name} On Floor ({awayTeam.tricode})
                    </span>
                    <span className="font-mono" style={{ color: resolvedColors.awayColor }}>
                      {currentMargin <= 0 ? `Lead: +${Math.abs(currentMargin)}` : `Deficit: -${currentMargin}`}
                    </span>
                  </div>

                  <div className="space-y-1.5">
                    {currentAwayLineup.map((p) => (
                      <div
                        key={`away-lineup-${p.personId}`}
                        className="flex items-center justify-between bg-surface/70 border border-borderDark/50 rounded-lg px-3 py-1.5 text-xs font-mono"
                      >
                        <div className="flex items-center gap-2 truncate">
                          <span className="text-gray-400 font-bold w-5">{p.jerseyNum}</span>
                          <span className="text-white font-medium truncate">{p.name}</span>
                          <span className="text-[10px] text-gray-400">({p.position})</span>
                        </div>
                        <div className="flex items-center gap-2.5 text-[11px] shrink-0">
                          <span>{p.points} PTS</span>
                          <span className="text-gray-400">{p.rebounds} REB</span>
                          <span className="text-gray-400">{p.assists} AST</span>
                          <span className={`font-bold ${p.plusMinus >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                            {p.plusMinus >= 0 ? `+${p.plusMinus}` : p.plusMinus}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : leftTab === "boxscore" ? (
              /* Full Team Boxscores View */
              <div className="max-h-[430px] overflow-y-auto space-y-4 pr-1 scrollbar-thin scrollbar-thumb-borderDark">
                {[awayTeam, homeTeam].map((tm) => (
                  <div key={`box-${tm.tricode}`}>
                    <div className="text-xs font-bold text-white mb-1.5 flex items-center justify-between">
                      <span>
                        {tm.city} {tm.name} ({tm.tricode})
                      </span>
                      <span className="text-gray-400 font-mono">{tm.score} PTS</span>
                    </div>
                    <table className="w-full text-[11px] font-mono text-left border-collapse">
                      <thead>
                        <tr className="text-gray-400 border-b border-borderDark">
                          <th className="py-1">Player</th>
                          <th className="py-1 text-right">MIN</th>
                          <th className="py-1 text-right">PTS</th>
                          <th className="py-1 text-right">REB</th>
                          <th className="py-1 text-right">AST</th>
                          <th className="py-1 text-right">FG</th>
                          <th className="py-1 text-right">+/-</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tm.players.map((p) => (
                          <tr key={`row-${p.personId}`} className="border-b border-borderDark/30 hover:bg-surface/60">
                            <td className="py-1 text-white truncate max-w-[125px]">
                              {p.name} <span className="text-gray-500 text-[9px]">{p.position}</span>
                            </td>
                            <td className="py-1 text-right text-gray-400">{p.minutes}</td>
                            <td className="py-1 text-right font-bold text-white">{p.points}</td>
                            <td className="py-1 text-right text-gray-300">{p.rebounds}</td>
                            <td className="py-1 text-right text-gray-300">{p.assists}</td>
                            <td className="py-1 text-right text-gray-400">{p.fgStr || `${p.fgPct}%`}</td>
                            <td
                              className={`py-1 text-right font-bold ${
                                p.plusMinus >= 0 ? "text-emerald-400" : "text-red-400"
                              }`}
                            >
                              {p.plusMinus >= 0 ? `+${p.plusMinus}` : p.plusMinus}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            ) : (
              /* Live Shot Map View */
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-mono text-gray-400">
                  <span>Shots through Minute {currentMinute}: <strong className="text-white">{liveCourtShots.length} FGA</strong></span>
                  <span>Made: <strong className="text-emerald-400">{liveCourtShots.filter((s) => s.made === 1).length}</strong></span>
                </div>
                <div className="w-full aspect-[50/47] rounded-xl overflow-hidden bg-surface border border-borderDark p-2">
                  <CourtSVG shots={liveCourtShots} />
                </div>
              </div>
            )}
          </div>

          {/* Dynamically Computed Top Impact Players Head-to-Head */}
          <div className="bg-surfaceCard border border-borderDark rounded-xl p-4 shadow-card">
            <h3 className="text-xs font-extrabold text-white uppercase tracking-wider font-mono mb-3">
              Top Impact Performers ({awayTeam.tricode} vs {homeTeam.tricode})
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {awayLeader && (
                <div className="p-3 bg-surface rounded-lg border border-borderDark text-xs font-mono">
                  <span className="text-[10px] text-red-400 font-bold">{awayTeam.tricode} LEADER</span>
                  <div className="font-bold text-white text-sm mt-0.5 truncate">{awayLeader.name}</div>
                  <div className="text-gray-400 text-[11px] mt-1">
                    {awayLeader.points} PTS • {awayLeader.rebounds} REB • {awayLeader.assists} AST
                  </div>
                  <div className="text-gray-300 font-bold mt-0.5">
                    {awayLeader.plusMinus >= 0 ? `+${awayLeader.plusMinus}` : awayLeader.plusMinus} +/- •{" "}
                    {awayLeader.fgStr || `${awayLeader.fgPct}% FG`}
                  </div>
                </div>
              )}

              {homeLeader && (
                <div className="p-3 bg-surface rounded-lg border border-borderDark text-xs font-mono">
                  <span className="text-[10px] text-accent font-bold">{homeTeam.tricode} LEADER</span>
                  <div className="font-bold text-white text-sm mt-0.5 truncate">{homeLeader.name}</div>
                  <div className="text-gray-400 text-[11px] mt-1">
                    {homeLeader.points} PTS • {homeLeader.rebounds} REB • {homeLeader.assists} AST
                  </div>
                  <div className="text-emerald-400 font-bold mt-0.5">
                    {homeLeader.plusMinus >= 0 ? `+${homeLeader.plusMinus}` : homeLeader.plusMinus} +/- •{" "}
                    {homeLeader.fgStr || `${homeLeader.fgPct}% FG`}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: QUANTITATIVE PLAY-BY-PLAY FEED (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-3">
          <div className="bg-surfaceCard border border-borderDark rounded-xl p-4 shadow-card flex flex-col h-[680px]">
            {/* PBP Filter Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-borderDark/60 pb-3 mb-3">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-extrabold text-white flex items-center gap-1.5">
                  <span>⚡</span> QUANTITATIVE PLAY-BY-PLAY
                </h3>
                <span className="bg-surface px-2 py-0.5 rounded text-[11px] font-mono text-gray-400">
                  {displayPlays.length} Plays
                </span>
              </div>

              {/* Filter Tabs */}
              <div className="flex items-center bg-surface border border-borderDark rounded-lg p-0.5 text-xs font-mono">
                {[
                  { key: "all", label: "All Plays" },
                  { key: "scoring", label: "Scoring" },
                  { key: "clutch", label: "Clutch WPA" },
                  { key: "shots", label: "xeFG% Shots" },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setPbpFilter(tab.key as any)}
                    className={`px-2.5 py-1 rounded transition ${
                      pbpFilter === tab.key
                        ? "bg-accent text-white font-bold shadow-sm"
                        : "text-gray-400 hover:text-white"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Scrollable Event List */}
            <div
              ref={pbpScrollRef}
              className="flex-1 overflow-y-auto space-y-2 pr-1 scrollbar-thin scrollbar-thumb-borderDark"
            >
              {displayPlays.map((ev, idx) => {
                const isClutch = Math.abs(ev.wpa || 0) >= 0.04;
                const isMadeShot = ev.shotResult === "Made";

                return (
                  <div
                    key={`pbp-${ev.actionNumber || idx}`}
                    className={`p-2.5 rounded-lg border text-xs font-mono transition ${
                      isClutch
                        ? "bg-amber-950/20 border-amber-500/40 shadow-sm"
                        : isMadeShot
                        ? "bg-surface/90 border-borderDark/80"
                        : "bg-surface/50 border-borderDark/40 text-gray-300"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-gray-400">
                          {ev.period <= 4 ? `Q${ev.period}` : `OT${ev.period - 4}`}{" "}
                          {ev.clock.replace("PT", "").replace(".00S", "")}
                        </span>
                        <span
                          className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                            ev.teamTricode === homeTeam.tricode
                              ? "bg-blue-950 text-blue-300 border border-blue-800"
                              : "bg-red-950 text-red-300 border border-red-800"
                          }`}
                        >
                          {ev.teamTricode}
                        </span>
                        <span className="text-gray-400 text-[11px]">
                          { awayTeam.tricode } {ev.scoreAway} - { homeTeam.tricode } {ev.scoreHome}
                        </span>
                      </div>

                      {/* Right Badges: WPA & xeFG% */}
                      <div className="flex items-center gap-1.5">
                        {ev.wpa !== undefined && ev.wpa !== 0 && (
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              ev.wpa > 0
                                ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                                : "bg-red-950 text-red-300 border border-red-800"
                            }`}
                            title="Home Win Probability Swing on Play"
                          >
                            {ev.wpa > 0 ? `+${(ev.wpa * 100).toFixed(1)}%` : `${(ev.wpa * 100).toFixed(1)}%`} WPA
                          </span>
                        )}

                        {ev.xeFG !== null && ev.xeFG !== undefined && (
                          <span
                            className="bg-purple-950/70 text-purple-300 border border-purple-800/60 px-1.5 py-0.5 rounded text-[10px] font-bold"
                            title="Expected Effective Field Goal %"
                          >
                            xeFG%: {(ev.xeFG * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Play Description */}
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-gray-100 font-sans text-xs">{ev.description}</p>
                      {ev.shotArea && (
                        <span className="text-[10px] text-gray-500 whitespace-nowrap hidden sm:inline">
                          [{ev.shotArea}]
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}

              {displayPlays.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-gray-500 text-xs">
                  <span>No events match the selected filter.</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
