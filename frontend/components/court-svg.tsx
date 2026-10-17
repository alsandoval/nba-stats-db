"use client";

import React from "react";

export interface CourtShotPoint {
  x: number;
  y: number;
  made: number;
  dist?: number;
  is_3pt?: number;
  p_hat?: number;
}

interface CourtSVGProps {
  width?: number | string;
  height?: number | string;
  onCourtClick?: (x: number, y: number) => void;
  shots?: CourtShotPoint[];
  clickedPoint?: { x: number; y: number };
  children?: React.ReactNode;
}

export function CourtSVG({
  width = "100%",
  height = "100%",
  onCourtClick,
  shots = [],
  clickedPoint,
  children,
}: CourtSVGProps) {
  // Court coordinates: X from -25 to 25 ft, Y from 0 to 47 ft
  const handleSvgClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!onCourtClick) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Convert pixel coordinates to court feet (-25 to 25 ft X, 0 to 47 ft Y)
    const feetX = (clickX / rect.width) * 50 - 25;
    const feetY = (clickY / rect.height) * 47;
    onCourtClick(roundFeet(feetX), roundFeet(feetY));
  };

  const roundFeet = (val: number) => Math.round(val * 10) / 10;

  return (
    <div className="relative w-full h-full inline-block rounded-xl overflow-hidden bg-[#0a0f1d] shadow-xl">
      <svg
        viewBox="-25 -4 50 47"
        width={width}
        height={height}
        onClick={handleSvgClick}
        className="cursor-crosshair select-none w-full h-full"
      >
        {/* Court Floor */}
        <rect x="-25" y="-4" width="50" height="47" fill="#0d1424" />

        {/* Perimeter / Baseline */}
        <rect x="-25" y="0" width="50" height="43" fill="none" stroke="#1f2d47" strokeWidth="0.4" />

        {/* The Key / Paint (16 ft wide, 19 ft long) */}
        <rect x="-8" y="0" width="16" height="19" fill="#131c30" stroke="#3b82f6" strokeWidth="0.35" />

        {/* Free Throw Circle (Radius 6 ft at Y=19) */}
        <circle cx="0" cy="19" r="6" fill="none" stroke="#3b82f6" strokeWidth="0.35" />
        <circle cx="0" cy="19" r="6" fill="none" stroke="#1f2d47" strokeWidth="0.35" strokeDasharray="1,1" />

        {/* Restricted Area Arc (Radius 4 ft around hoop at 0, 4) */}
        <path d="M -4 4 A 4 4 0 0 0 4 4" fill="none" stroke="#f59e0b" strokeWidth="0.35" />

        {/* Backboard (6 ft wide, at Y=4) */}
        <line x1="-3" y1="4" x2="3" y2="4" stroke="#e5e7eb" strokeWidth="0.6" />

        {/* Basket Hoop (Radius 0.75 ft at Y=5.25) */}
        <circle cx="0" cy="5.25" r="0.75" fill="none" stroke="#f97316" strokeWidth="0.4" />

        {/* 3-Point Line: Corner 3s at x = -22 and x = 22 extending to y = 14 */}
        <line x1="-22" y1="0" x2="-22" y2="14" stroke="#3b82f6" strokeWidth="0.4" />
        <line x1="22" y1="0" x2="22" y2="14" stroke="#3b82f6" strokeWidth="0.4" />

        {/* 3-Point Arc (Radius 23.75 ft from hoop at 0, 5.25) */}
        {/* Arc connects (-22, 14) to (22, 14) */}
        <path
          d="M -22 14 A 23.75 23.75 0 0 0 22 14"
          fill="none"
          stroke="#3b82f6"
          strokeWidth="0.4"
        />

        {/* Half Court Line & Center Circle */}
        <line x1="-25" y1="43" x2="25" y2="43" stroke="#1f2d47" strokeWidth="0.4" />
        <circle cx="0" cy="43" r="6" fill="none" stroke="#1f2d47" strokeWidth="0.4" />

        {/* Render Player Shot Dots */}
        {shots.map((s, idx) => (
          <circle
            key={idx}
            cx={s.x}
            cy={s.y}
            r="0.55"
            fill={s.made === 1 ? "#10b981" : "#ef4444"}
            fillOpacity={s.made === 1 ? 0.85 : 0.45}
            stroke={s.made === 1 ? "#059669" : "#dc2626"}
            strokeWidth="0.1"
          />
        ))}

        {/* Render Clicked Point Target */}
        {clickedPoint && (
          <g transform={`translate(${clickedPoint.x}, ${clickedPoint.y})`}>
            <circle cx="0" cy="0" r="1.6" fill="none" stroke="#38bdf8" strokeWidth="0.3" strokeDasharray="0.8,0.8" className="animate-spin" />
            <circle cx="0" cy="0" r="0.6" fill="#38bdf8" stroke="#ffffff" strokeWidth="0.2" />
          </g>
        )}

        {children}
      </svg>
    </div>
  );
}
