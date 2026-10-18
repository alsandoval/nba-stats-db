"use client";

import React, { useState, useMemo } from "react";
import { LiveCandlestick } from "@/lib/data-service";

/**
 * Official 30-Team High-Contrast NBA Palette tuned for dark (#0B0F19) financial/analytics canvas.
 * Ensures dark primary colors (like Pacers Navy #002D62 or Nets Black #000000) have vibrant,
 * unmistakable team-authentic primary and secondary colors that pop with high contrast.
 */
export const NBA_TEAM_PALETTE: Record<
  string,
  { primary: string; secondary: string; name: string }
> = {
  ATL: { primary: "#E03A3E", secondary: "#C1D32F", name: "Hawks Red" },
  BOS: { primary: "#00BA63", secondary: "#BA9653", name: "Celtics Green" },
  BKN: { primary: "#E2E8F0", secondary: "#38BDF8", name: "Brooklyn Silver" },
  CHA: { primary: "#00B2A9", secondary: "#A855F7", name: "Hornets Teal" },
  CHI: { primary: "#EF4444", secondary: "#F8FAFC", name: "Bulls Red" },
  CLE: { primary: "#E11D48", secondary: "#FBBF24", name: "Cavs Wine" },
  DAL: { primary: "#0084FF", secondary: "#94A3B8", name: "Mavs Royal" },
  DEN: { primary: "#FEC524", secondary: "#38BDF8", name: "Nuggets Gold" },
  DET: { primary: "#3B82F6", secondary: "#EF4444", name: "Pistons Blue" },
  GSW: { primary: "#3B82F6", secondary: "#FFC72C", name: "Warriors Blue/Gold" },
  HOU: { primary: "#F43F5E", secondary: "#94A3B8", name: "Rockets Red" },
  IND: { primary: "#FDBB30", secondary: "#3B82F6", name: "Pacers Gold" },
  LAC: { primary: "#38BDF8", secondary: "#F43F5E", name: "Clippers Blue" },
  LAL: { primary: "#FDB927", secondary: "#A855F7", name: "Lakers Gold" },
  MEM: { primary: "#5D76A9", secondary: "#F59E0B", name: "Grizzlies Beale Blue" },
  MIA: { primary: "#F43F5E", secondary: "#06B6D4", name: "Heat Vice/Red" },
  MIL: { primary: "#10B981", secondary: "#EEE1C6", name: "Bucks Green" },
  MIN: { primary: "#78BE20", secondary: "#38BDF8", name: "Wolves Aurora" },
  NOP: { primary: "#E5B869", secondary: "#EF4444", name: "Pelicans Gold" },
  NYK: { primary: "#F58426", secondary: "#2563EB", name: "Knicks Orange" },
  OKC: { primary: "#0095EB", secondary: "#EF3B24", name: "Thunder Blue" },
  ORL: { primary: "#0077C0", secondary: "#C4CED4", name: "Magic Blue" },
  PHI: { primary: "#2563EB", secondary: "#EF4444", name: "Sixers Blue" },
  PHX: { primary: "#F97316", secondary: "#A855F7", name: "Suns Orange" },
  POR: { primary: "#EF4444", secondary: "#CBD5E1", name: "Blazers Red" },
  SAC: { primary: "#A855F7", secondary: "#94A3B8", name: "Kings Purple" },
  SAS: { primary: "#2DD4BF", secondary: "#E2E8F0", name: "Spurs Fiesta/Silver" },
  TOR: { primary: "#EF4444", secondary: "#A855F7", name: "Raptors Red" },
  UTA: { primary: "#FACC15", secondary: "#38BDF8", name: "Jazz Gold" },
  WAS: { primary: "#E31837", secondary: "#3B82F6", name: "Wizards Red" },
};

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace("#", "").trim();
  const full =
    clean.length === 3
      ? clean
          .split("")
          .map((c) => c + c)
          .join("")
      : clean.padEnd(6, "0");
  const num = parseInt(full.slice(0, 6), 16) || 0;
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255];
}

function colorDistance(hexA: string, hexB: string): number {
  const [r1, g1, b1] = hexToRgb(hexA);
  const [r2, g2, b2] = hexToRgb(hexB);
  return Math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2);
}

