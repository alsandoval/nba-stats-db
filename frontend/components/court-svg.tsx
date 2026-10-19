"use client";

import React, { useState } from "react";
import { ShotZoneSplit } from "@/lib/data-service";

export interface CourtShotPoint {
  x: number;
  y: number;
  made: number;
  dist?: number;
  is_3pt?: number;
  p_hat?: number;
  zone?: string;
}

interface CourtSVGProps {
  width?: number | string;
  height?: number | string;
  onCourtClick?: (x: number, y: number) => void;
  shots?: CourtShotPoint[];
  zones?: Record<string, ShotZoneSplit>;
  viewMode?: "both" | "dots" | "zones";
  clickedPoint?: { x: number; y: number };
  children?: React.ReactNode;
}

function getZoneFill(z?: ShotZoneSplit): { fill: string; stroke: string; badgeBg: string; text: string } {
  if (!z || !z.fga) {
    return {
      fill: "rgba(30, 41, 59, 0.25)",
      stroke: "#243456",
      badgeBg: "rgba(15, 23, 42, 0.85)",
      text: "#94a3b8",
    };
  }
  const diff = (z.fg_pct - z.exp_pct) * 100;
  if (diff >= 3.0) {
    return {
      fill: "rgba(16, 185, 129, 0.28)",
      stroke: "#10b981",
      badgeBg: "rgba(6, 78, 59, 0.92)",
      text: "#6ee7b7",
    };
  }
  if (diff >= 0.5) {
    return {
      fill: "rgba(20, 184, 166, 0.20)",
      stroke: "#14b8a6",
      badgeBg: "rgba(19, 78, 74, 0.9)",
      text: "#5eead4",
    };
  }
  if (diff >= -1.5) {
    return {
      fill: "rgba(245, 158, 11, 0.16)",
      stroke: "#f59e0b",
      badgeBg: "rgba(69, 26, 3, 0.9)",
      text: "#fcd34d",
    };
  }
  return {
    fill: "rgba(239, 68, 68, 0.22)",
    stroke: "#ef4444",
    badgeBg: "rgba(69, 10, 10, 0.92)",
    text: "#fca5a5",
  };
}

