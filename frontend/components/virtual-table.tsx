"use client";

import React, { useRef, useState, useMemo } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

export interface ColumnDef {
  key: string;
  header: string;
  width?: string;
  flex?: number;
  sortable?: boolean;
  isPercentile?: boolean;
  align?: "left" | "center" | "right";
  render?: (val: any, row: any, index?: number) => React.ReactNode;
}

interface VirtualTableProps {
  data: any[];
  columns: ColumnDef[];
  rowHeight?: number;
  maxHeight?: string;
  height?: string;
  onRowClick?: (row: any) => void;
  defaultSortKey?: string;
  defaultSortAsc?: boolean;
}

export function PercentileBadge({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, Math.round(value || 0)));
  let badgeColor = "bg-slate-800/90 text-gray-300 border-gray-700";
  let barColor = "bg-gray-500";

  if (clamped >= 90) {
    badgeColor = "bg-emerald-950/90 text-emerald-300 border-emerald-500/50 shadow-sm";
    barColor = "bg-emerald-400";
  } else if (clamped >= 75) {
    badgeColor = "bg-teal-950/90 text-teal-300 border-teal-500/50";
    barColor = "bg-teal-400";
  } else if (clamped >= 50) {
    badgeColor = "bg-amber-950/90 text-amber-300 border-amber-500/50";
    barColor = "bg-amber-400";
  } else if (clamped >= 25) {
    badgeColor = "bg-orange-950/90 text-orange-300 border-orange-500/50";
    barColor = "bg-orange-400";
  } else {
    badgeColor = "bg-red-950/90 text-red-400 border-red-600/50";
    barColor = "bg-red-500";
  }

  return (
    <div className="inline-flex items-center gap-1.5">
      <div className="w-10 h-1.5 rounded-full bg-surface border border-borderDark/70 overflow-hidden hidden sm:block">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${clamped}%` }} />
      </div>
      <span
        className={`inline-flex items-center justify-center font-mono text-[11px] font-extrabold px-2 py-0.5 rounded-md border min-w-[32px] ${badgeColor}`}
      >
        {clamped}
      </span>
    </div>
  );
}

export function VirtualTable({
  data,
  columns,
  rowHeight = 46,
  maxHeight = "600px",
  height,
  onRowClick,
  defaultSortKey,
  defaultSortAsc = false,
}: VirtualTableProps) {
  const parentRef = useRef<HTMLDivElement>(null);
  const [sortKey, setSortKey] = useState<string | null>(defaultSortKey || null);
  const [sortAsc, setSortAsc] = useState<boolean>(defaultSortAsc);

  const handleHeaderClick = (col: ColumnDef) => {
    if (col.sortable === false || col.key === "rank") return;
    if (sortKey === col.key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(col.key);
      const isTextCol =
        col.key.includes("name") || col.key.includes("archetype") || col.key === "season";
      setSortAsc(isTextCol);
    }
  };

  const sortedData = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const vA = a[sortKey];
      const vB = b[sortKey];
      if (typeof vA === "number" && typeof vB === "number") {
        return sortAsc ? vA - vB : vB - vA;
      }
      const sA = String(vA ?? "").toLowerCase();
      const sB = String(vB ?? "").toLowerCase();
      if (sA < sB) return sortAsc ? -1 : 1;
      if (sA > sB) return sortAsc ? 1 : -1;
      return 0;
    });
  }, [data, sortKey, sortAsc]);

  const virtualizer = useVirtualizer({
    count: sortedData.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan: 14,
  });

  const effectiveHeight = height || maxHeight;

  return (
    <div className="border border-borderDark rounded-xl overflow-hidden bg-surfaceCard shadow-inner">
      <div className="overflow-x-auto">
        <div className="min-w-[880px]">
          {/* Sticky Interactive Table Header */}
          <div className="bg-surface/95 backdrop-blur-md border-b border-borderDark flex items-center font-mono font-bold text-[11px] text-gray-400 uppercase tracking-wider py-3 px-4 select-none">
            {columns.map((col) => {
              const isSortable = col.sortable !== false && col.key !== "rank";
              const isActiveSort = sortKey === col.key;
              const flexVal =
                col.flex !== undefined
                  ? col.flex
                  : col.key === "rank"
                  ? 0
                  : col.key.includes("name")
                  ? 1.6
                  : col.key.includes("archetype")
                  ? 1.3
                  : 1;

              return (
                <div
                  key={col.key}
                  onClick={() => handleHeaderClick(col)}
                  style={{
                    width: col.width || "110px",
                    minWidth: col.width || "90px",
                    flex: flexVal,
                  }}
                  className={`px-1.5 flex items-center gap-1 transition ${
                    isSortable ? "cursor-pointer hover:text-white" : ""
                  } ${isActiveSort ? "text-accent font-extrabold" : ""} ${
                    col.align === "right"
                      ? "justify-end text-right"
                      : col.align === "center"
                      ? "justify-center text-center"
                      : "justify-start text-left"
                  }`}
                >
                  <span className="truncate">{col.header}</span>
                  {isSortable && (
                    <span className="text-[9px] opacity-80">
                      {isActiveSort ? (sortAsc ? "▲" : "▼") : "⇅"}
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Virtualized Body */}
          <div
            ref={parentRef}
            style={{ height: effectiveHeight, overflowY: "auto", position: "relative" }}
            className="divide-y divide-borderDark/30"
          >
            {sortedData.length === 0 ? (
              <div className="py-20 text-center font-mono text-xs text-gray-500">
                No matching records found. Try adjusting your search or filter criteria.
              </div>
            ) : (
              <div
                style={{
                  height: `${virtualizer.getTotalSize()}px`,
                  width: "100%",
                  position: "relative",
                }}
              >
                {virtualizer.getVirtualItems().map((virtualRow) => {
                  const row = sortedData[virtualRow.index];
                  return (
                    <div
                      key={virtualRow.index}
                      onClick={() => onRowClick && onRowClick(row)}
                      style={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        width: "100%",
                        height: `${virtualRow.size}px`,
                        transform: `translateY(${virtualRow.start}px)`,
                      }}
                      className={`flex items-center px-4 text-sm transition border-l-2 border-transparent hover:border-l-accent hover:bg-surface/75 ${
                        onRowClick ? "cursor-pointer" : ""
                      } ${virtualRow.index % 2 === 1 ? "bg-surface/20" : ""}`}
                    >
                      {columns.map((col) => {
                        const val = col.key === "rank" ? virtualRow.index + 1 : row[col.key];
                        const flexVal =
                          col.flex !== undefined
                            ? col.flex
                            : col.key === "rank"
                            ? 0
                            : col.key.includes("name")
                            ? 1.6
                            : col.key.includes("archetype")
                            ? 1.3
                            : 1;

                        return (
                          <div
                            key={col.key}
                            style={{
                              width: col.width || "110px",
                              minWidth: col.width || "90px",
                              flex: flexVal,
                            }}
                            className={`px-1.5 truncate ${
                              col.align === "right"
                                ? "text-right"
                                : col.align === "center"
                                ? "text-center"
                                : "text-left"
                            }`}
                          >
                            {col.render ? (
                              col.render(val, row, virtualRow.index)
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
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
