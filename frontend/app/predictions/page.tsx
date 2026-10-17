"use client";

import React, { useEffect, useState } from "react";
import { DataService, Team, WinProbResult } from "@/lib/data-service";

export default function PredictionsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [homeTeamId, setHomeTeamId] = useState<number>(1610612738); // BOS
  const [awayTeamId, setAwayTeamId] = useState<number>(1610612743); // DEN

  // Live Simulator state
  const [scoreMargin, setScoreMargin] = useState<number>(4);
  const [period, setPeriod] = useState<number>(4);
  const [clockSeconds, setClockSeconds] = useState<number>(180); // 3:00 remaining
  const [possessionHome, setPossessionHome] = useState<number>(1);
  const [winProb, setWinProb] = useState<WinProbResult | null>(null);

  // Marquee timeline
  const [timeline, setTimeline] = useState<any[]>([]);

  useEffect(() => {
    DataService.getTeams().then(setTeams);
    const marquee = DataService.getMarqueeTimeline();
    if (marquee && marquee.timeline) {
      setTimeline(marquee.timeline);
    }
  }, []);

  // Update live simulation on slider changes
  useEffect(() => {
    // Total seconds remaining calculation
    let totalSec = clockSeconds;
    if (period === 1) totalSec += 2160;
    else if (period === 2) totalSec += 1440;
    else if (period === 3) totalSec += 720;

    const res = DataService.calculateWinProbability(scoreMargin, totalSec, period, possessionHome);
    setWinProb(res);
  }, [scoreMargin, period, clockSeconds, possessionHome]);

  const homeTeam = teams.find((t) => t.team_id === homeTeamId) || teams[0];
  const awayTeam = teams.find((t) => t.team_id === awayTeamId) || teams[1];

  // Head to head matchup projection calculation
  const calcMatchup = () => {
    if (!homeTeam || !awayTeam) return null;
    const hca = 2.5; // Home court advantage
    const estPace = (homeTeam.pace + awayTeam.pace) / 2.0;

    // Expected efficiency
    const homeExpOff = (homeTeam.off_rating + awayTeam.def_rating) / 2.0 + 1.25;
    const awayExpOff = (awayTeam.off_rating + homeTeam.def_rating) / 2.0 - 1.25;

    const homeExpPts = Math.round((homeExpOff * estPace) / 100.0);
    const awayExpPts = Math.round((awayExpOff * estPace) / 100.0);

    const projectedMargin = homeExpPts - awayExpPts;
    const homeWinProb = Math.min(0.92, Math.max(0.08, 0.50 + projectedMargin * 0.038));

    return {
      homeExpPts,
      awayExpPts,
      projectedMargin,
      homeWinProb: Number((homeWinProb * 100).toFixed(1)),
      awayWinProb: Number(((1.0 - homeWinProb) * 100).toFixed(1)),
      estPace: Number(estPace.toFixed(1)),
    };
  };

  const matchup = calcMatchup();

  return (
    <div className="space-y-8">
      {/* Title Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-white flex items-center gap-2">
          <span>🔮</span> Game Outcome Predictor &amp; Win Probability Studio
        </h1>
        <p className="text-sm text-gray-400 mt-1 font-mono">
          Head-to-head match-up simulator calibrated via Net Ratings and continuous Brownian motion volatility models.
        </p>
      </div>

      {/* Part 1: Head-to-Head Matchup Simulator */}
      <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-6">
        <div className="flex items-center justify-between border-b border-borderDark pb-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <span>⚔️</span> Head-to-Head Game Projection
          </h2>
          <span className="text-xs font-mono text-gray-400">Regular Season Simulation</span>
        </div>

        {/* Team Selectors */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
          {/* Home Team */}
          <div className="p-4 rounded-xl bg-surface border border-borderDark space-y-3">
            <span className="text-xs uppercase font-mono text-accent font-bold">🏠 Home Franchise</span>
            <select
              value={homeTeamId}
              onChange={(e) => setHomeTeamId(Number(e.target.value))}
              className="w-full bg-surfaceCard border border-borderDark rounded-xl p-2.5 text-sm font-bold text-white focus:outline-none focus:border-accent font-mono"
            >
              {teams.map((t) => (
                <option key={t.team_id} value={t.team_id}>
                  {t.full_name} ({t.wins}-{t.losses})
                </option>
              ))}
            </select>
            {homeTeam && (
              <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono pt-1">
                <div>
                  <span className="text-gray-500 block text-[10px]">Net Rtg</span>
                  <span className="font-bold text-white">
                    {homeTeam.net_rating > 0 ? `+${homeTeam.net_rating}` : homeTeam.net_rating}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[10px]">ORtg</span>
                  <span className="font-bold text-white">{homeTeam.off_rating}</span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[10px]">Pace</span>
                  <span className="font-bold text-white">{homeTeam.pace}</span>
                </div>
              </div>
            )}
          </div>

          {/* Away Team */}
          <div className="p-4 rounded-xl bg-surface border border-borderDark space-y-3">
            <span className="text-xs uppercase font-mono text-cyan-400 font-bold">✈️ Away Franchise</span>
            <select
              value={awayTeamId}
              onChange={(e) => setAwayTeamId(Number(e.target.value))}
              className="w-full bg-surfaceCard border border-borderDark rounded-xl p-2.5 text-sm font-bold text-white focus:outline-none focus:border-accent font-mono"
            >
              {teams.map((t) => (
                <option key={t.team_id} value={t.team_id}>
                  {t.full_name} ({t.wins}-{t.losses})
                </option>
              ))}
            </select>
            {awayTeam && (
              <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono pt-1">
                <div>
                  <span className="text-gray-500 block text-[10px]">Net Rtg</span>
                  <span className="font-bold text-white">
                    {awayTeam.net_rating > 0 ? `+${awayTeam.net_rating}` : awayTeam.net_rating}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[10px]">ORtg</span>
                  <span className="font-bold text-white">{awayTeam.off_rating}</span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[10px]">Pace</span>
                  <span className="font-bold text-white">{awayTeam.pace}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Projected Outcome Card */}
        {matchup && (
          <div className="p-6 rounded-2xl bg-gradient-to-r from-surface to-surfaceCard border border-borderDark text-center space-y-4">
            <div className="flex items-center justify-center gap-6">
              <div className="text-right">
                <span className="text-xs font-mono text-gray-400 block">{homeTeam?.abbreviation}</span>
                <span className="text-4xl font-extrabold font-mono text-accent">
                  {matchup.homeExpPts}
                </span>
              </div>
              <span className="text-xl font-bold text-gray-500">&mdash;</span>
              <div className="text-left">
                <span className="text-xs font-mono text-gray-400 block">{awayTeam?.abbreviation}</span>
                <span className="text-4xl font-extrabold font-mono text-cyan-400">
                  {matchup.awayExpPts}
                </span>
              </div>
            </div>

            {/* Win Probability Bar */}
            <div className="max-w-md mx-auto space-y-1.5">
              <div className="flex items-center justify-between text-xs font-mono font-bold">
                <span className="text-accent">{homeTeam?.abbreviation} {matchup.homeWinProb}%</span>
                <span className="text-cyan-400">{awayTeam?.abbreviation} {matchup.awayWinProb}%</span>
              </div>
              <div className="w-full h-3 rounded-full bg-surface border border-borderDark overflow-hidden flex">
                <div
                  className="bg-accent h-full transition-all duration-300"
                  style={{ width: `${matchup.homeWinProb}%` }}
                />
                <div
                  className="bg-cyan-400 h-full transition-all duration-300"
                  style={{ width: `${matchup.awayWinProb}%` }}
                />
              </div>
              <p className="text-[11px] text-gray-400 font-mono mt-1">
                Projected Pace: {matchup.estPace} possessions &middot; {homeTeam?.abbreviation} favored by {Math.abs(matchup.projectedMargin)} pts
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Part 2: Interactive Real-Time Win Probability Simulator */}
      <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-6">
        <div className="flex items-center justify-between border-b border-borderDark pb-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>🎛️</span> Live In-Game Win Probability Simulator
            </h2>
            <p className="text-xs text-gray-400 font-mono">
              Adjust score margin, game clock, and possession in real-time to observe dynamic probability decay.
            </p>
          </div>
          <span className="text-xs font-mono text-accent font-bold">
            &sigma;(t) = 12.5 &times; &radic;(t / 2880)
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Controls */}
          <div className="lg:col-span-2 space-y-5">
            {/* Score Margin Slider */}
            <div className="bg-surface p-4 rounded-xl border border-borderDark">
              <div className="flex items-center justify-between text-xs font-mono mb-2">
                <span className="text-gray-300 font-bold">Score Margin (Home - Away):</span>
                <span
                  className={`text-base font-bold ${
                    scoreMargin > 0
                      ? "text-emerald-400"
                      : scoreMargin < 0
                      ? "text-red-400"
                      : "text-gray-400"
                  }`}
                >
                  {scoreMargin > 0 ? `+${scoreMargin}` : scoreMargin} pts
                </span>
              </div>
              <input
                type="range"
                min="-25"
                max="25"
                step="1"
                value={scoreMargin}
                onChange={(e) => setScoreMargin(Number(e.target.value))}
                className="w-full accent-accent cursor-pointer"
              />
              <div className="flex justify-between text-[10px] font-mono text-gray-500 mt-1">
                <span>Away +25</span>
                <span>Tied (0)</span>
                <span>Home +25</span>
              </div>
            </div>

            {/* Period Selector & Clock Slider */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-surface p-4 rounded-xl border border-borderDark">
                <label className="block text-xs font-mono text-gray-300 font-bold mb-2">Period</label>
                <div className="grid grid-cols-4 gap-1.5 text-xs font-mono">
                  {[1, 2, 3, 4].map((q) => (
                    <button
                      key={q}
                      onClick={() => setPeriod(q)}
                      className={`py-2 rounded-lg font-bold transition ${
                        period === q
                          ? "bg-accent text-white"
                          : "bg-surfaceCard text-gray-400 hover:text-white"
                      }`}
                    >
                      Q{q}
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-surface p-4 rounded-xl border border-borderDark">
                <div className="flex items-center justify-between text-xs font-mono mb-2">
                  <span className="text-gray-300 font-bold">Clock in Period:</span>
                  <span className="text-accent font-bold">
                    {Math.floor(clockSeconds / 60)}:
                    {String(clockSeconds % 60).padStart(2, "0")}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="720"
                  step="10"
                  value={clockSeconds}
                  onChange={(e) => setClockSeconds(Number(e.target.value))}
                  className="w-full accent-accent cursor-pointer"
                />
                <div className="flex justify-between text-[10px] font-mono text-gray-500 mt-1">
                  <span>0:00 (End)</span>
                  <span>12:00 (Start)</span>
                </div>
              </div>
            </div>

            {/* Possession Toggle */}
            <div className="bg-surface p-4 rounded-xl border border-borderDark flex items-center justify-between">
              <span className="text-xs font-mono text-gray-300 font-bold">Has Possession of Ball:</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPossessionHome(1)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition ${
                    possessionHome === 1
                      ? "bg-accent text-white"
                      : "bg-surfaceCard text-gray-400 hover:text-white"
                  }`}
                >
                  Home Ball (+1.1 pts)
                </button>
                <button
                  onClick={() => setPossessionHome(0)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition ${
                    possessionHome === 0
                      ? "bg-cyan-400 text-black"
                      : "bg-surfaceCard text-gray-400 hover:text-white"
                  }`}
                >
                  Away Ball (-1.1 pts)
                </button>
              </div>
            </div>
          </div>

          {/* Probability Gauge Result */}
          <div className="bg-surface p-6 rounded-xl border border-borderDark flex flex-col justify-between text-center space-y-4">
            <div>
              <span className="text-xs font-mono uppercase text-gray-400">Calculated Win Probability</span>
              <div className="text-5xl font-extrabold font-mono text-emerald-400 mt-2">
                {winProb ? `${(winProb.home_win_prob * 100).toFixed(1)}%` : "50.0%"}
              </div>
              <span className="text-xs text-gray-400 font-mono mt-1 block">
                Home Team Victory Probability
              </span>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="w-full h-4 rounded-full bg-surfaceCard border border-borderDark overflow-hidden flex">
                <div
                  className="bg-emerald-500 h-full transition-all duration-150"
                  style={{ width: `${(winProb?.home_win_prob ?? 0.5) * 100}%` }}
                />
                <div
                  className="bg-red-500 h-full transition-all duration-150"
                  style={{ width: `${(winProb?.away_win_prob ?? 0.5) * 100}%` }}
                />
              </div>
              <div className="flex justify-between text-gray-400">
                <span>Home: {((winProb?.home_win_prob ?? 0.5) * 100).toFixed(1)}%</span>
                <span>Away: {((winProb?.away_win_prob ?? 0.5) * 100).toFixed(1)}%</span>
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-surfaceCard border border-borderDark text-[11px] font-mono text-gray-400">
              Standardized Margin Velocity:{" "}
              <strong className="text-white">
                {winProb
                  ? (
                      winProb.score_margin /
                      Math.sqrt((winProb.seconds_remaining || 1) + 1)
                    ).toFixed(2)
                  : "0.00"}
              </strong>
            </div>
          </div>
        </div>
      </div>

      {/* Part 3: Historical Clutch Game Replay */}
      {timeline.length > 0 && (
        <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-borderDark pb-3">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <span>📈</span> Real Game Win Probability Timeline
              </h2>
              <p className="text-xs text-gray-400 font-mono">
                Marquee Replay: Boston Celtics (118) vs Los Angeles Lakers (105)
              </p>
            </div>
            <span className="text-xs font-mono text-accent">Game 0022300061</span>
          </div>

          {/* Visual Step Chart */}
          <div className="h-44 w-full flex items-end gap-1 pt-4 pb-2">
            {timeline.map((point, idx) => {
              const hPct = point.home_win_prob * 100;
              return (
                <div
                  key={idx}
                  className="flex-1 flex flex-col items-center h-full justify-end group relative"
                >
                  <div
                    className="w-full bg-accent/70 hover:bg-accent rounded-t transition"
                    style={{ height: `${hPct}%` }}
                  />
                  {/* Tooltip */}
                  <div className="hidden group-hover:block absolute bottom-full mb-2 bg-surface border border-borderDark p-2 rounded-lg text-[10px] font-mono whitespace-nowrap z-20 shadow-xl">
                    <p className="text-white font-bold">Q{point.period} &middot; Margin: {point.score_margin > 0 ? `+${point.score_margin}` : point.score_margin}</p>
                    <p className="text-accent">BOS Win Prob: {hPct.toFixed(1)}%</p>
                    <p className="text-gray-400">{point.home_score} - {point.away_score}</p>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between text-xs font-mono text-gray-500 border-t border-borderDark pt-2">
            <span>Tip-off (Q1 12:00)</span>
            <span>Halftime (Q2 0:00)</span>
            <span>Clutch Time (Q4 5:00)</span>
            <span>Final Buzzer (0:00)</span>
          </div>
        </div>
      )}
    </div>
  );
}