export function CourtSVG({
  width = "100%",
  height = "100%",
  onCourtClick,
  shots = [],
  zones,
  viewMode = "both",
  clickedPoint,
  children,
}: CourtSVGProps) {
  const [hoveredShot, setHoveredShot] = useState<CourtShotPoint | null>(null);

  const handleSvgClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!onCourtClick) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const feetX = (clickX / rect.width) * 50 - 25;
    const feetY = (clickY / rect.height) * 47;
    onCourtClick(roundFeet(feetX), roundFeet(feetY));
  };

  const roundFeet = (val: number) => Math.round(val * 10) / 10;

  const showZones = (viewMode === "both" || viewMode === "zones") && zones && Object.keys(zones).length > 0;
  const showDots = viewMode === "both" || viewMode === "dots";

  const raStyle = getZoneFill(zones?.["Restricted Area"]);
  const paintStyle = getZoneFill(zones?.["In The Paint (Non-RA)"]);
  const midStyle = getZoneFill(zones?.["Mid-Range"]);
  const lc3Style = getZoneFill(zones?.["Left Corner 3"]);
  const rc3Style = getZoneFill(zones?.["Right Corner 3"]);
  const atb3Style = getZoneFill(zones?.["Above the Break 3"]);

  const renderZoneTag = (
    x: number,
    y: number,
    label: string,
    z?: ShotZoneSplit,
    styleObj?: ReturnType<typeof getZoneFill>
  ) => {
    if (!z || !styleObj) return null;
    const diff = (z.fg_pct - z.exp_pct) * 100;
    const diffStr = diff >= 0 ? `+${diff.toFixed(1)}%` : `${diff.toFixed(1)}%`;
    return (
      <g transform={`translate(${x}, ${y})`} className="pointer-events-none">
        <rect
          x="-5.4"
          y="-1.9"
          width="10.8"
          height="3.8"
          rx="0.9"
          fill={styleObj.badgeBg}
          stroke={styleObj.stroke}
          strokeWidth="0.18"
        />
        <text
          x="0"
          y="-0.3"
          textAnchor="middle"
          fill="#ffffff"
          fontSize="1.25"
          fontWeight="800"
          className="font-mono"
        >
          {(z.fg_pct * 100).toFixed(1)}% ({diffStr})
        </text>
        <text
          x="0"
          y="1.15"
          textAnchor="middle"
          fill={styleObj.text}
          fontSize="0.92"
          fontWeight="600"
          className="font-mono"
        >
          {label} • {z.fgm}/{z.fga}
        </text>
      </g>
    );
  };

  return (
    <div className="relative w-full h-full inline-block rounded-xl overflow-hidden bg-[#070b16] shadow-2xl">
      <svg
        viewBox="-25 -4 50 47"
        width={width}
        height={height}
        onClick={handleSvgClick}
        className="cursor-crosshair select-none w-full h-full"
      >
        <defs>
          <radialGradient id="courtFloorGrad" cx="50%" cy="20%" r="75%">
            <stop offset="0%" stopColor="#131f3a" />
            <stop offset="60%" stopColor="#0b1223" />
            <stop offset="100%" stopColor="#070b16" />
          </radialGradient>
          <linearGradient id="paintKeyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="rgba(59, 130, 246, 0.16)" />
            <stop offset="100%" stopColor="rgba(15, 23, 42, 0.35)" />
          </linearGradient>
        </defs>

        {/* Court Floor */}
        <rect x="-25" y="-4" width="50" height="47" fill="url(#courtFloorGrad)" />

        {/* Subtle Hardwood / Tactical Grid Lines */}
        {[-20, -15, -10, -5, 0, 5, 10, 15, 20].map((gx) => (
          <line
            key={`gx-${gx}`}
            x1={gx}
            y1="0"
            x2={gx}
            y2="43"
            stroke="#1e293b"
            strokeWidth="0.08"
            strokeOpacity="0.45"
          />
        ))}

        {/* Optional 6-Zone Efficiency Heatmap Polygons */}
        {showZones && (
          <g>
            {/* Above the Break 3 Region */}
            <path
              d="M -25 14 L -22 14 A 23.75 23.75 0 0 0 22 14 L 25 14 L 25 43 L -25 43 Z"
              fill={atb3Style.fill}
            />
            {/* Left Corner 3 */}
            <rect x="-25" y="0" width="3" height="14" fill={lc3Style.fill} />
            {/* Right Corner 3 */}
            <rect x="22" y="0" width="3" height="14" fill={rc3Style.fill} />
            {/* Mid-Range */}
            <path
              d="M -22 0 L -8 0 L -8 19 L 8 19 L 8 0 L 22 0 L 22 14 A 23.75 23.75 0 0 1 -22 14 Z"
              fill={midStyle.fill}
            />
            {/* In The Paint (Non-RA) */}
            <rect x="-8" y="0" width="16" height="19" fill={paintStyle.fill} />
            {/* Restricted Area */}
            <path d="M -4 0 L -4 5.25 A 4 4 0 0 0 4 5.25 L 4 0 Z" fill={raStyle.fill} />
          </g>
        )}

        {/* Perimeter / Baseline */}
        <rect x="-25" y="0" width="50" height="43" fill="none" stroke="#283959" strokeWidth="0.35" />

        {/* The Key / Paint (16 ft wide, 19 ft long) */}
        <rect
          x="-8"
          y="0"
          width="16"
          height="19"
          fill={showZones ? "none" : "url(#paintKeyGrad)"}
          stroke="#3b82f6"
          strokeWidth="0.35"
        />

        {/* Lane Hash Marks */}
        {[-8, 8].map((lx) =>
          [7, 8, 11, 14].map((ly) => (
            <line
              key={`hash-${lx}-${ly}`}
              x1={lx}
              y1={ly}
              x2={lx < 0 ? lx - 0.8 : lx + 0.8}
              y2={ly}
              stroke="#3b82f6"
              strokeWidth="0.25"
            />
          ))
        )}

        {/* Free Throw Circle (Radius 6 ft at Y=19) */}
        <path d="M -6 19 A 6 6 0 0 0 6 19" fill="none" stroke="#3b82f6" strokeWidth="0.35" />
        <path
          d="M -6 19 A 6 6 0 0 1 6 19"
          fill="none"
          stroke="#334155"
          strokeWidth="0.3"
          strokeDasharray="0.9,0.9"
        />

        {/* Restricted Area Arc (Radius 4 ft around hoop at 0, 5.25) */}
        <path d="M -4 4 A 4 4 0 0 0 4 4" fill="none" stroke="#f59e0b" strokeWidth="0.38" />

        {/* Backboard (6 ft wide, at Y=4) */}
        <line x1="-3" y1="4" x2="3" y2="4" stroke="#f8fafc" strokeWidth="0.55" />

        {/* Basket Hoop (Radius 0.75 ft at Y=5.25) */}
        <circle cx="0" cy="5.25" r="0.75" fill="none" stroke="#f97316" strokeWidth="0.4" />

        {/* 3-Point Line: Corner 3s at x = -22 and x = 22 extending to y = 14 */}
        <line x1="-22" y1="0" x2="-22" y2="14" stroke="#3b82f6" strokeWidth="0.4" />
        <line x1="22" y1="0" x2="22" y2="14" stroke="#3b82f6" strokeWidth="0.4" />

        {/* 3-Point Arc (Radius 23.75 ft from hoop at 0, 5.25) */}
        <path
          d="M -22 14 A 23.75 23.75 0 0 0 22 14"
          fill="none"
          stroke="#3b82f6"
          strokeWidth="0.4"
        />

        {/* Half Court Line & Center Circle */}
        <line x1="-25" y1="43" x2="25" y2="43" stroke="#283959" strokeWidth="0.4" />
        <circle cx="0" cy="43" r="6" fill="none" stroke="#283959" strokeWidth="0.35" />
        <circle cx="0" cy="43" r="2" fill="none" stroke="#3b82f6" strokeWidth="0.25" />

        {/* Render Player Shot Dots */}
        {showDots &&
          shots.map((s, idx) => (
            <circle
              key={idx}
              cx={s.x}
              cy={s.y}
              r={viewMode === "dots" ? "0.62" : "0.52"}
              fill={s.made === 1 ? "#10b981" : "#f43f5e"}
              fillOpacity={s.made === 1 ? 0.88 : 0.48}
              stroke={s.made === 1 ? "#ecfdf5" : "#881337"}
              strokeWidth="0.09"
              onMouseEnter={() => setHoveredShot(s)}
              onMouseLeave={() => setHoveredShot(null)}
              className="transition-opacity hover:opacity-100"
            />
          ))}

        {/* Render 6-Zone Floating Callout Badges */}
        {showZones && (
          <g>
            {renderZoneTag(0, 2.3, "Rim / RA", zones?.["Restricted Area"], raStyle)}
            {renderZoneTag(0, 12.2, "Paint", zones?.["In The Paint (Non-RA)"], paintStyle)}
            {renderZoneTag(-14.2, 16.5, "Mid-Range", zones?.["Mid-Range"], midStyle)}
            {renderZoneTag(-18.8, 5.2, "L Corner 3", zones?.["Left Corner 3"], lc3Style)}
            {renderZoneTag(18.8, 5.2, "R Corner 3", zones?.["Right Corner 3"], rc3Style)}
            {renderZoneTag(0, 31.8, "Above Break 3", zones?.["Above the Break 3"], atb3Style)}
          </g>
        )}

        {/* Render Clicked Point Target */}
        {clickedPoint && (
          <g transform={`translate(${clickedPoint.x}, ${clickedPoint.y})`}>
            <circle
              cx="0"
              cy="0"
              r="1.6"
              fill="none"
              stroke="#38bdf8"
              strokeWidth="0.3"
              strokeDasharray="0.8,0.8"
              className="animate-spin"
            />
            <circle cx="0" cy="0" r="0.6" fill="#38bdf8" stroke="#ffffff" strokeWidth="0.2" />
          </g>
        )}

        {children}
      </svg>

      {/* Floating Hover Shot Tooltip */}
      {hoveredShot && (
        <div className="absolute bottom-3 left-3 bg-surface/95 backdrop-blur-md border border-borderDark rounded-lg px-3 py-1.5 text-[11px] font-mono text-gray-200 shadow-xl pointer-events-none flex items-center gap-2.5">
          <span
            className={`px-1.5 py-0.5 rounded font-extrabold text-[10px] ${
              hoveredShot.made === 1
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                : "bg-red-500/20 text-red-300 border border-red-500/40"
            }`}
          >
            {hoveredShot.made === 1 ? "MADE FG" : "MISSED FG"}
          </span>
          <span>
            {hoveredShot.zone || (hoveredShot.is_3pt ? "3PT Attempt" : "2PT Attempt")}
          </span>
          {hoveredShot.dist !== undefined && (
            <span className="text-accent font-bold">{hoveredShot.dist} ft</span>
          )}
          {hoveredShot.p_hat !== undefined && (
            <span className="text-gray-400">
              xFG%: {(hoveredShot.p_hat * 100).toFixed(1)}%
            </span>
          )}
        </div>
      )}
    </div>
  );
}