function ensureBrightOnDark(hex: string, fallback: string): string {
  if (!hex || !hex.startsWith("#")) return fallback;
  const [r, g, b] = hexToRgb(hex);
  const luminance = 0.299 * r + 0.587 * g + 0.114 * b;
  if (luminance >= 75) return hex;
  // Brighten overly dark team hexes so they pop on #0B0F19
  const boost = (c: number) => Math.min(255, Math.round(c + (255 - c) * 0.45));
  const toHex = (c: number) => c.toString(16).padStart(2, "0");
  return `#${toHex(boost(r))}${toHex(boost(g))}${toHex(boost(b))}`;
}

export function getTeamPalette(tricode: string): {
  primary: string;
  secondary: string;
  name: string;
} {
  const tri = (tricode || "").toUpperCase();
  return (
    NBA_TEAM_PALETTE[tri] || {
      primary: "#3B82F6",
      secondary: "#38BDF8",
      name: tri || "NBA",
    }
  );
}

export function resolveMatchupTeamColors(
  homeTricode: string,
  awayTricode: string,
  rawHomeColor?: string,
  rawAwayColor?: string
): { homeColor: string; homeSecondary: string; awayColor: string; awaySecondary: string } {
  const hTri = (homeTricode || "HOM").toUpperCase();
  const aTri = (awayTricode || "AWY").toUpperCase();

  const hEntry = NBA_TEAM_PALETTE[hTri];
  const aEntry = NBA_TEAM_PALETTE[aTri];

  const hPrimary = hEntry?.primary || ensureBrightOnDark(rawHomeColor || "#3B82F6", "#3B82F6");
  const hSec = hEntry?.secondary || "#FBBF24";

  let aPrimary = aEntry?.primary || ensureBrightOnDark(rawAwayColor || "#F43F5E", "#F43F5E");
  let aSec = aEntry?.secondary || "#38BDF8";

  // If the two teams' primary colors are too close visually (e.g. two red teams or two blue teams),
  // switch the away team (or home team) to its official high-contrast secondary color.
  if (colorDistance(hPrimary, aPrimary) < 110) {
    if (colorDistance(hPrimary, aSec) >= 110) {
      const tmp = aPrimary;
      aPrimary = aSec;
      aSec = tmp;
    } else if (colorDistance(hSec, aPrimary) >= 110) {
      return {
        homeColor: hSec,
        homeSecondary: hPrimary,
        awayColor: aPrimary,
        awaySecondary: aSec,
      };
    } else {
      aPrimary = "#F43F5E";
    }
  }

  return {
    homeColor: hPrimary,
    homeSecondary: hSec,
    awayColor: aPrimary,
    awaySecondary: aSec,
  };
}

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
  homeColor,
  awayColor,
}: DifferentialCandlestickChartProps) {
  const [hoveredCandle, setHoveredCandle] = useState<LiveCandlestick | null>(null);
  // Default to "winprob" candlesticks so every candle directly represents each team's Win Probability in Team Colors
  const [metricMode, setMetricMode] = useState<"winprob" | "margin" | "area">("winprob");

  const {
    homeColor: resolvedHomeColor,
    homeSecondary: resolvedHomeSec,
    awayColor: resolvedAwayColor,
    awaySecondary: resolvedAwaySec,
  } = useMemo(
    () => resolveMatchupTeamColors(homeTricode, awayTricode, homeColor, awayColor),
    [homeTricode, awayTricode, homeColor, awayColor]
  );

  // Normalize candlesticks so every candle always has wpOpen, wpHigh, wpLow, wpClose (in 0..1)
  const normalizedCandles = useMemo(() => {
    let prevWp = 0.52;
    return candlesticks.map((c) => {
      const wpClose = typeof c.wpClose === "number" ? c.wpClose : c.homeWinProb ?? 0.5;
      const wpOpen = typeof c.wpOpen === "number" ? c.wpOpen : prevWp;
      const marginSwingWp = (c.high - Math.max(c.open, c.close)) * 0.018;
      const marginDipWp = (Math.min(c.open, c.close) - c.low) * 0.018;
      const wpHigh =
        typeof c.wpHigh === "number"
          ? c.wpHigh
          : Math.min(0.999, Math.max(wpOpen, wpClose) + Math.max(0.005, marginSwingWp));
      const wpLow =
        typeof c.wpLow === "number"
          ? c.wpLow
          : Math.max(0.001, Math.min(wpOpen, wpClose) - Math.max(0.005, marginDipWp));
      prevWp = wpClose;
      // Team that won the Win Probability battle in this minute:
      const homeWonMinute =
        Math.abs(wpClose - wpOpen) > 0.0005
          ? wpClose > wpOpen
          : c.close !== c.open
          ? c.close > c.open
          : wpClose >= 0.5;

      return {
        ...c,
        wpOpen,
        wpHigh,
        wpLow,
        wpClose,
        awayWpOpen: Number((1 - wpOpen).toFixed(4)),
        awayWpClose: Number((1 - wpClose).toFixed(4)),
        homeWonMinute,
      };
    });
  }, [candlesticks]);

  // Active candle at currentMinute
  const activeCandle = useMemo(() => {
    if (hoveredCandle) {
      return normalizedCandles.find((c) => c.minute === hoveredCandle.minute) || normalizedCandles[0];
    }
    return (
      normalizedCandles.find((c) => c.minute === currentMinute) ||
      normalizedCandles[normalizedCandles.length - 1]
    );
  }, [normalizedCandles, hoveredCandle, currentMinute]);

  // SVG dimensions
  const width = 1020;
  const height = 440;
  const margin = { top: 34, right: 68, bottom: 65, left: 68 };
  const chartWidth = width - margin.left - margin.right;
  const chartHeight = height - margin.top - margin.bottom;

  // Split height into Candlestick pane (top 72%) and Volume pane (bottom 24%)
  const candlePaneHeight = chartHeight * 0.72;
  const volumePaneHeight = chartHeight * 0.24;
  const paneGap = chartHeight * 0.04;
  const volumeTop = margin.top + candlePaneHeight + paneGap;

  // Determine Y domain for score margin mode & volume
  const { minMargin, maxMargin, maxVol } = useMemo(() => {
    let minM = -10;
    let maxM = 15;
    let maxV = 10;
    for (const c of normalizedCandles) {
      if (c.low < minM) minM = c.low;
      if (c.high > maxM) maxM = c.high;
      if (c.volume > maxV) maxV = c.volume;
    }
    const yPad = Math.max(4, Math.ceil((maxM - minM) * 0.1));
    return {
      minMargin: minM - yPad,
      maxMargin: maxM + yPad,
      maxVol: Math.max(12, maxV + 2),
    };
  }, [normalizedCandles]);

  // Scales
  const totalMinutes = Math.max(48, normalizedCandles.length);
  const colWidth = chartWidth / totalMinutes;
  const candleBodyWidth = Math.max(5.5, colWidth * 0.74);

  const getYMargin = (val: number) => {
    const range = maxMargin - minMargin;
    const norm = (val - minMargin) / (range || 1);
    return margin.top + (1 - norm) * candlePaneHeight;
  };

  const getYWinProb = (wp: number) => {
    const clamped = Math.max(0, Math.min(1, wp));
    return margin.top + (1 - clamped) * candlePaneHeight;
  };

  const getYVolume = (val: number) => {
    const norm = val / (maxVol || 1);
    return volumeTop + volumePaneHeight - norm * volumePaneHeight;
  };

  const midLineY = metricMode === "margin" ? getYMargin(0) : getYWinProb(0.5);

  // Continuous Win Probability Polyline Path
  const winProbPoints = useMemo(() => {
    return normalizedCandles
      .map((c) => {
        const x = margin.left + (c.minute - 0.5) * colWidth;
        const y = getYWinProb(c.wpClose);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [normalizedCandles, colWidth]);

  // Dual-Team Area Path for Win Probability around 50% centerline
  const { homeAreaPath, awayAreaPath } = useMemo(() => {
    if (normalizedCandles.length === 0) return { homeAreaPath: "", awayAreaPath: "" };
    const y50 = getYWinProb(0.5);
    const firstX = margin.left + 0.5 * colWidth;
    let dHome = `M ${firstX.toFixed(1)} ${y50.toFixed(1)} `;
    let dAway = `M ${firstX.toFixed(1)} ${y50.toFixed(1)} `;

    normalizedCandles.forEach((c) => {
      const x = margin.left + (c.minute - 0.5) * colWidth;
      const yHome = getYWinProb(Math.max(0.5, c.wpClose));
      const yAway = getYWinProb(Math.min(0.5, c.wpClose));
      dHome += `L ${x.toFixed(1)} ${yHome.toFixed(1)} `;
      dAway += `L ${x.toFixed(1)} ${yAway.toFixed(1)} `;
    });

    const lastX = margin.left + (normalizedCandles.length - 0.5) * colWidth;
    dHome += `L ${lastX.toFixed(1)} ${y50.toFixed(1)} Z`;
    dAway += `L ${lastX.toFixed(1)} ${y50.toFixed(1)} Z`;
    return { homeAreaPath: dHome, awayAreaPath: dAway };
  }, [normalizedCandles, colWidth]);

  // Current active playhead X
  const playheadX = margin.left + (currentMinute - 0.5) * colWidth;

  const currentHomeWpPct = activeCandle ? (activeCandle.wpClose * 100).toFixed(1) : "50.0";
  const currentAwayWpPct = activeCandle ? ((1 - activeCandle.wpClose) * 100).toFixed(1) : "50.0";

  return (
    <div className="bg-surfaceCard border border-borderDark rounded-xl p-4 shadow-card flex flex-col gap-3 relative">
      {/* Header & Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-borderDark/60 pb-3">
        <div className="flex items-center gap-3">
          <div
            className="px-2.5 py-1.5 rounded-lg font-extrabold text-xs tracking-wider uppercase border flex items-center gap-2"
            style={{
              backgroundColor: `${resolvedHomeColor}18`,
              borderColor: `${resolvedHomeColor}50`,
              color: resolvedHomeColor,
            }}
          >
            <span>📊 TEAM WIN PROBABILITY OHLC</span>
          </div>
          <div>
            <h3 className="text-white font-extrabold text-sm md:text-base flex items-center gap-2">
              {metricMode === "winprob"
                ? `Minute-by-Minute Win Probability Candlesticks (${awayTricode} vs ${homeTricode})`
                : metricMode === "margin"
                ? `Minute-by-Minute Score Margin Candlesticks (${awayTricode} vs ${homeTricode})`
                : `Team Win Probability Flow (${awayTricode} vs ${homeTricode})`}
            </h3>
            <p className="text-xs text-gray-400 flex flex-wrap items-center gap-2 mt-0.5">
              <span className="inline-flex items-center gap-1">
                <span
                  className="w-2.5 h-2.5 rounded-sm inline-block"
                  style={{ backgroundColor: resolvedHomeColor }}
                />
                <strong className="text-white">{homeTricode}</strong> Win Prob Surge
              </span>
              <span>•</span>
              <span className="inline-flex items-center gap-1">
                <span
                  className="w-2.5 h-2.5 rounded-sm inline-block"
                  style={{ backgroundColor: resolvedAwayColor }}
                />
                <strong className="text-white">{awayTricode}</strong> Win Prob Surge
              </span>
              <span>•</span>
              <span>50% Line = Toss-Up Equilibrium</span>
            </p>
          </div>
        </div>

        {/* Live Team Win Probability Tug-of-War Pill + Mode Selector */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Live Win Prob Breakdown */}
          <div className="bg-surface border border-borderDark rounded-lg px-3 py-1.5 flex items-center gap-3 text-xs font-mono">
            <div className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: resolvedAwayColor }}
              />
              <span className="font-bold text-white">{awayTricode}</span>
              <span className="font-extrabold" style={{ color: resolvedAwayColor }}>
                {currentAwayWpPct}%
              </span>
            </div>
            <div className="w-24 h-2 rounded-full overflow-hidden bg-gray-800 flex">
              <div
                style={{
                  width: `${currentAwayWpPct}%`,
                  backgroundColor: resolvedAwayColor,
                }}
                className="h-full transition-all duration-200"
              />
              <div
                style={{
                  width: `${currentHomeWpPct}%`,
                  backgroundColor: resolvedHomeColor,
                }}
                className="h-full transition-all duration-200"
              />
            </div>
            <div className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: resolvedHomeColor }}
              />
              <span className="font-bold text-white">{homeTricode}</span>
              <span className="font-extrabold" style={{ color: resolvedHomeColor }}>
                {currentHomeWpPct}%
              </span>
            </div>
          </div>

          {/* Chart Metric Mode Switcher */}
          <div className="flex items-center bg-surface border border-borderDark rounded-lg p-0.5 text-xs">
            <button
              onClick={() => setMetricMode("winprob")}
              className={`px-2.5 py-1 rounded font-medium transition ${
                metricMode === "winprob"
                  ? "bg-accent text-white shadow-sm font-semibold"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Win Prob Candles (%)
            </button>
            <button
              onClick={() => setMetricMode("margin")}
              className={`px-2.5 py-1 rounded font-medium transition ${
                metricMode === "margin"
                  ? "bg-accent text-white shadow-sm font-semibold"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Score Margin (Pts)
            </button>
            <button
              onClick={() => setMetricMode("area")}
              className={`px-2.5 py-1 rounded font-medium transition ${
                metricMode === "area"
                  ? "bg-accent text-white shadow-sm font-semibold"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Team WP Area
            </button>
          </div>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="relative w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto min-w-[760px] select-none"
        >
          <defs>
            {/* Team-Colored Candle Gradients */}
            <linearGradient id="homeTeamCandleGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={resolvedHomeColor} stopOpacity="0.98" />
              <stop offset="100%" stopColor={resolvedHomeColor} stopOpacity="0.78" />
            </linearGradient>
            <linearGradient id="awayTeamCandleGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={resolvedAwayColor} stopOpacity="0.98" />
              <stop offset="100%" stopColor={resolvedAwayColor} stopOpacity="0.78" />
            </linearGradient>
            {/* Subtle Territory Background Tints */}
            <linearGradient id="homeZoneTint" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={resolvedHomeColor} stopOpacity="0.14" />
              <stop offset="100%" stopColor={resolvedHomeColor} stopOpacity="0.01" />
            </linearGradient>
            <linearGradient id="awayZoneTint" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={resolvedAwayColor} stopOpacity="0.01" />
              <stop offset="100%" stopColor={resolvedAwayColor} stopOpacity="0.14" />
            </linearGradient>
          </defs>

          {/* Main Chart Background */}
          <rect
            x={margin.left}
            y={margin.top}
            width={chartWidth}
            height={candlePaneHeight}
            fill="#0B0F19"
            rx="6"
          />
          {/* Top Half = Home Team Territory Tint; Bottom Half = Away Team Territory Tint */}
          <rect
            x={margin.left}
            y={margin.top}
            width={chartWidth}
            height={Math.max(0, midLineY - margin.top)}
            fill="url(#homeZoneTint)"
          />
          <rect
            x={margin.left}
            y={midLineY}
            width={chartWidth}
            height={Math.max(0, margin.top + candlePaneHeight - midLineY)}
            fill="url(#awayZoneTint)"
          />

          {/* Team Territory Watermark Badges inside Canvas */}
          <text
            x={margin.left + 12}
            y={margin.top + 18}
            fill={resolvedHomeColor}
            fontSize="11"
            fontFamily="monospace"
            fontWeight="bold"
            opacity="0.85"
          >
            ▲ {homeTricode} WIN PROBABILITY TERRITORY (50% → 100%)
          </text>
          <text
            x={margin.left + 12}
            y={margin.top + candlePaneHeight - 10}
            fill={resolvedAwayColor}
            fontSize="11"
            fontFamily="monospace"
            fontWeight="bold"
            opacity="0.85"
          >
            ▼ {awayTricode} WIN PROBABILITY TERRITORY (50% → 100%)
          </text>

          {/* Volume Pane Background */}
          <rect
            x={margin.left}
            y={volumeTop}
            width={chartWidth}
            height={volumePaneHeight}
            fill="#090D16"
            rx="4"
          />

          {/* Horizontal Grid Lines & Dual-Team Labels */}
          {metricMode !== "margin" ? (
            // WIN PROBABILITY Y-AXIS (0%, 25%, 50%, 75%, 100%)
            [
              { wp: 1.0, leftLabel: `100% ${homeTricode}`, rightLabel: `0% ${awayTricode}`, color: resolvedHomeColor },
              { wp: 0.75, leftLabel: `75% ${homeTricode}`, rightLabel: `25% ${awayTricode}`, color: resolvedHomeColor },
              { wp: 0.5, leftLabel: "50% EVEN", rightLabel: "50% EVEN", color: "#94a3b8" },
              { wp: 0.25, leftLabel: `25% ${homeTricode}`, rightLabel: `75% ${awayTricode}`, color: resolvedAwayColor },
              { wp: 0.0, leftLabel: `0% ${homeTricode}`, rightLabel: `100% ${awayTricode}`, color: resolvedAwayColor },
            ].map((row) => {
              const y = getYWinProb(row.wp);
              const isMid = row.wp === 0.5;
              return (
                <g key={`wp-grid-${row.wp}`}>
                  <line
                    x1={margin.left}
                    y1={y}
                    x2={width - margin.right}
                    y2={y}
                    stroke={isMid ? "#94a3b8" : "#1e293b"}
                    strokeWidth={isMid ? 1.5 : 1}
                    strokeDasharray={isMid ? "5 4" : undefined}
                  />
                  {/* Left Y-Axis: Home Perspective */}
                  <text
                    x={margin.left - 8}
                    y={y + 3}
                    fill={row.color}
                    fontSize="9.5"
                    fontFamily="monospace"
                    fontWeight={isMid ? "bold" : "normal"}
                    textAnchor="end"
                  >
                    {row.leftLabel}
                  </text>
                  {/* Right Y-Axis: Away Perspective */}
                  <text
                    x={width - margin.right + 8}
                    y={y + 3}
                    fill={row.color}
                    fontSize="9.5"
                    fontFamily="monospace"
                    fontWeight={isMid ? "bold" : "normal"}
                    textAnchor="start"
                  >
                    {row.rightLabel}
                  </text>
                </g>
              );
            })
          ) : (
            // SCORE MARGIN Y-AXIS (-15, -10, -5, 0, +5, +10, +15)
            [-20, -15, -10, -5, 0, 5, 10, 15, 20].map((val) => {
              if (val < minMargin || val > maxMargin) return null;
              const y = getYMargin(val);
              const isZero = val === 0;
              const labelColor =
                val > 0 ? resolvedHomeColor : val < 0 ? resolvedAwayColor : "#94a3b8";
              return (
                <g key={`margin-grid-${val}`}>
                  <line
                    x1={margin.left}
                    y1={y}
                    x2={width - margin.right}
                    y2={y}
                    stroke={isZero ? "#94a3b8" : "#1e293b"}
                    strokeWidth={isZero ? 1.5 : 1}
                    strokeDasharray={isZero ? "5 4" : undefined}
                  />
                  <text
                    x={margin.left - 8}
                    y={y + 4}
                    fill={labelColor}
                    fontSize="9.5"
                    fontFamily="monospace"
                    textAnchor="end"
                  >
                    {val > 0 ? `${homeTricode} +${val}` : val < 0 ? `${awayTricode} +${Math.abs(val)}` : "TIE 0"}
                  </text>
                </g>
              );
            })
          )}

          {/* Quarter / OT Period Dividers */}
          {[12, 24, 36, 48].map((qMin, idx) => {
            const divX = margin.left + qMin * colWidth;
            const qStartX = margin.left + (qMin - 12) * colWidth;
            const periodNum = idx + 1;
            return (
              <g key={`period-${qMin}`}>
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
                {qMin < totalMinutes && (
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

          {/* Area Mode Fill (Dual Team Colors) */}
          {metricMode === "area" && (
            <g>
              <path
                d={homeAreaPath}
                fill={resolvedHomeColor}
                fillOpacity="0.32"
                stroke={resolvedHomeColor}
                strokeWidth="2"
              />
              <path
                d={awayAreaPath}
                fill={resolvedAwayColor}
                fillOpacity="0.32"
                stroke={resolvedAwayColor}
                strokeWidth="2"
              />
            </g>
          )}

          {/* Candlesticks & Volume Bars in Team Colors */}
          {normalizedCandles.map((c) => {
            const isHovered = hoveredCandle?.minute === c.minute;
            const isCurrent = currentMinute === c.minute;
            const isPlayed = c.minute <= currentMinute;
            const candleX =
              margin.left + (c.minute - 1) * colWidth + (colWidth - candleBodyWidth) / 2;
            const midX = candleX + candleBodyWidth / 2;

            // Choose Y coordinates based on active metricMode ("winprob" vs "margin")
            const highY =
              metricMode === "margin" ? getYMargin(c.high) : getYWinProb(c.wpHigh);
            const lowY =
              metricMode === "margin" ? getYMargin(c.low) : getYWinProb(c.wpLow);
            const openY =
              metricMode === "margin" ? getYMargin(c.open) : getYWinProb(c.wpOpen);
            const closeY =
              metricMode === "margin" ? getYMargin(c.close) : getYWinProb(c.wpClose);

            const bodyTop = Math.min(openY, closeY);
            const bodyHeight = Math.max(3.5, Math.abs(closeY - openY));

            // Color the candle in the Team Color of whichever team won the minute!
            const isHomeCandle =
              metricMode === "margin" ? c.close >= c.open : c.homeWonMinute;
            const candleFill = isHomeCandle
              ? "url(#homeTeamCandleGrad)"
              : "url(#awayTeamCandleGrad)";
            const teamStrokeColor = isHomeCandle ? resolvedHomeColor : resolvedAwayColor;
            const teamAccentStroke = isHomeCandle ? resolvedHomeSec : resolvedAwaySec;

            // Volume bar calculations
            const volY = getYVolume(c.volume);
            const volHeight = Math.max(2, volumeTop + volumePaneHeight - volY);

            return (
              <g
                key={`candle-${c.minute}`}
                className="cursor-pointer transition-opacity"
                opacity={isPlayed ? 1 : 0.38}
                onMouseEnter={() => setHoveredCandle(c)}
                onMouseLeave={() => setHoveredCandle(null)}
                onClick={() => onSelectMinute && onSelectMinute(c.minute)}
              >
                {/* Candlestick Mode (Win Prob or Margin) */}
                {metricMode !== "area" && (
                  <>
                    {/* Upper & Lower Wick in Team Color */}
                    <line
                      x1={midX}
                      y1={highY}
                      x2={midX}
                      y2={lowY}
                      stroke={teamStrokeColor}
                      strokeWidth={isHovered || isCurrent ? 2.5 : 1.75}
                    />

                    {/* Candle Body in Team Color */}
                    <rect
                      x={candleX}
                      y={bodyTop}
                      width={candleBodyWidth}
                      height={bodyHeight}
                      rx="1.5"
                      fill={candleFill}
                      stroke={
                        isHovered || isCurrent
                          ? "#ffffff"
                          : teamStrokeColor
                      }
                      strokeWidth={isHovered || isCurrent ? 1.6 : 0.8}
                      className="transition duration-150"
                    />
                  </>
                )}

                {/* Scoring Volume Bar (Bottom Pane) in Team Color */}
                <rect
                  x={candleX}
                  y={volY}
                  width={candleBodyWidth}
                  height={volHeight}
                  rx="1"
                  fill={teamStrokeColor}
                  stroke={isHovered ? teamAccentStroke : undefined}
                  strokeWidth={isHovered ? 0.8 : 0}
                  opacity={isHovered ? 1 : 0.82}
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

          {/* Subtle Connecting Win Prob Trendline across Candles */}
          <polyline
            fill="none"
            stroke="#ffffff"
            strokeOpacity={metricMode === "winprob" ? "0.28" : "0.55"}
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={winProbPoints}
            className="pointer-events-none"
          />

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
            Game Elapsed Time (Minutes 1 - {totalMinutes}) • Click Any Minute Candle to Scrub Play-by-Play
          </text>

          {/* Volume Pane Title */}
          <text
            x={margin.left}
            y={volumeTop - 5}
            fill="#94a3b8"
            fontSize="9"
            fontFamily="monospace"
            fontWeight="bold"
          >
            SCORING INTENSITY (PTS / MIN COLORED BY MINUTE WINNER: {homeTricode} vs {awayTricode})
          </text>
        </svg>

        {/* Floating Tooltip when hovering over a minute */}
        {hoveredCandle && (() => {
          const hc =
            normalizedCandles.find((c) => c.minute === hoveredCandle.minute) ||
            normalizedCandles[0];
          const wpSwingPct = ((hc.wpClose - hc.wpOpen) * 100).toFixed(1);
          const candleColor = hc.homeWonMinute ? resolvedHomeColor : resolvedAwayColor;
          const winnerTri = hc.homeWonMinute ? homeTricode : awayTricode;

          return (
            <div
              className="absolute z-20 pointer-events-none bg-surface/95 border border-borderDark rounded-lg p-3 shadow-2xl backdrop-blur-md text-xs font-mono min-w-[275px] transform -translate-x-1/2 -translate-y-full"
              style={{
                left: `${Math.min(86, Math.max(14, ((margin.left + (hc.minute - 0.5) * colWidth) / width) * 100))}%`,
                top: `${(margin.top / height) * 100 + 8}%`,
                borderColor: candleColor,
              }}
            >
              <div className="flex items-center justify-between border-b border-borderDark/60 pb-1.5 mb-2">
                <span className="font-bold text-white flex items-center gap-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-sm"
                    style={{ backgroundColor: candleColor }}
                  />
                  {hc.clockLabel}
                </span>
                <span
                  className="px-1.5 py-0.5 rounded text-[10px] font-bold"
                  style={{
                    backgroundColor: `${candleColor}25`,
                    color: candleColor,
                  }}
                >
                  {winnerTri} Minute (Min {hc.minute})
                </span>
              </div>

              {/* Team Win Probabilities at Close of Minute */}
              <div className="grid grid-cols-2 gap-2 mb-2 p-1.5 rounded bg-surfaceCard border border-borderDark/60">
                <div>
                  <div className="text-[10px] text-gray-400">{homeTricode} Win Prob</div>
                  <div className="text-sm font-extrabold" style={{ color: resolvedHomeColor }}>
                    {(hc.wpClose * 100).toFixed(1)}%
                  </div>
                  <div className="text-[10px] text-gray-400">
                    Open {(hc.wpOpen * 100).toFixed(1)}% ({Number(wpSwingPct) >= 0 ? `+${wpSwingPct}%` : `${wpSwingPct}%`})
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-gray-400">{awayTricode} Win Prob</div>
                  <div className="text-sm font-extrabold" style={{ color: resolvedAwayColor }}>
                    {((1 - hc.wpClose) * 100).toFixed(1)}%
                  </div>
                  <div className="text-[10px] text-gray-400">
                    Open {((1 - hc.wpOpen) * 100).toFixed(1)}% ({Number(wpSwingPct) <= 0 ? `+${Math.abs(Number(wpSwingPct)).toFixed(1)}%` : `-${wpSwingPct}%`})
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] mb-2">
                <div className="text-gray-400">
                  WP Range:{" "}
                  <span className="text-white font-semibold">
                    {(hc.wpLow * 100).toFixed(0)}%–{(hc.wpHigh * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="text-gray-400">
                  Score Margin:{" "}
                  <span className="text-white font-semibold">
                    {hc.open > 0 ? `+${hc.open}` : hc.open} → {hc.close > 0 ? `+${hc.close}` : hc.close}
                  </span>
                </div>
                <div className="text-gray-400">
                  MinutePts ({homeTricode}-{awayTricode}):{" "}
                  <span className="text-white font-semibold">
                    {hc.homePoints} - {hc.awayPoints}
                  </span>
                </div>
                <div className="text-gray-400">
                  Events: <span className="text-white font-semibold">{hc.eventCount} plays</span>
                </div>
              </div>

              {hc.momentum && (
                <div
                  className="px-2 py-0.5 rounded text-[10px] font-bold mb-1.5 border"
                  style={{
                    backgroundColor: `${candleColor}18`,
                    borderColor: `${candleColor}45`,
                    color: candleColor,
                  }}
                >
                  ⚡ {hc.momentum}
                </div>
              )}

              {hc.keyPlay && (
                <div className="text-[10px] text-gray-300 italic border-t border-borderDark/50 pt-1 line-clamp-2">
                  &ldquo;{hc.keyPlay}&rdquo;
                </div>
              )}
            </div>
          );
        })()}
      </div>

      {/* Legend & Summary Footer */}
      <div className="flex flex-wrap items-center justify-between text-xs text-gray-400 pt-1 border-t border-borderDark/40 font-mono">
        <div className="flex flex-wrap items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span
              className="w-3 h-3 rounded-sm inline-block"
              style={{ backgroundColor: resolvedHomeColor }}
            />
            <strong className="text-white">{homeTricode} Candle</strong> ({homeTricode} Win Prob Gained)
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className="w-3 h-3 rounded-sm inline-block"
              style={{ backgroundColor: resolvedAwayColor }}
            />
            <strong className="text-white">{awayTricode} Candle</strong> ({awayTricode} Win Prob Gained)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-slate-400 inline-block" />
            <strong className="text-gray-200">50% Toss-Up Line</strong> (Even Win Odds)
          </span>
        </div>
        <div className="text-gray-400 text-[11px]">
          Candlestick Wicks = Intra-Minute Peak/Trough Win Probability • Body = Open to Close WP%
        </div>
      </div>
    </div>
  );
}
