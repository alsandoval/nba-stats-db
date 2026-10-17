"use client";

import React, { useState, useMemo } from "react";
import { LiveCandlestick } from "@/lib/data-service";

interface DifferentialCandlestickChartProps {
  candlesticks: LiveCandlestick[];
  currentMinute: number;
  onSelectMinute?: (minute: number) => void;
  homeTricode?: string;
  awayTricode?: string;
  homeColor?: string;
  awayColor?: string;
}

export function DifferentialCandlestickChart({
  candlesticks,
  currentMinute,
  onSelectMinute,
  homeTricode = "IND",
  awayTricode = "CLE",
  homeColor = "#002D62",
  awayColor = "#860038",
}: DifferentialCandlestickChartProps) {
  const [hoveredCandle, setHoveredCandle] = useState<LiveCandlestick | null>(null);
  const [viewMode, setViewMode] = useState<"candlestick" | "area">("candlestick");
  const [showWinProb, setShowWinProb] = useState<boolean>(true);

  // SVG dimensions
  const width = 1000;
  const height = 420;
  const margin = { top: 30, right: 55, bottom: 65, left: 55 };
  const chartWidth = width - margin.left - margin.right;
  const chartHeight = height - margin.top - margin.bottom;

  // Split height into Candlestick pane (top 72%) and Volume pane (bottom 28%)
  const candlePaneHeight = chartHeight * 0.72;
  const volumePaneHeight = chartHeight * 0.24;
  const paneGap = chartHeight * 0.04;
  const volumeTop = margin.top + candlePaneHeight + paneGap;

  // Determine Y domain for margin
  const { minMargin, maxMargin, maxVol } = useMemo(() => {
    let minM = -10;
    let maxM = 15;
    let maxV = 10;
    for (const c of candlesticks) {
      if (c.low < minM) minM = c.low;
      if (c.high > maxM) maxM = c.high;
      if (c.volume > maxV) maxV = c.volume;
    }
    // Pad margins to look clean
    const yPad = Math.max(4, Math.ceil((maxM - minM) * 0.1));
    return {
      minMargin: minM - yPad,
      maxMargin: maxM + yPad,
      maxVol: Math.max(12, maxV + 2),
    };
  }, [candlesticks]);

  // Scales
  const totalMinutes = 48;
  const colWidth = chartWidth / totalMinutes;
  const candleBodyWidth = Math.max(6, colWidth * 0.72);

  const getYMargin = (val: number) => {
    const range = maxMargin - minMargin;
    const norm = (val - minMargin) / (range || 1);
    return margin.top + (1 - norm) * candlePaneHeight;
  };

  const getYVolume = (val: number) => {
    const norm = val / (maxVol || 1);
    return volumeTop + volumePaneHeight - norm * volumePaneHeight;
  };

  const getYWinProb = (wp: number) => {
    return margin.top + (1 - wp) * candlePaneHeight;
  };

  const zeroY = getYMargin(0);

  // Win Probability Polyline Path
  const winProbPoints = useMemo(() => {
    return candlesticks
      .map((c) => {
        const x = margin.left + (c.minute - 0.5) * colWidth;
        const y = getYWinProb(c.homeWinProb);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [candlesticks, colWidth]);

  // Area Path for Margin
  const areaPath = useMemo(() => {
    if (candlesticks.length === 0) return "";
    const firstX = margin.left + 0.5 * colWidth;
    let d = `M ${firstX.toFixed(1)} ${zeroY.toFixed(1)} `;
    candlesticks.forEach((c) => {
      const x = margin.left + (c.minute - 0.5) * colWidth;
      const y = getYMargin(c.close);
      d += `L ${x.toFixed(1)} ${y.toFixed(1)} `;
    });
    const lastX = margin.left + (candlesticks.length - 0.5) * colWidth;
    d += `L ${lastX.toFixed(1)} ${zeroY.toFixed(1)} Z`;
    return d;
  }, [candlesticks, colWidth, zeroY]);

  // Current active playhead X
  const playheadX = margin.left + (currentMinute - 0.5) * colWidth;

  return (
    <div className="bg-surfaceCard border border-borderDark rounded-xl p-4 shadow-card flex flex-col gap-3 relative">
      {/* Header & Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-borderDark/60 pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-accent/10 border border-accent/20 text-accent font-bold text-sm">
            📊 OHLC CANDLESTICKS
          </div>
          <div>
            <h3 className="text-white font-extrabold text-sm md:text-base flex items-center gap-2">
              Minute-by-Minute Lead Differential & Volume
              <span className="text-[11px] font-normal text-gray-400 font-mono hidden sm:inline">
                (Financial-Grade NBA Execution)
              </span>
            </h3>
            <p className="text-xs text-gray-400">
              Green = {homeTricode} Lead Growth • Red = {awayTricode} Rally • Bottom Bars = Scoring Intensity
            </p>
          </div>
        </div>

        {/* View Controls */}
        <div className="flex items-center gap-2">
          {/* Win Prob Toggle */}
          <button
            onClick={() => setShowWinProb(!showWinProb)}
            className={`px-2.5 py-1 rounded text-xs font-semibold font-mono transition flex items-center gap-1.5 border ${
              showWinProb
                ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"
                : "bg-surface border-borderDark text-gray-400 hover:text-white"
            }`}
            title="Toggle Continuous Win Probability Overlay"
          >
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            <span>Win Prob (0-100%)</span>
          </button>

          {/* Candlestick vs Area */}
          <div className="flex items-center bg-surface border border-borderDark rounded-lg p-0.5 text-xs">
            <button
              onClick={() => setViewMode("candlestick")}
              className={`px-2.5 py-1 rounded font-medium transition ${
                viewMode === "candlestick"
                  ? "bg-accent text-white shadow-sm font-semibold"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Candlesticks
            </button>
            <button
              onClick={() => setViewMode("area")}
              className={`px-2.5 py-1 rounded font-medium transition ${
                viewMode === "area"
                  ? "bg-accent text-white shadow-sm font-semibold"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Area Lead
            </button>
          </div>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="relative w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto min-w-[750px] select-none"
        >
          <defs>
            {/* Gradients */}
            <linearGradient id="bullishGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.95" />
              <stop offset="100%" stopColor="#059669" stopOpacity="0.85" />
            </linearGradient>
            <linearGradient id="bearishGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ef4444" stopOpacity="0.95" />
              <stop offset="100%" stopColor="#dc2626" stopOpacity="0.85" />
            </linearGradient>
            <linearGradient id="areaLeadGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {/* Grid Background & Zero Line */}
          <rect
            x={margin.left}
            y={margin.top}
            width={chartWidth}
            height={candlePaneHeight}
            fill="#0B0F19"
            rx="6"
          />
          <rect
            x={margin.left}
            y={volumeTop}
            width={chartWidth}
            height={volumePaneHeight}
            fill="#090D16"
            rx="4"
          />

          {/* Horizontal Grid lines */}
          {[-15, -10, -5, 0, 5, 10, 15, 20].map((val) => {
            if (val < minMargin || val > maxMargin) return null;
            const y = getYMargin(val);
            const isZero = val === 0;
            return (
              <g key={`grid-${val}`}>
                <line
                  x1={margin.left}
                  y1={y}
                  x2={width - margin.right}
                  y2={y}
                  stroke={isZero ? "#64748b" : "#1e293b"}
                  strokeWidth={isZero ? 1.5 : 1}
                  strokeDasharray={isZero ? "4 4" : undefined}
                />
                <text
                  x={margin.left - 8}
                  y={y + 4}
                  fill={isZero ? "#94a3b8" : "#475569"}
                  fontSize="10"
                  fontFamily="monospace"
                  textAnchor="end"
                >
                  {val > 0 ? `+${val}` : val}
                </text>
              </g>
            );
          })}

          {/* Period Background Shading & Dividers (Q1, Q2, Q3, Q4) */}
          {[12, 24, 36, 48].map((qMin, idx) => {
            const divX = margin.left + qMin * colWidth;
            const qStartX = margin.left + (qMin - 12) * colWidth;
            const periodNum = idx + 1;
            return (
              <g key={`period-${qMin}`}>
                {/* Quarter Label */}
                <text
                  x={qStartX + (12 * colWidth) / 2}
                  y={margin.top - 10}
                  fill="#94a3b8"
                  fontSize="11"
                  fontWeight="bold"
                  textAnchor="middle"
                >
                  QUARTER {periodNum}
                </text>
                {/* Vertical Divider */}
                {qMin < 48 && (
                  <line
                    x1={divX}
                    y1={margin.top - 5}
                    x2={divX}
                    y2={height - margin.bottom + 15}
                    stroke="#334155"
                    strokeWidth="1.5"
                    strokeDasharray="3 3"
                  />
                )}
              </g>
            );
          })}

          {/* Area Mode Fill */}
          {viewMode === "area" && (
            <path d={areaPath} fill="url(#areaLeadGrad)" stroke="#3b82f6" strokeWidth="2" />
          )}

          {/* Candlesticks & Volume Bars */}
          {candlesticks.map((c) => {
            const isHovered = hoveredCandle?.minute === c.minute;
            const isCurrent = currentMinute === c.minute;
            const isPlayed = c.minute <= currentMinute;
            const candleX = margin.left + (c.minute - 1) * colWidth + (colWidth - candleBodyWidth) / 2;
            const midX = candleX + candleBodyWidth / 2;

            const highY = getYMargin(c.high);
            const lowY = getYMargin(c.low);
            const openY = getYMargin(c.open);
            const closeY = getYMargin(c.close);

            const bodyTop = Math.min(openY, closeY);
            const bodyHeight = Math.max(3, Math.abs(closeY - openY));

            const isBull = c.close >= c.open;
            const candleFill = isBull ? "url(#bullishGrad)" : "url(#bearishGrad)";
            const wickColor = isBull ? "#10b981" : "#ef4444";

            // Volume bar calculations
            const volY = getYVolume(c.volume);
            const volHeight = Math.max(2, volumeTop + volumePaneHeight - volY);

            return (
              <g
                key={`candle-${c.minute}`}
                className="cursor-pointer transition-opacity"
                opacity={isPlayed ? 1 : 0.4}
                onMouseEnter={() => setHoveredCandle(c)}
                onMouseLeave={() => setHoveredCandle(null)}
                onClick={() => onSelectMinute && onSelectMinute(c.minute)}
              >
                {/* Candlestick Mode */}
                {viewMode === "candlestick" && (
                  <>
                    {/* Upper & Lower Wick */}
                    <line
                      x1={midX}
                      y1={highY}
                      x2={midX}
                      y2={lowY}
                      stroke={wickColor}
                      strokeWidth={isHovered || isCurrent ? 2.5 : 1.5}
                    />

                    {/* Candle Body */}
                    <rect
                      x={candleX}
                      y={bodyTop}
                      width={candleBodyWidth}
                      height={bodyHeight}
                      rx="1.5"
                      fill={candleFill}
                      stroke={isHovered || isCurrent ? "#ffffff" : wickColor}
                      strokeWidth={isHovered || isCurrent ? 1.5 : 0.5}
                      className="transition duration-150"
                    />
                  </>
                )}

                {/* Scoring Volume Bar (Bottom Pane) */}
                <rect
                  x={candleX}
                  y={volY}
                  width={candleBodyWidth}
                  height={volHeight}
                  rx="1"
                  fill={isBull ? "#10b981" : "#ef4444"}
                  opacity={isHovered ? 1 : 0.75}
                />

                {/* Invisible Hover Zone for Easy Clicking */}
                <rect
                  x={margin.left + (c.minute - 1) * colWidth}
                  y={margin.top}
                  width={colWidth}
                  height={chartHeight}
                  fill="transparent"
                />
              </g>
            );
          })}

          {/* Continuous Win Probability Curve Overlay */}
          {showWinProb && (
            <g className="pointer-events-none">
              <polyline
                fill="none"
                stroke="#06b6d4"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={winProbPoints}
                className="drop-shadow-[0_0_8px_rgba(6,182,212,0.6)]"
              />
              {/* Right Y-Axis Scale for Win Prob */}
              <text
                x={width - margin.right + 8}
                y={getYWinProb(1.0) + 4}
                fill="#06b6d4"
                fontSize="9"
                fontFamily="monospace"
              >
                100%
              </text>
              <text
                x={width - margin.right + 8}
                y={getYWinProb(0.5) + 4}
                fill="#06b6d4"
                fontSize="9"
                fontFamily="monospace"
              >
                50%
              </text>
              <text
                x={width - margin.right + 8}
                y={getYWinProb(0.0) + 4}
                fill="#06b6d4"
                fontSize="9"
                fontFamily="monospace"
              >
                0%
              </text>
            </g>
          )}

          {/* Active Playhead Scrubber Line */}
          <g className="pointer-events-none">
            <line
              x1={playheadX}
              y1={margin.top - 12}
              x2={playheadX}
              y2={volumeTop + volumePaneHeight}
              stroke="#f59e0b"
              strokeWidth="2"
              strokeDasharray="4 2"
            />
            {/* Scrubber Knob */}
            <circle cx={playheadX} cy={margin.top - 12} r="5" fill="#f59e0b" />
            <text
              x={playheadX}
              y={margin.top - 18}
              fill="#f59e0b"
              fontSize="10"
              fontWeight="bold"
              fontFamily="monospace"
              textAnchor="middle"
            >
              m{currentMinute}
            </text>
          </g>

          {/* X-Axis Minute Labels */}
          {[1, 6, 12, 18, 24, 30, 36, 42, 48].map((m) => {
            const x = margin.left + (m - 0.5) * colWidth;
            return (
              <text
                key={`axis-m-${m}`}
                x={x}
                y={height - margin.bottom + 22}
                fill="#64748b"
                fontSize="10"
                fontFamily="monospace"
                textAnchor="middle"
              >
                {m}&apos;
              </text>
            );
          })}

          <text
            x={width / 2}
            y={height - margin.bottom + 38}
            fill="#94a3b8"
            fontSize="11"
            fontFamily="monospace"
            textAnchor="middle"
          >
            Game Elapsed Time (Minutes 1 - 48)
          </text>

          {/* Volume Pane Title */}
          <text
            x={margin.left}
            y={volumeTop - 5}
            fill="#64748b"
            fontSize="9"
            fontFamily="monospace"
            fontWeight="bold"
          >
            SCORING VOLUME (Combined PTS / Min)
          </text>
        </svg>

        {/* Floating Tooltip when hovering over a minute */}
        {hoveredCandle && (
          <div
            className="absolute z-20 pointer-events-none bg-surface/95 border border-borderDark rounded-lg p-3 shadow-2xl backdrop-blur-md text-xs font-mono min-w-[240px] transform -translate-x-1/2 -translate-y-full"
            style={{
              left: `${((margin.left + (hoveredCandle.minute - 0.5) * colWidth) / width) * 100}%`,
              top: `${(margin.top / height) * 100}%`,
            }}
          >
            <div className="flex items-center justify-between border-b border-borderDark/60 pb-1.5 mb-2">
              <span className="font-bold text-white flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${hoveredCandle.isBullish ? "bg-emerald-400" : "bg-red-400"}`} />
                {hoveredCandle.clockLabel}
              </span>
              <span className="text-gray-400">Min {hoveredCandle.minute}</span>
            </div>

            <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] mb-2">
              <div className="text-gray-400">
                Open Lead:{" "}
                <span className="text-white font-semibold">
                  {hoveredCandle.open > 0 ? `+${hoveredCandle.open}` : hoveredCandle.open}
                </span>
              </div>
              <div className="text-gray-400">
                Close Lead:{" "}
                <span className={`font-semibold ${hoveredCandle.isBullish ? "text-emerald-400" : "text-red-400"}`}>
                  {hoveredCandle.close > 0 ? `+${hoveredCandle.close}` : hoveredCandle.close}
                </span>
              </div>
              <div className="text-gray-400">
                Peak Lead: <span className="text-white font-semibold">+{hoveredCandle.high}</span>
              </div>
              <div className="text-gray-400">
                Trough: <span className="text-white font-semibold">{hoveredCandle.low}</span>
              </div>
              <div className="text-gray-400">
                Scoring: <span className="text-white font-semibold">{hoveredCandle.homePoints} - {hoveredCandle.awayPoints}</span>
              </div>
              <div className="text-cyan-400 font-semibold">
                Win Prob: {(hoveredCandle.homeWinProb * 100).toFixed(1)}%
              </div>
            </div>

            {hoveredCandle.momentum && (
              <div className="bg-accent/15 text-accent border border-accent/30 px-2 py-0.5 rounded text-[10px] font-bold mb-1.5">
                ⚡ {hoveredCandle.momentum}
              </div>
            )}

            {hoveredCandle.keyPlay && (
              <div className="text-[10px] text-gray-300 italic border-t border-borderDark/50 pt-1 line-clamp-2">
                &ldquo;{hoveredCandle.keyPlay}&rdquo;
              </div>
            )}
          </div>
        )}
      </div>

      {/* Legend & Summary Footer */}
      <div className="flex flex-wrap items-center justify-between text-xs text-gray-400 pt-1 border-t border-borderDark/40 font-mono">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-emerald-500 inline-block" />
            <strong className="text-gray-200">Bullish Candle</strong> ({homeTricode} Won Minute)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-red-500 inline-block" />
            <strong className="text-gray-200">Bearish Candle</strong> ({awayTricode} Won Minute)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-1 bg-cyan-400 inline-block" />
            <strong className="text-gray-200">Win Prob Curve</strong> (0% - 100%)
          </span>
        </div>
        <div className="text-gray-400 text-[11px]">
          Click any candle to jump live playback to that exact game minute
        </div>
      </div>
    </div>
  );
}
