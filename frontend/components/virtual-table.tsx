"use client";

import React, { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

interface ColumnDef {
  key: string;
  header: string;
  width?: string;
  isPercentile?: boolean;
  align?: "left" | "center" | "right";
  render?: (val: any, row: any) => React.ReactNode;
}

interface VirtualTableProps {
  data: any[];
  columns: ColumnDef[];
  rowHeight?: number;
  maxHeight?: string;
  height?: string;
}

export function PercentileBadge({ value }: { value: number }) {
  let badgeColor = "bg-slate-800 text-gray-400 border-gray-700";
  if (value >= 90) {
    badgeColor = "bg-emerald-950 text-emerald-300 border-emerald-600/50";
  } else if (value >= 75) {
    badgeColor = "bg-teal-950 text-teal-300 border-teal-600/50";
  } else if (value >= 50) {
    badgeColor = "bg-amber-950 text-amber-300 border-amber-600/50";
  } else if (value >= 25) {
    badgeColor = "bg-orange-950 text-orange-300 border-orange-600/50";
  } else {
    badgeColor = "bg-red-950 text-red-400 border-red-700/50";
  }

  return (
    <span
      className={`inline-flex items-center justify-center font-mono text-[11px] font-bold px-2 py-0.5 rounded border ${badgeColor}`}
    >
      {Math.round(value)}
    </span>
  );
}

export function VirtualTable({
  data,
  columns,
  rowHeight = 44,
  maxHeight = "600px",
}: VirtualTableProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: data.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan: 10,
  });

  return (
    <div className="border border-borderDark rounded-lg overflow-hidden bg-surfaceCard">
      {/* Table Header */}
      <div className="bg-surface border-b border-borderDark flex font-semibold text-xs text-gray-400 uppercase tracking-wider py-3 px-4">
        {columns.map((col) => (
          <div
            key={col.key}
            style={{ width: col.width || "120px" }}
            className={`flex-shrink-0 ${
              col.align === "right"
                ? "text-right"
                : col.align === "center"
                ? "text-center"
                : "text-left"
            }`}
          >
            {col.header}
          </div>
        ))}
      </div>

      {/* Virtualized Body */}
      <div
        ref={parentRef}
        style={{ height: maxHeight, overflowY: "auto", position: "relative" }}
        className="divide-y divide-borderDark/40"
      >
        <div
          style={{
            height: `${virtualizer.getTotalSize()}px`,
            width: "100%",
            position: "relative",
          }}
        >
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const row = data[virtualRow.index];
            return (
              <div
                key={virtualRow.index}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
                className="flex items-center px-4 hover:bg-surface/50 text-sm transition"
              >
                {columns.map((col) => {
                  const val = row[col.key];
                  return (
                    <div
                      key={col.key}
                      style={{ width: col.width || "120px" }}
                      className={`flex-shrink-0 truncate ${
                        col.align === "right"
                          ? "text-right"
                          : col.align === "center"
                          ? "text-center"
                          : "text-left"
                      }`}
                    >
                      {col.render ? (
                        col.render(val, row)
                      ) : col.isPercentile ? (
                        <PercentileBadge value={Number(val) || 0} />
                      ) : (
                        val
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
