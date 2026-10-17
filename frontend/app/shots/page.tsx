"use client";

import React, { useEffect, useState } from "react";
import { CourtSVG } from "@/components/court-svg";
import { DataService, ShotResult } from "@/lib/data-service";

interface ShotItem {
  x: number;
  y: number;
  dist: number;
  made: number;
  is_3pt: number;
  p_hat: number;
}

interface ShotSummary {
  shots_analyzed: number;
  actual_efg_pct: number;
  x_efg_pct: number;
  smoe: number;
  expected_points_per_shot: number;
  actual_points_per_shot: number;
}

const PLAYERS = [
  { id: 2544, name: "LeBron James", team: "LAL" },
  { id: 201939, name: "Stephen Curry", team: "GSW" },
  { id: 203999, name: "Nikola Jokic", team: "DEN" },
  { id: 1629029, name: "Luka Doncic", team: "DAL" },
  { id: 1628369, name: "Jayson Tatum", team: "BOS" },
  { id: 203507, name: "Giannis Antetokounmpo", team: "MIL" },
  { id: 1628983, name: "Shai Gilgeous-Alexander", team: "OKC" },
  { id: 201142, name: "Kevin Durant", team: "PHX" },
  { id: 1630162, name: "Anthony Edwards", team: "MIN" },
];

export default function ShotsPage() {
  const [selectedPlayer, setSelectedPlayer] = useState(2544);
  const [shots, setShots] = useState<ShotItem[]>([]);
  const [summary, setSummary] = useState<ShotSummary | null>(null);
  const [activeTab, setActiveTab] = useState<"player" | "simulator">("player");
  const [clickedShot, setClickedShot] = useState<ShotResult | null>(null);

  // Load player shot chart
  useEffect(() => {
    const profile = DataService.getShotProfile(selectedPlayer);
    if (profile) {
      setShots(profile.shots || []);
      setSummary(profile.summary || null);
    }
  }, [selectedPlayer]);

  // Click on court to evaluate hypothetical shot
  const handleCourtClick = (x: number, y: number) => {
    const evalResult = DataService.evaluateShot(x, y, 1, 360.0);
    setClickedShot(evalResult);
  };

  const selectedPlayerObj = PLAYERS.find((p) => p.id === selectedPlayer);

  return (
    <div className="space-y-6">
      {/* Title & Diagnostic Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-2">
            <span>🎯</span> Spatial Shot Quality &amp; SMOE Engine
          </h1>
          <p className="text-sm text-gray-400 mt-1 font-mono">
            XGBoost Expected Effective Field Goal % (xeFG%) and Shot-Making Over Expected
          </p>
        </div>

        {/* View Mode Tabs & Player Selector */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex bg-surfaceCard rounded-xl p-0.5 border border-borderDark text-xs font-mono">
            <button
              onClick={() => setActiveTab("player")}
              className={`px-3 py-1.5 rounded-lg transition ${
                activeTab === "player" ? "bg-accent text-white font-bold" : "text-gray-400 hover:text-white"
              }`}
            >
              Player Charts
            </button>
            <button
              onClick={() => setActiveTab("simulator")}
              className={`px-3 py-1.5 rounded-lg transition ${
                activeTab === "simulator" ? "bg-accent text-white font-bold" : "text-gray-400 hover:text-white"
              }`}
            >
              Interactive Click Court
            </button>
          </div>

          {activeTab === "player" && (
            <select
              value={selectedPlayer}
              onChange={(e) => setSelectedPlayer(Number(e.target.value))}
              className="bg-surfaceCard border border-borderDark rounded-xl px-4 py-1.5 text-xs font-bold text-white focus:outline-none focus:border-accent"
            >
              {PLAYERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.team})
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Main Interactive Stage */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Interactive Court SVG Visualizer */}
        <div className="lg:col-span-2 bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl flex flex-col items-center">
          <div className="w-full flex items-center justify-between mb-4 text-xs font-mono text-gray-400">
            <span>
              {activeTab === "player"
                ? `${selectedPlayerObj?.name} Shot Chart (300 Field Goals)`
                : "Click anywhere on the court to simulate shot expectation"}
            </span>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" /> Made
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-400" /> Missed
              </span>
            </div>
          </div>

          {/* Court Component */}
          <div className="w-full max-w-[620px] aspect-[50/47] rounded-xl overflow-hidden bg-surface border border-borderDark/60 shadow-inner p-2">
            <CourtSVG
              shots={activeTab === "player" ? shots : []}
              onCourtClick={handleCourtClick}
              clickedPoint={clickedShot ? { x: clickedShot.shot_x, y: clickedShot.shot_y } : undefined}
            />
          </div>

          <p className="text-[11px] font-mono text-gray-500 mt-3 text-center">
            Standard NBA Dimensions: 50ft width &middot; 47ft half-court length &middot; 23.75ft 3PT arc &middot; 22ft corners
          </p>
        </div>

        {/* Analytics Card */}
        <div className="space-y-6">
          {/* Shot Quality or Click Result Card */}
          {activeTab === "simulator" ? (
            <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-5">
              <h3 className="font-bold text-white text-base flex items-center gap-2">
                <span>📍</span> Spatial Shot Evaluator
              </h3>

              {clickedShot ? (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-surface border border-borderDark text-center">
                    <span className="text-[10px] uppercase font-mono text-gray-400">Make Probability (p̂)</span>
                    <div className="text-4xl font-extrabold font-mono text-emerald-400 mt-1">
                      {(clickedShot.make_probability * 100).toFixed(1)}%
                    </div>
                    <span className="text-xs text-gray-400 font-mono mt-1 block">
                      {clickedShot.shot_dist >= 23.75 ? "3-Point Attempt" : "2-Point Attempt"}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                    <div className="p-3 rounded-xl bg-surface border border-borderDark">
                      <span className="text-gray-400 block text-[10px]">Shot Distance</span>
                      <span className="text-base font-bold text-white">{clickedShot.shot_dist} ft</span>
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
                      <span className="text-base font-bold text-white">{clickedShot.shot_angle}&deg;</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="py-16 text-center text-xs font-mono text-gray-500 border border-dashed border-borderDark rounded-xl p-4">
                  Click any location on the court above to inspect expected conversion probability and point value.
                </div>
              )}
            </div>
          ) : (
            <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-5">
              <div className="flex items-center justify-between border-b border-borderDark pb-3">
                <h3 className="font-bold text-white text-base">
                  {selectedPlayerObj?.name} Shot Breakdown
                </h3>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-surface border border-borderDark text-accent">
                  {selectedPlayerObj?.team}
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
                      Actual eFG% vs League Baseline xeFG%
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
            </div>
          )}

          {/* Mathematical Formulation Explainer */}
          <div className="p-4 bg-surfaceCard border border-borderDark rounded-2xl text-xs text-gray-400 font-mono space-y-1.5 shadow-lg">
            <span className="text-accent font-bold">XGBoost xeFG% Formulation:</span>
            <p className="text-[11px] text-gray-300">
              <code>xeFG% = (Shot_Value &times; p̂) / 2</code>
            </p>
            <p className="text-[11px] text-gray-500">
              Where <code>p̂ = P(Made | dist, angle, period, clock, 3PT)</code> estimates the baseline expectation of an average NBA player from that exact spatial coordinate.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
