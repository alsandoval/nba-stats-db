"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { checkBackendStatus } from "@/lib/data-service";

export function NavHeader() {
  const pathname = usePathname();
  const [isLive, setIsLive] = useState<boolean>(false);
  const [menuOpen, setMenuOpen] = useState<boolean>(false);

  useEffect(() => {
    checkBackendStatus().then(setIsLive);
  }, []);

  const navLinks = [
    { href: "/", label: "Overview", icon: "📊" },
    { href: "/live", label: "Live Center", icon: "🔴", isLive: true },
    { href: "/wowy", label: "WOWY Studio", icon: "⚡" },
    { href: "/rapm", label: "RAPM Hub", icon: "📈" },
    { href: "/shots", label: "Shot Quality", icon: "🎯" },
    { href: "/predictions", label: "Predictions", icon: "🔮" },
    { href: "/cba", label: "CBA & Trade Machine", icon: "⚖️" },
    { href: "/compare", label: "Player Compare", icon: "👥" },
  ];

  return (
    <header className="border-b border-borderDark bg-surface/95 backdrop-blur-md sticky top-0 z-50 px-4 md:px-8 py-3.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand Logo */}
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5 group">
            <span className="text-2xl transform group-hover:scale-110 transition duration-200">🏀</span>
            <div className="flex flex-col">
              <span className="font-extrabold text-lg tracking-wider text-white flex items-center gap-1.5">
                ANTIGRAVITY <span className="text-accent text-sm font-semibold bg-accent/10 px-1.5 py-0.5 rounded border border-accent/30">NBA</span>
              </span>
              <span className="text-[10px] text-gray-400 font-mono">Analytics & Prediction Engine</span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden xl:flex items-center gap-1 font-medium text-sm">
            {navLinks.map((link) => {
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                    active
                      ? "bg-accent/20 text-accent border border-accent/40 shadow-sm"
                      : "text-gray-300 hover:text-white hover:bg-surfaceCard"
                  }`}
                >
                  <span>{link.icon}</span>
                  <span>{link.label}</span>
                  {(link as any).isLive && (
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping inline-block ml-0.5" />
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Status Pill & Actions */}
        <div className="flex items-center gap-3">
          {/* Mode Pill */}
          <div className="flex items-center gap-2 bg-surfaceCard px-3 py-1 rounded-full border border-borderDark text-[11px] font-mono">
            <span
              className={`w-2 h-2 rounded-full ${
                isLive ? "bg-accentGreen animate-pulse shadow-glow" : "bg-cyan-400"
              }`}
            />
            <span className="text-gray-300 hidden sm:inline">
              {isLive ? "FastAPI + DuckDB Live" : "GitHub Pages / Edge Static"}
            </span>
            <span className="text-gray-300 sm:hidden">
              {isLive ? "Live" : "Static"}
            </span>
          </div>

          {/* GitHub Pages Deploy Badge / Help */}
          <Link
            href="/cba"
            className="hidden md:flex items-center gap-1.5 px-3 py-1 bg-surfaceCard hover:bg-surface border border-borderDark rounded-lg text-xs text-gray-300 hover:text-white transition"
            title="Second Apron & Trade Machine Simulator"
          >
            <span>Trade Machine</span>
          </Link>

          {/* Mobile Menu Toggle */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="xl:hidden p-2 rounded-lg bg-surfaceCard border border-borderDark text-gray-300 hover:text-white"
          >
            <span className="text-lg">☰</span>
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {menuOpen && (
        <div className="xl:hidden mt-3 pt-3 border-t border-borderDark grid grid-cols-2 gap-2 text-xs">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setMenuOpen(false)}
              className={`p-2.5 rounded-lg flex items-center gap-2 ${
                pathname === link.href ? "bg-accent/20 text-accent border border-accent/30 font-bold" : "bg-surfaceCard text-gray-300"
              }`}
            >
              <span>{link.icon}</span>
              <span>{link.label}</span>
            </Link>
          ))}
        </div>
      )}
    </header>
  );
}
