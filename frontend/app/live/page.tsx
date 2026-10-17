"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import {
  dataService,
  LiveGameFeed,
  LiveScoreboard,
  LivePlayEvent,
  LivePlayerStat,
} from "@/lib/data-service";
import { DifferentialCandlestickChart } from "@/components/differential-candlestick-chart";

export default function LiveGameCompanionPage() {
  const [scoreboard, setScoreboard] = useState<LiveScoreboard | null>(null);
  const [selectedGameId, setSelectedGameId] = useState<string>("0022300001");
  const [gameFeed, setGameFeed] = useState<LiveGameFeed | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Playback / Replay state
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(2); // 1x, 2x, 5x, 10x
  const [currentMinute, setCurrentMinute] = useState<number>(48); // default to end of game or live
  const [pbpFilter, setPbpFilter] = useState<"all" | "scoring" | "clutch" | "shots">("all");

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const pbpScrollRef = useRef<HTMLDivElement | null>(null);

  // Load scoreboard and game feed
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      const [sb, feed] = await Promise.all([
        dataService.getLiveScoreboard(),
        dataService.getLiveGameFeed(selectedGameId),
      ]);
      setScoreboard(sb);
      setGameFeed(feed);
      setLoading(false);
    }
    loadData();
  }, [selectedGameId]);

  // Playback timer loop
  useEffect(() => {
    if (isPlaying) {
      const intervalMs = Math.max(200, Math.floor(1200 / playbackSpeed));
      timerRef.current = setInterval(() => {
        setCurrentMinute((prev) => {
          if (prev >= 48) {
            setIsPlaying(false);
            return 48;
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
  }, [isPlaying, playbackSpeed]);

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
      list = list.filter((p) => p.actionType.includes("pt") || p.actionType.includes("freethrow"));
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

  // Active 5 players on floor for each team at current minute
  const { currentHomeLineup, currentAwayLineup } = useMemo(() => {
    if (!gameFeed) return { currentHomeLineup: [], currentAwayLineup: [] };
    const homePlayerIds = latestPlay?.homeLineup || gameFeed.homeTeam.starters;
    const awayPlayerIds = latestPlay?.awayLineup || gameFeed.awayTeam.starters;

    const hList = gameFeed.homeTeam.players.filter((p) => homePlayerIds.includes(p.personId));
    const aList = gameFeed.awayTeam.players.filter((p) => awayPlayerIds.includes(p.personId));

    return {
      currentHomeLineup: hList.length > 0 ? hList : gameFeed.homeTeam.players.slice(0, 5),
      currentAwayLineup: aList.length > 0 ? aList : gameFeed.awayTeam.players.slice(0, 5),
    };
  }, [gameFeed, latestPlay]);

  // Jump to decisive clutch plays (Minute 44+)
  const jumpToClutch = () => {
    setCurrentMinute(44);
    setIsPlaying(true);
  };

  if (loading || !gameFeed) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center text-white">
        <div className="w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin mb-4" />
        <p className="font-mono text-sm text-gray-400">Loading Live NBA Companion Feed & Candlesticks...</p>
      </div>
    );
  }

  const { homeTeam, awayTeam, candlesticks } = gameFeed;

  return (
    <div className="min-h-screen bg-background text-gray-100 flex flex-col pb-16">
      {/* 1. TOP LIVE SCOREBOARD TICKER */}
      <section className="bg-surface/90 border-b border-borderDark px-4 py-2 sticky top-[57px] z-40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
          {/* Active Games Switcher */}
          <div className="flex items-center gap-2 overflow-x-auto w-full md:w-auto pb-1 md:pb-0 scrollbar-none">
            <span className="text-[11px] font-mono text-gray-400 uppercase tracking-wider font-bold">Games:</span>
            {scoreboard?.games.map((g) => {
              const active = g.gameId === selectedGameId;
              return (
                <button
                  key={g.gameId}
                  onClick={() => setSelectedGameId(g.gameId)}
                  className={`px-3 py-1 rounded-lg text-xs font-mono transition flex items-center gap-2 border whitespace-nowrap ${
                    active
                      ? "bg-accent/20 border-accent text-white shadow-sm font-bold"
                      : "bg-surfaceCard/80 border-borderDark text-gray-400 hover:text-white hover:bg-surfaceCard"
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${g.gameStatus === 2 ? "bg-red-500 animate-ping" : "bg-emerald-400"}`} />
                  <span>{g.homeTeam.tricode} {g.homeTeam.score} - {g.awayTeam.tricode} {g.awayTeam.score}</span>
                  <span className="text-[10px] text-gray-400 font-normal">({g.gameStatusText.split(" ")[0]})</span>
                </button>
              );
            })}
          </div>

          {/* Live Status Pill */}
          <div className="flex items-center gap-2 text-xs font-mono">
            <div className="flex items-center gap-1.5 bg-red-950/40 text-red-400 border border-red-800/50 px-2.5 py-0.5 rounded-full">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <span className="font-bold tracking-wider">LIVE SYNC ACTIVE</span>
            </div>
            <span className="text-gray-400 hidden lg:inline">Low-latency play-by-play stream</span>
          </div>
        </div>
      </section>

      {/* 2. MARQUEE GAME BANNER & DIGITAL SCOREBOARD */}
      <section className="max-w-7xl mx-auto w-full px-4 pt-6">
        <div className="bg-gradient-to-r from-surfaceCard via-surface to-surfaceCard border border-borderDark rounded-2xl p-5 md:p-6 shadow-2xl relative overflow-hidden">
          {/* Subtle Court Line Graphic in Background */}
          <div className="absolute inset-0 opacity-5 pointer-events-none bg-[radial-gradient(#3b82f6_1px,transparent_1px)] [background-size:16px_16px]" />

          <div className="relative z-10 grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
            {/* Away Team Card */}
            <div className="md:col-span-4 flex items-center gap-4">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center font-black text-2xl text-white shadow-lg border border-white/10"
                style={{ backgroundColor: awayTeam.color }}
              >
                {awayTeam.tricode}
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-mono text-gray-400 uppercase tracking-widest">{awayTeam.city}</span>
                <h2 className="text-xl md:text-2xl font-black text-white">{awayTeam.name}</h2>
                <span className="text-xs text-gray-400 font-mono">48-34 • 2nd Seed East</span>
              </div>
              <div className="ml-auto text-right">
                <span className="text-4xl md:text-5xl font-black text-white tracking-tight">{currentAwayScore}</span>
                <div className="text-[10px] text-gray-400 font-mono mt-0.5">Bonus: IN</div>
              </div>
            </div>

            {/* Center: Live Game Clock, Period, and Possession Indicator */}
            <div className="md:col-span-4 flex flex-col items-center justify-center text-center px-2 py-3 bg-surface/80 rounded-xl border border-borderDark/80">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-bold text-accent tracking-wider font-mono bg-accent/10 px-2 py-0.5 rounded border border-accent/20">
                  {currentMinute >= 48 ? "FINAL" : `Q${Math.min(4, Math.floor((currentMinute - 1) / 12) + 1)} MIN ${currentMinute}`}
                </span>
                <span className="text-xs text-gray-400 font-mono">• {gameFeed.arena}</span>
              </div>

              {/* Game Clock Display */}
              <div className="text-2xl md:text-3xl font-black font-mono tracking-wider text-white">
                {latestPlay?.clock ? latestPlay.clock.replace("PT", "").replace(".00S", "").replace("M", ":") : "00:00"}
              </div>

              {/* Possession Arrow Indicator */}
              <div className="flex items-center gap-2 mt-1.5 text-xs font-mono">
                <span className="text-gray-400">Possession:</span>
                <span className="flex items-center gap-1 font-bold text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded border border-amber-400/30 animate-pulse">
                  🏀 {latestPlay?.teamTricode || homeTeam.tricode}
                </span>
              </div>

              {/* Live Margin & Win Probability Badges */}
              <div className="flex items-center gap-2 mt-2 font-mono text-xs">
                <span
                  className={`px-2 py-0.5 rounded font-bold ${
                    currentMargin > 0
                      ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                      : currentMargin < 0
                      ? "bg-red-950 text-red-300 border border-red-800"
                      : "bg-surfaceCard text-gray-300 border border-borderDark"
                  }`}
                >
                  {currentMargin > 0 ? `+${currentMargin} ${homeTeam.tricode}` : currentMargin < 0 ? `+${Math.abs(currentMargin)} ${awayTeam.tricode}` : "TIED"}
                </span>

                <span className="bg-cyan-950 text-cyan-300 border border-cyan-800 px-2 py-0.5 rounded font-bold">
                  {(currentWinProb * 100).toFixed(1)}% {homeTeam.tricode} WP
                </span>
              </div>
            </div>

            {/* Home Team Card */}
            <div className="md:col-span-4 flex items-center justify-end gap-4">
              <div className="mr-auto text-left md:order-1">
                <span className="text-4xl md:text-5xl font-black text-white tracking-tight">{currentHomeScore}</span>
                <div className="text-[10px] text-gray-400 font-mono mt-0.5">Bonus: IN</div>
              </div>
              <div className="flex flex-col text-right md:order-2">
                <span className="text-xs font-mono text-gray-400 uppercase tracking-widest">{homeTeam.city}</span>
                <h2 className="text-xl md:text-2xl font-black text-white">{homeTeam.name}</h2>
                <span className="text-xs text-gray-400 font-mono">47-35 • 6th Seed East</span>
              </div>
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center font-black text-2xl text-white shadow-lg border border-white/10 md:order-3"
                style={{ backgroundColor: homeTeam.color }}
              >
                {homeTeam.tricode}
              </div>
            </div>
          </div>

          {/* Quarter by Quarter Linescore Mini-Table */}
          <div className="mt-5 pt-4 border-t border-borderDark/60 flex flex-wrap items-center justify-between text-xs font-mono gap-4">
            <div className="flex items-center gap-6">
              <span className="text-gray-400 font-bold">Linescore:</span>
              <div className="flex items-center gap-4">
                <span className="text-gray-400">{awayTeam.tricode}: 26 | 27 | 34 | 29 = <strong className="text-white">116</strong></span>
                <span className="text-gray-500">vs</span>
                <span className="text-gray-400">{homeTeam.tricode}: 36 | 34 | 18 | 33 = <strong className="text-white">121</strong></span>
              </div>
            </div>
            <div className="flex items-center gap-4 text-[11px] text-gray-400">
              <span>Lead Changes: <strong className="text-white">10</strong></span>
              <span>Times Tied: <strong className="text-white">4</strong></span>
              <span>Biggest Lead: <strong className="text-white">IND +18</strong></span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. INTERACTIVE REPLAY & SIMULATION DECK */}
      <section className="max-w-7xl mx-auto w-full px-4 pt-4">
        <div className="bg-surfaceCard border border-borderDark rounded-xl p-3 md:p-4 shadow-card flex flex-col md:flex-row items-center justify-between gap-4">
          {/* Controls: Play/Pause & Step Buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className={`px-4 py-2 rounded-lg font-bold text-xs flex items-center gap-2 transition ${
                isPlaying
                  ? "bg-amber-500 text-black shadow-lg shadow-amber-500/20"
                  : "bg-accent hover:bg-accentHover text-white shadow-lg shadow-accent/20"
              }`}
            >
              <span>{isPlaying ? "⏸ PAUSE" : "▶ PLAY REPLAY"}</span>
            </button>

            {/* Rewind to Start */}
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

            {/* Jump to Clutch */}
            <button
              onClick={jumpToClutch}
              className="px-3 py-1.5 bg-gradient-to-r from-amber-500/20 to-orange-500/20 hover:from-amber-500/30 hover:to-orange-500/30 border border-amber-500/40 text-amber-300 rounded-lg text-xs font-bold transition flex items-center gap-1.5"
            >
              ⚡ Jump to Clutch (Q4 Dagger)
            </button>
          </div>

          {/* Timeline Scrubber Slider */}
          <div className="flex-1 max-w-xl w-full flex items-center gap-3">
            <span className="text-xs font-mono text-gray-400 whitespace-nowrap">Q1 12:00</span>
            <input
              type="range"
              min="1"
              max="48"
              value={currentMinute}
              onChange={(e) => {
                setCurrentMinute(parseInt(e.target.value));
              }}
              className="w-full h-2 bg-surface rounded-lg appearance-none cursor-pointer accent-accent"
            />
            <span className="text-xs font-mono text-gray-400 whitespace-nowrap">Q4 00:00</span>
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
      </section>

      {/* 5. SPLIT VIEW: ON-COURT 10-PLAYER LINEUP CARDS & LIVE QUANT PLAY-BY-PLAY */}
      <section className="max-w-7xl mx-auto w-full px-4 pt-4 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: ACTIVE 10 PLAYERS ON THE FLOOR & STATS (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          {/* Active Lineup Summary Card */}
          <div className="bg-surfaceCard border border-borderDark rounded-xl p-4 shadow-card">
            <div className="flex items-center justify-between border-b border-borderDark/60 pb-2 mb-3">
              <h3 className="text-sm font-extrabold text-white flex items-center gap-2">
                <span>🛡️</span> ACTIVE 10-PLAYER FLOOR LINEUPS
              </h3>
              <span className="text-[11px] font-mono text-gray-400">At Minute {currentMinute}</span>
            </div>

            {/* Home 5-Man On Court */}
            <div className="mb-4">
              <div className="flex items-center justify-between text-xs font-bold text-gray-300 mb-2">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: homeTeam.color }} />
                  {homeTeam.name} On Floor ({homeTeam.tricode})
                </span>
                <span className="font-mono text-emerald-400">Lead: +{Math.max(0, currentMargin)}</span>
              </div>

              <div className="space-y-1.5">
                {currentHomeLineup.map((p) => (
                  <div
                    key={`home-lineup-${p.personId}`}
                    className="flex items-center justify-between bg-surface/70 border border-borderDark/50 rounded-lg px-3 py-1.5 text-xs font-mono"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-gray-400 font-bold w-5">{p.jerseyNum}</span>
                      <span className="text-white font-medium">{p.name}</span>
                      <span className="text-[10px] text-gray-400">({p.position})</span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px]">
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
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: awayTeam.color }} />
                  {awayTeam.name} On Floor ({awayTeam.tricode})
                </span>
                <span className="font-mono text-red-400">Deficit: -{Math.max(0, currentMargin)}</span>
              </div>

              <div className="space-y-1.5">
                {currentAwayLineup.map((p) => (
                  <div
                    key={`away-lineup-${p.personId}`}
                    className="flex items-center justify-between bg-surface/70 border border-borderDark/50 rounded-lg px-3 py-1.5 text-xs font-mono"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-gray-400 font-bold w-5">{p.jerseyNum}</span>
                      <span className="text-white font-medium">{p.name}</span>
                      <span className="text-[10px] text-gray-400">({p.position})</span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px]">
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
          </div>

          {/* Leading Scorers Head-to-Head */}
          <div className="bg-surfaceCard border border-borderDark rounded-xl p-4 shadow-card">
            <h3 className="text-xs font-extrabold text-white uppercase tracking-wider font-mono mb-3">
              Top Impact Players of the Game
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {/* Home Leader (Myles Turner 27 pts or Tyrese Haliburton) */}
              <div className="p-3 bg-surface rounded-lg border border-borderDark text-xs font-mono">
                <span className="text-[10px] text-accent font-bold">IND LEADER</span>
                <div className="font-bold text-white text-sm mt-0.5">Myles Turner</div>
                <div className="text-gray-400 text-[11px] mt-1">27 PTS • 9 REB • 2 BLK</div>
                <div className="text-emerald-400 font-bold mt-0.5">+11.0 +/- (9-14 FG)</div>
              </div>

              {/* Away Leader (Donovan Mitchell 38 pts) */}
              <div className="p-3 bg-surface rounded-lg border border-borderDark text-xs font-mono">
                <span className="text-[10px] text-red-400 font-bold">CLE LEADER</span>
                <div className="font-bold text-white text-sm mt-0.5">Donovan Mitchell</div>
                <div className="text-gray-400 text-[11px] mt-1">38 PTS • 5 REB • 9 AST</div>
                <div className="text-gray-300 font-bold mt-0.5">4-7 3PT • 13-21 FG</div>
              </div>
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
                const isThree = ev.actionType === "3pt";

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
                          Q{ev.period} {ev.clock.replace("PT", "").replace(".00S", "")}
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
                          {ev.scoreHome} - {ev.scoreAway}
                        </span>
                      </div>

                      {/* Right Badges: WPA & xeFG% */}
                      <div className="flex items-center gap-1.5">
                        {/* WPA Badge */}
                        {ev.wpa !== undefined && ev.wpa !== 0 && (
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              ev.wpa > 0
                                ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                                : "bg-red-950 text-red-300 border border-red-800"
                            }`}
                            title="Win Probability Added by this Play"
                          >
                            {ev.wpa > 0 ? `+${(ev.wpa * 100).toFixed(1)}%` : `${(ev.wpa * 100).toFixed(1)}%`} WPA
                          </span>
                        )}

                        {/* xeFG% Badge */}
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
                      <p className="text-gray-100 font-sans text-xs">
                        {ev.description}
                      </p>
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
