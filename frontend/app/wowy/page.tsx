"use client";

import React from "react";
import { WOWYBuilder } from "@/components/wowy-builder";

export default function WOWYPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-white">With-Or-Without-You (WOWY) Lineup Engine</h1>
        <p className="text-sm text-gray-400 mt-1">
          Vectorized 64-bit integer bitmasks queried via in-memory DuckDB over partitioned Apache Parquet possessions.
        </p>
      </div>

      <WOWYBuilder />
    </div>
  );
}
