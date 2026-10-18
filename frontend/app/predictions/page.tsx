"use client";

import React, { useEffect, useState, useMemo } from "react";
import {
  DataService,
  Team,
  WinProbResult,
  HistoricalGame,
  SEASONS_10YR,
} from "@/lib/data-service";
import { resolveMatchupTeamColors } from "@/components/differential-candlestick-chart";

export default function PredictionsPage() {
  const [homeSeason, setHomeSeason] = useState<string>("2023-24");
  const [awaySeason, setAwaySeason] = useState<string>("2023-24");
  const [homeTeams, setHomeTeams] = useState<Team[]>([]);
  const [awayTeams, setAwayTeams] = useState<Team[]>([]);
  const [homeTeamId, setHomeTeamId] = useState<number>(1610612738); // BOS
  const [awayTeamId, setAwayTeamId] = useState<number>(1610612743); // DEN

  // Live Simulator state
  const [scoreMargin, setScoreMargin] = useState<number>(4);
  const [period, setPeriod] = useState<number>(4);
  const [clockSeconds, setClockSeconds] = useState<number>(180);
  const [possessionHome, setPossessionHome] = useState<number>(1);
  const [winProb, setWinProb] = useState<WinProbResult | null>(null);

  // 10-Season Historical Games Archive state
  const [archiveSeason, setArchiveSeason] = useState<string>("2024-25");
  const [archiveTeam, setArchiveTeam] = useState<string>("ALL");
  const [archiveType, setArchiveType] = useState<string>("ALL");
  const [archiveSearch, setArchiveSearch] = useState<string>("");
  const [historicalGames, setHistoricalGames] = useState<HistoricalGame[]>([]);

  useEffect(() => {
    DataService.getTeams(homeSeason).then(setHomeTeams);
  }, [homeSeason]);

  useEffect(() => {
    DataService.getTeams(awaySeason).then(setAwayTeams);
  }, [awaySeason]);

  useEffect(() => {
    DataService.getHistoricalGames(archiveSeason, archiveTeam, archiveSearch).then(
      (games) => {
        if (archiveType !== "ALL") {
          setHistoricalGames(games.filter((g) => g.type === archiveType));
        } else {
          setHistoricalGames(games);
        }
      }
    );
  }, [archiveSeason, archiveTeam, archiveType, archiveSearch]);

  useEffect(() => {
    let totalSec = clockSeconds;
    if (period === 1) totalSec += 2160;
    else if (period === 2) totalSec += 1440;
    else if (period === 3) totalSec += 720;

    const res = DataService.calculateWinProbability(
      scoreMargin,
      totalSec,
      period,
      possessionHome
    );
    setWinProb(res);
  }, [scoreMargin, period, clockSeconds, possessionHome]);

  const homeTeam = homeTeams.find((t) => t.team_id === homeTeamId) || homeTeams[0];
  const awayTeam = awayTeams.find((t) => t.team_id === awayTeamId) || awayTeams[1];

  const { homeColor, awayColor } = useMemo(
    () =>
      resolveMatchupTeamColors(
        homeTeam?.abbreviation || "BOS",
        awayTeam?.abbreviation || "DEN"
      ),
    [homeTeam, awayTeam]
  );

  // Head to head matchup projection calculation
  const matchup = useMemo(() => {
    if (!homeTeam || !awayTeam) return null;
    const estPace = (homeTeam.pace + awayTeam.pace) / 2.0;

    const homeExpOff = (homeTeam.off_rating + awayTeam.def_rating) / 2.0 + 1.35;
    const awayExpOff = (awayTeam.off_rating + homeTeam.def_rating) / 2.0 - 1.35;

    const homeExpPts = Math.round((homeExpOff * estPace) / 100.0);
    const awayExpPts = Math.round((awayExpOff * estPace) / 100.0);

    const projectedMargin = homeExpPts - awayExpPts;
    const homeWinProb = Math.min(0.94, Math.max(0.06, 0.5 + projectedMargin * 0.036));

    return {
      homeExpPts,
      awayExpPts,
      projectedMargin,
      homeWinProb: Number((homeWinProb * 100).toFixed(1)),
      awayWinProb: Number(((1.0 - homeWinProb) * 100).toFixed(1)),
      estPace: Number(estPace.toFixed(1)),
    };
  }, [homeTeam, awayTeam]);

  return (
    <div className="space-y-8">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-2">
            <span>🔮</span> Cross-Era Matchup Predictor &amp; 12,729-Game Historical Archive
          </h1>
          <p className="text-sm text-gray-400 mt-1 font-mono">
            Simulate head-to-head matchups across any of the last 10 seasons (2015-16 to 2024-25) and explore all 12,729 historical games.
          </p>
        </div>

        {/* Cross-Era Preset Buttons */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <button
            onClick={() => {
              setHomeSeason("2023-24");
              setHomeTeamId(1610612738); // BOS
              setAwaySeason("2015-16");
              setAwayTeamId(1610612744); // GSW 73-9
            }}
            className="px-3 py-1.5 rounded-lg bg-surfaceCard hover:bg-surface border border-borderDark text-gray-200 hover:text-white transition"
          >
            &apos;24 BOS vs &apos;16 GSW (73-9)
          </button>
          <button
            onClick={() => {
              setHomeSeason("2022-23");
              setHomeTeamId(1610612743); // DEN
              setAwaySeason("2019-20");
              setAwayTeamId(1610612747); // LAL
            }}
            className="px-3 py-1.5 rounded-lg bg-surfaceCard hover:bg-surface border border-borderDark text-gray-200 hover:text-white transition"
          >
            &apos;23 DEN vs &apos;20 LAL
          </button>
        </div>
      </div>

      {/* Part 1: Multi-Season Head-to-Head Matchup Simulator */}
      <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-6">
        <div className="flex items-center justify-between border-b border-borderDark pb-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <span>⚔️</span> Multi-Season Head-to-Head Projection (2015-16 to 2024-25)
          </h2>
          <span className="text-xs font-mono text-gray-400">
            Team-Colored Efficiency &amp; Pace Simulation
          </span>
        </div>

        {/* Team & Season Selectors */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
          {/* Home Team */}
          <div
            className="p-4 rounded-xl bg-surface border space-y-3"
            style={{ borderColor: `${homeColor}60` }}
          >
            <div className="flex items-center justify-between">
              <span
                className="text-xs uppercase font-mono font-extrabold"
                style={{ color: homeColor }}
              >
                🏠 Home Franchise
              </span>
              <select
                value={homeSeason}
                onChange={(e) => setHomeSeason(e.target.value)}
                className="bg-surfaceCard border border-borderDark rounded-lg px-2.5 py-1 text-xs font-mono font-bold text-white"
              >
                {SEASONS_10YR.map((s) => (
                  <option key={s} value={s}>
                    {s} Season
                  </option>
                ))}
              </select>
            </div>
            <select
              value={homeTeamId}
              onChange={(e) => setHomeTeamId(Number(e.target.value))}
              className="w-full bg-surfaceCard border border-borderDark rounded-xl p-2.5 text-sm font-bold text-white focus:outline-none focus:border-accent font-mono"
            >
              {homeTeams.map((t) => (
                <option key={t.team_id} value={t.team_id}>
                  {homeSeason} {t.full_name} ({t.wins}-{t.losses})
                </option>
              ))}
            </select>
            {homeTeam && (
              <div className="grid grid-cols-4 gap-2 text-center text-xs font-mono pt-1">
                <div>
                  <span className="text-gray-500 block text-[10px]">Record</span>
                  <span className="font-bold text-white">
                    {homeTeam.wins}-{homeTeam.losses}
                  </span>
                </div>
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
                  <span className="text-gray-500 block text-[10px]">DRtg</span>
                  <span className="font-bold text-white">{homeTeam.def_rating}</span>
                </div>
              </div>
            )}
          </div>

          {/* Away Team */}
          <div
            className="p-4 rounded-xl bg-surface border space-y-3"
            style={{ borderColor: `${awayColor}60` }}
          >
            <div className="flex items-center justify-between">
              <span
                className="text-xs uppercase font-mono font-extrabold"
                style={{ color: awayColor }}
              >
                ✈️ Away Franchise
              </span>
              <select
                value={awaySeason}
                onChange={(e) => setAwaySeason(e.target.value)}
                className="bg-surfaceCard border border-borderDark rounded-lg px-2.5 py-1 text-xs font-mono font-bold text-white"
              >
                {SEASONS_10YR.map((s) => (
                  <option key={s} value={s}>
                    {s} Season
                  </option>
                ))}
              </select>
            </div>
            <select
              value={awayTeamId}
              onChange={(e) => setAwayTeamId(Number(e.target.value))}
              className="w-full bg-surfaceCard border border-borderDark rounded-xl p-2.5 text-sm font-bold text-white focus:outline-none focus:border-accent font-mono"
            >
              {awayTeams.map((t) => (
                <option key={t.team_id} value={t.team_id}>
                  {awaySeason} {t.full_name} ({t.wins}-{t.losses})
                </option>
              ))}
            </select>
            {awayTeam && (
              <div className="grid grid-cols-4 gap-2 text-center text-xs font-mono pt-1">
                <div>
                  <span className="text-gray-500 block text-[10px]">Record</span>
                  <span className="font-bold text-white">
                    {awayTeam.wins}-{awayTeam.losses}
                  </span>
                </div>
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
                  <span className="text-gray-500 block text-[10px]">DRtg</span>
                  <span className="font-bold text-white">{awayTeam.def_rating}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Projected Outcome Card in Team Colors */}
        {matchup && (
          <div className="p-6 rounded-2xl bg-gradient-to-r from-surface to-surfaceCard border border-borderDark text-center space-y-4">
            <div className="flex items-center justify-center gap-8">
              <div className="text-right">
                <span className="text-xs font-mono text-gray-400 block">
                  {homeSeason} {homeTeam?.abbreviation}
                </span>
                <span
                  className="text-4xl font-extrabold font-mono"
                  style={{ color: homeColor }}
                >
                  {matchup.homeExpPts}
                </span>
              </div>
              <span className="text-xl font-bold text-gray-500">&mdash;</span>
              <div className="text-left">
                <span className="text-xs font-mono text-gray-400 block">
                  {awaySeason} {awayTeam?.abbreviation}
                </span>
                <span
                  className="text-4xl font-extrabold font-mono"
                  style={{ color: awayColor }}
                >
                  {matchup.awayExpPts}
                </span>
              </div>
            </div>

            {/* Win Probability Bar in Team Colors */}
            <div className="max-w-lg mx-auto space-y-1.5">
              <div className="flex items-center justify-between text-xs font-mono font-extrabold">
                <span style={{ color: homeColor }}>
                  {homeSeason} {homeTeam?.abbreviation} Win Prob: {matchup.homeWinProb}%
                </span>
                <span style={{ color: awayColor }}>
                  {awaySeason} {awayTeam?.abbreviation} Win Prob: {matchup.awayWinProb}%
                </span>
              </div>
              <div className="w-full h-3.5 rounded-full bg-surface border border-borderDark overflow-hidden flex">
                <div
                  className="h-full transition-all duration-300"
                  style={{ width: `${matchup.homeWinProb}%`, backgroundColor: homeColor }}
                />
                <div
                  className="h-full transition-all duration-300"
                  style={{ width: `${matchup.awayWinProb}%`, backgroundColor: awayColor }}
                />
              </div>
              <p className="text-[11px] text-gray-400 font-mono mt-1">
                Projected Pace: {matchup.estPace} possessions &middot;{" "}
                {matchup.projectedMargin >= 0 ? homeTeam?.abbreviation : awayTeam?.abbreviation}{" "}
                favored by {Math.abs(matchup.projectedMargin)} pts
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
          <div className="lg:col-span-2 space-y-5">
            <div className="bg-surface p-4 rounded-xl border border-borderDark">
              <div className="flex items-center justify-between text-xs font-mono mb-2">
                <span className="text-gray-300 font-bold">Score Margin (Home - Away):</span>
                <span
                  className="text-base font-bold"
                  style={{
                    color:
                      scoreMargin > 0
                        ? homeColor
                        : scoreMargin < 0
                        ? awayColor
                        : "#94a3b8",
                  }}
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
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-surface p-4 rounded-xl border border-borderDark">
                <label className="block text-xs font-mono text-gray-300 font-bold mb-2">
                  Period
                </label>
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
              </div>
            </div>

            <div className="bg-surface p-4 rounded-xl border border-borderDark flex items-center justify-between">
              <span className="text-xs font-mono text-gray-300 font-bold">
                Has Possession of Ball:
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPossessionHome(1)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition ${
                    possessionHome === 1
                      ? "bg-accent text-white"
                      : "bg-surfaceCard text-gray-400 hover:text-white"
                  }`}
                >
                  {homeTeam?.abbreviation || "Home"} Ball (+1.1 pts)
                </button>
                <button
                  onClick={() => setPossessionHome(0)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition ${
                    possessionHome === 0
                      ? "bg-cyan-400 text-black"
                      : "bg-surfaceCard text-gray-400 hover:text-white"
                  }`}
                >
                  {awayTeam?.abbreviation || "Away"} Ball (-1.1 pts)
                </button>
              </div>
            </div>
          </div>

          <div className="bg-surface p-6 rounded-xl border border-borderDark flex flex-col justify-between text-center space-y-4">
            <div>
              <span className="text-xs font-mono uppercase text-gray-400">
                Calculated Win Probability
              </span>
              <div
                className="text-5xl font-extrabold font-mono mt-2"
                style={{ color: homeColor }}
              >
                {winProb ? `${(winProb.home_win_prob * 100).toFixed(1)}%` : "50.0%"}
              </div>
              <span className="text-xs text-gray-400 font-mono mt-1 block">
                {homeTeam?.abbreviation || "Home"} Victory Probability
              </span>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="w-full h-4 rounded-full bg-surfaceCard border border-borderDark overflow-hidden flex">
                <div
                  className="h-full transition-all duration-150"
                  style={{
                    width: `${(winProb?.home_win_prob ?? 0.5) * 100}%`,
                    backgroundColor: homeColor,
                  }}
                />
                <div
                  className="h-full transition-all duration-150"
                  style={{
                    width: `${(winProb?.away_win_prob ?? 0.5) * 100}%`,
                    backgroundColor: awayColor,
                  }}
                />
              </div>
              <div className="flex justify-between font-bold">
                <span style={{ color: homeColor }}>
                  {homeTeam?.abbreviation || "Home"}:{" "}
                  {((winProb?.home_win_prob ?? 0.5) * 100).toFixed(1)}%
                </span>
                <span style={{ color: awayColor }}>
                  {awayTeam?.abbreviation || "Away"}:{" "}
                  {((winProb?.away_win_prob ?? 0.5) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Part 3: Complete 10-Season Historical Games Archive (12,729 Games) */}
      <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-borderDark pb-4">
          <div>
            <h2 className="text-lg font-extrabold text-white flex items-center gap-2">
              <span>📚</span> Complete 10-Season NBA Game Results Archive (12,729 Games)
            </h2>
            <p className="text-xs text-gray-400 font-mono mt-0.5">
              Every Regular Season &amp; Playoff game from 2015-16 through 2024-25. Filter by season, franchise, or date.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 text-xs font-mono">
            <input
              type="text"
              placeholder="Search date or matchup..."
              value={archiveSearch}
              onChange={(e) => setArchiveSearch(e.target.value)}
              className="bg-surface border border-borderDark rounded-xl px-3 py-1.5 text-white placeholder-gray-500 focus:outline-none focus:border-accent w-44"
            />
            <select
              value={archiveSeason}
              onChange={(e) => setArchiveSeason(e.target.value)}
              className="bg-surface border border-accent/50 rounded-xl px-3 py-1.5 font-bold text-white"
            >
              {SEASONS_10YR.map((s) => (
                <option key={s} value={s}>
                  {s} Season
                </option>
              ))}
              <option value="ALL">All 10 Seasons (12,729 Games)</option>
            </select>
            <select
              value={archiveTeam}
              onChange={(e) => setArchiveTeam(e.target.value)}
              className="bg-surface border border-borderDark rounded-xl px-3 py-1.5 text-white"
            >
              <option value="ALL">All 30 Teams</option>
              {homeTeams.map((t) => (
                <option key={t.abbreviation} value={t.abbreviation}>
                  {t.abbreviation} - {t.full_name}
                </option>
              ))}
            </select>
            <select
              value={archiveType}
              onChange={(e) => setArchiveType(e.target.value)}
              className="bg-surface border border-borderDark rounded-xl px-3 py-1.5 text-white"
            >
              <option value="ALL">Reg Season + Playoffs</option>
              <option value="Regular Season">Regular Season</option>
              <option value="Playoffs">Playoffs</option>
            </select>
          </div>
        </div>

        <div className="flex items-center justify-between text-xs font-mono text-gray-400">
          <span>
            Matching Games: <strong className="text-white">{historicalGames.length.toLocaleString()}</strong>
          </span>
          <span>Showing top 150 matching results</span>
        </div>

        <div className="overflow-x-auto max-h-[460px] overflow-y-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-surface text-gray-400 uppercase border-b border-borderDark sticky top-0">
              <tr>
                <th className="py-2.5 px-3">Date</th>
                <th className="py-2.5 px-3">Season</th>
                <th className="py-2.5 px-3">Stage</th>
                <th className="py-2.5 px-3">Away Team</th>
                <th className="py-2.5 px-3 text-center">Final Score</th>
                <th className="py-2.5 px-3">Home Team</th>
                <th className="py-2.5 px-3 text-right">Differential</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-borderDark/40">
              {historicalGames.slice(0, 150).map((g) => {
                const homeWon = g.h_pts >= g.a_pts;
                return (
                  <tr key={g.id} className="hover:bg-surface/60 transition">
                    <td className="py-2.5 px-3 text-gray-300">{g.date}</td>
                    <td className="py-2.5 px-3 text-gray-400">{g.season}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          g.type === "Playoffs"
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                            : "bg-surface border border-borderDark text-gray-400"
                        }`}
                      >
                        {g.type}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={!homeWon ? "font-extrabold text-white" : "text-gray-400"}>
                        {g.away} ({g.a_pts})
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-center font-bold text-white">
                      {g.a_pts} - {g.h_pts}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={homeWon ? "font-extrabold text-white" : "text-gray-400"}>
                        {g.home} ({g.h_pts})
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold">
                      <span className={homeWon ? "text-emerald-400" : "text-cyan-400"}>
                        {homeWon ? `${g.home} +${g.margin}` : `${g.away} +${Math.abs(g.margin)}`}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
