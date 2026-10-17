"use client";

import React, { useEffect, useState } from "react";
import { DataService, CBATeam } from "@/lib/data-service";

export default function CBAPage() {
  const [cbaTeams, setCbaTeams] = useState<CBATeam[]>([]);
  const [selectedTeamAId, setSelectedTeamAId] = useState<number>(1610612738); // BOS
  const [selectedTeamBId, setSelectedTeamBId] = useState<number>(1610612744); // GSW

  // Trade machine state
  const [teamASendIds, setTeamASendIds] = useState<Array<string | number>>([]);
  const [teamBSendIds, setTeamBSendIds] = useState<Array<string | number>>([]);
  const [activeTab, setActiveTab] = useState<"trade" | "overview">("trade");

  // Single team simulator state
  const [simPayroll, setSimPayroll] = useState<number>(185000000);

  useEffect(() => {
    DataService.getCBATeams().then((teams) => {
      setCbaTeams(teams);
      if (teams.length > 1) {
        setSelectedTeamAId(teams[0].team_id);
        setSelectedTeamBId(teams[1].team_id);
      }
    });
  }, []);

  const teamA = cbaTeams.find((t) => t.team_id === selectedTeamAId) || cbaTeams[0];
  const teamB = cbaTeams.find((t) => t.team_id === selectedTeamBId) || cbaTeams[1];

  const fmtM = (val: number) => `$${(val / 1e6).toFixed(2)}M`;

  // Trade machine calculations
  const teamASendPlayers = (teamA?.contracts || []).filter((c) => teamASendIds.includes(c.contract_id));
  const teamBSendPlayers = (teamB?.contracts || []).filter((c) => teamBSendIds.includes(c.contract_id));

  const tradeResult =
    teamA && teamB
      ? DataService.validateTrade(teamA, teamB, teamASendPlayers, teamBSendPlayers)
      : null;

  const toggleSendA = (cid: string | number) => {
    setTeamASendIds((prev) => (prev.includes(cid) ? prev.filter((id) => id !== cid) : [...prev, cid]));
  };

  const toggleSendB = (cid: string | number) => {
    setTeamBSendIds((prev) => (prev.includes(cid) ? prev.filter((id) => id !== cid) : [...prev, cid]));
  };

  const clearTrade = () => {
    setTeamASendIds([]);
    setTeamBSendIds([]);
  };

  return (
    <div className="space-y-6">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-2">
            <span>⚖️</span> 2023 CBA Capology &amp; Trade Machine
          </h1>
          <p className="text-sm text-gray-400 mt-1 font-mono">
            First Apron ($178.1M), Second Apron ($188.9M), Salary Matching Bands &amp; Penalty Simulator
          </p>
        </div>

        {/* Tab switch */}
        <div className="flex bg-surfaceCard rounded-xl p-0.5 border border-borderDark text-xs font-mono">
          <button
            onClick={() => setActiveTab("trade")}
            className={`px-4 py-1.5 rounded-lg transition ${
              activeTab === "trade" ? "bg-accent text-white font-bold" : "text-gray-400 hover:text-white"
            }`}
          >
            2-Team Trade Machine
          </button>
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-4 py-1.5 rounded-lg transition ${
              activeTab === "overview" ? "bg-accent text-white font-bold" : "text-gray-400 hover:text-white"
            }`}
          >
            All Teams Apron Table
          </button>
        </div>
      </div>

      {activeTab === "trade" ? (
        /* TRADE MACHINE VIEW */
        <div className="space-y-6">
          {/* Trade Decision Banner */}
          <div
            className={`p-5 rounded-2xl border transition shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
              !teamASendPlayers.length && !teamBSendPlayers.length
                ? "bg-surfaceCard border-borderDark text-gray-300"
                : tradeResult?.is_legal
                ? "bg-emerald-950/40 border-emerald-500/70 text-emerald-200"
                : "bg-red-950/40 border-red-500/70 text-red-200"
            }`}
          >
            <div className="flex items-center gap-3">
              <span className="text-3xl">
                {!teamASendPlayers.length && !teamBSendPlayers.length
                  ? "⚖️"
                  : tradeResult?.is_legal
                  ? "✅"
                  : "🚫"}
              </span>
              <div>
                <h3 className="text-lg font-extrabold">
                  {!teamASendPlayers.length && !teamBSendPlayers.length
                    ? "Select Players to Propose Trade"
                    : tradeResult?.is_legal
                    ? "TRADE IS SUCCESSFUL & CBA COMPLIANT"
                    : "TRADE FAILS CBA RESTRICTIONS"}
                </h3>
                {tradeResult?.reasons && tradeResult.reasons.length > 0 && (
                  <ul className="text-xs list-disc list-inside mt-1 space-y-0.5 text-red-300 font-mono">
                    {tradeResult.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                )}
                {tradeResult?.is_legal && (teamASendPlayers.length > 0 || teamBSendPlayers.length > 0) && (
                  <p className="text-xs text-emerald-300 font-mono mt-0.5">
                    Both franchises meet 2023 CBA salary-matching bands and apron limits.
                  </p>
                )}
              </div>
            </div>

            <button
              onClick={clearTrade}
              className="px-4 py-1.5 bg-surface hover:bg-surfaceCard border border-borderDark rounded-xl text-xs font-mono font-bold text-gray-300 hover:text-white transition"
            >
              Reset Proposal
            </button>
          </div>

          {/* Trade Machine Stages (Team A & Team B) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Team A Stage */}
            {teamA && (
              <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-5">
                <div className="flex items-center justify-between border-b border-borderDark pb-4">
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-accent/20 border border-accent/40 text-accent font-bold">
                      Team A
                    </span>
                    <select
                      value={selectedTeamAId}
                      onChange={(e) => {
                        setSelectedTeamAId(Number(e.target.value));
                        setTeamASendIds([]);
                      }}
                      className="bg-surface border border-borderDark rounded-xl p-2 text-sm font-bold text-white focus:outline-none focus:border-accent font-mono"
                    >
                      {cbaTeams.map((t) => (
                        <option key={t.team_id} value={t.team_id}>
                          {t.team_name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <span
                    className={`text-xs font-mono font-bold px-2.5 py-1 rounded-full border ${
                      teamA.total_taxable_payroll > teamA.second_apron
                        ? "bg-red-950/60 border-red-500 text-red-300"
                        : teamA.total_taxable_payroll > teamA.first_apron
                        ? "bg-amber-950/60 border-amber-500 text-amber-300"
                        : "bg-surface border-borderDark text-gray-300"
                    }`}
                  >
                    {teamA.tax_bracket}
                  </span>
                </div>

                {/* Team A Payroll / Cap Diagnostic */}
                <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                  <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                    <span className="text-gray-500 block text-[10px]">Payroll</span>
                    <span className="font-bold text-white">{fmtM(teamA.total_taxable_payroll)}</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                    <span className="text-gray-500 block text-[10px]">1st Apron Room</span>
                    <span className="font-bold text-gray-300">{fmtM(teamA.apron_1_space)}</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                    <span className="text-gray-500 block text-[10px]">Tax Bill</span>
                    <span className="font-bold text-amber-400">{fmtM(teamA.estimated_luxury_tax)}</span>
                  </div>
                </div>

                {/* Team A Contract Roster Selector */}
                <div>
                  <h4 className="text-xs uppercase font-mono text-gray-400 mb-2">
                    Select Outgoing Contracts ({teamASendPlayers.length} selected):
                  </h4>
                  <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
                    {teamA.contracts.map((c) => {
                      const isSelected = teamASendIds.includes(c.contract_id);
                      return (
                        <div
                          key={c.contract_id}
                          onClick={() => toggleSendA(c.contract_id)}
                          className={`p-3 rounded-xl border cursor-pointer transition flex items-center justify-between text-xs font-mono ${
                            isSelected
                              ? "bg-accent/20 border-accent text-white shadow-sm"
                              : "bg-surface border-borderDark hover:border-gray-600 text-gray-300"
                          }`}
                        >
                          <div className="truncate">
                            <span className="font-bold block truncate">{c.player_name}</span>
                            <span className="text-[10px] text-gray-400">{c.contract_type}</span>
                          </div>
                          <span className="font-bold text-sm text-accent">
                            {fmtM(c.cap_hit || c.current_salary)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Financial Summary */}
                <div className="p-3 bg-surface rounded-xl border border-borderDark text-xs font-mono space-y-1">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Outgoing Salary:</span>
                    <span className="font-bold text-white">{fmtM(tradeResult?.teamA_outgoing || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Incoming Salary:</span>
                    <span className="font-bold text-cyan-400">{fmtM(tradeResult?.teamA_incoming || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Permitted Incoming:</span>
                    <span className="font-bold text-gray-300">{fmtM(tradeResult?.teamA_allowed_incoming || 0)}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Team B Stage */}
            {teamB && (
              <div className="bg-surfaceCard border border-borderDark rounded-2xl p-6 shadow-xl space-y-5">
                <div className="flex items-center justify-between border-b border-borderDark pb-4">
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-cyan-400/20 border border-cyan-400/40 text-cyan-400 font-bold">
                      Team B
                    </span>
                    <select
                      value={selectedTeamBId}
                      onChange={(e) => {
                        setSelectedTeamBId(Number(e.target.value));
                        setTeamBSendIds([]);
                      }}
                      className="bg-surface border border-borderDark rounded-xl p-2 text-sm font-bold text-white focus:outline-none focus:border-accent font-mono"
                    >
                      {cbaTeams.map((t) => (
                        <option key={t.team_id} value={t.team_id}>
                          {t.team_name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <span
                    className={`text-xs font-mono font-bold px-2.5 py-1 rounded-full border ${
                      teamB.total_taxable_payroll > teamB.second_apron
                        ? "bg-red-950/60 border-red-500 text-red-300"
                        : teamB.total_taxable_payroll > teamB.first_apron
                        ? "bg-amber-950/60 border-amber-500 text-amber-300"
                        : "bg-surface border-borderDark text-gray-300"
                    }`}
                  >
                    {teamB.tax_bracket}
                  </span>
                </div>

                {/* Team B Payroll / Cap Diagnostic */}
                <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                  <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                    <span className="text-gray-500 block text-[10px]">Payroll</span>
                    <span className="font-bold text-white">{fmtM(teamB.total_taxable_payroll)}</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                    <span className="text-gray-500 block text-[10px]">1st Apron Room</span>
                    <span className="font-bold text-gray-300">{fmtM(teamB.apron_1_space)}</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-surface border border-borderDark">
                    <span className="text-gray-500 block text-[10px]">Tax Bill</span>
                    <span className="font-bold text-amber-400">{fmtM(teamB.estimated_luxury_tax)}</span>
                  </div>
                </div>

                {/* Team B Contract Roster Selector */}
                <div>
                  <h4 className="text-xs uppercase font-mono text-gray-400 mb-2">
                    Select Outgoing Contracts ({teamBSendPlayers.length} selected):
                  </h4>
                  <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
                    {teamB.contracts.map((c) => {
                      const isSelected = teamBSendIds.includes(c.contract_id);
                      return (
                        <div
                          key={c.contract_id}
                          onClick={() => toggleSendB(c.contract_id)}
                          className={`p-3 rounded-xl border cursor-pointer transition flex items-center justify-between text-xs font-mono ${
                            isSelected
                              ? "bg-cyan-400/20 border-cyan-400 text-white shadow-sm"
                              : "bg-surface border-borderDark hover:border-gray-600 text-gray-300"
                          }`}
                        >
                          <div className="truncate">
                            <span className="font-bold block truncate">{c.player_name}</span>
                            <span className="text-[10px] text-gray-400">{c.contract_type}</span>
                          </div>
                          <span className="font-bold text-sm text-cyan-400">
                            {fmtM(c.cap_hit || c.current_salary)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Financial Summary */}
                <div className="p-3 bg-surface rounded-xl border border-borderDark text-xs font-mono space-y-1">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Outgoing Salary:</span>
                    <span className="font-bold text-white">{fmtM(tradeResult?.teamB_outgoing || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Incoming Salary:</span>
                    <span className="font-bold text-accent">{fmtM(tradeResult?.teamB_incoming || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Permitted Incoming:</span>
                    <span className="font-bold text-gray-300">{fmtM(tradeResult?.teamB_allowed_incoming || 0)}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* ALL TEAMS APRON TABLE VIEW */
        <div className="bg-surfaceCard border border-borderDark rounded-2xl shadow-xl overflow-hidden">
          <div className="p-5 border-b border-borderDark">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span>📋</span> All 30 NBA Franchises Taxable Payroll &amp; Apron Thresholds
            </h3>
            <p className="text-xs text-gray-400 font-mono mt-0.5">
              Salary Cap: $136.0M &middot; Tax Level: $165.3M &middot; First Apron: $178.1M &middot; Second Apron: $188.9M
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm font-mono">
              <thead className="bg-surface text-gray-400 text-xs uppercase border-b border-borderDark">
                <tr>
                  <th className="py-3 px-4">Franchise</th>
                  <th className="py-3 px-3 text-right">Taxable Payroll</th>
                  <th className="py-3 px-3 text-center">Status Tier</th>
                  <th className="py-3 px-3 text-right">Luxury Tax Bill</th>
                  <th className="py-3 px-3 text-right">1st Apron Space</th>
                  <th className="py-3 px-3 text-right">2nd Apron Space</th>
                  <th className="py-3 px-3 text-center">Frozen Pick</th>
                  <th className="py-3 px-3 text-center">Agg. Trade</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borderDark/40 text-xs">
                {cbaTeams.map((t) => (
                  <tr key={t.team_id} className="hover:bg-surface/50 transition">
                    <td className="py-2.5 px-4 font-bold text-white font-sans flex items-center gap-2">
                      <span className="px-1.5 py-0.5 rounded bg-surface border border-borderDark text-[10px] text-accent font-mono">
                        {t.team_abbreviation}
                      </span>
                      <span>{t.team_name}</span>
                    </td>
                    <td className="py-2.5 px-3 text-right text-gray-200">
                      {fmtM(t.total_taxable_payroll)}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                          t.tax_bracket.includes("Second")
                            ? "bg-red-950/60 border-red-500 text-red-300"
                            : t.tax_bracket.includes("First")
                            ? "bg-amber-950/60 border-amber-500 text-amber-300"
                            : "bg-surface border-borderDark text-gray-400"
                        }`}
                      >
                        {t.tax_bracket}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right text-amber-400 font-bold">
                      {t.estimated_luxury_tax > 0 ? fmtM(t.estimated_luxury_tax) : "$0.00M"}
                    </td>
                    <td
                      className={`py-2.5 px-3 text-right font-bold ${
                        t.apron_1_space >= 0 ? "text-emerald-400" : "text-red-400"
                      }`}
                    >
                      {t.apron_1_space >= 0 ? `+${fmtM(t.apron_1_space)}` : fmtM(t.apron_1_space)}
                    </td>
                    <td
                      className={`py-2.5 px-3 text-right font-bold ${
                        t.apron_2_space >= 0 ? "text-emerald-400" : "text-red-400"
                      }`}
                    >
                      {t.apron_2_space >= 0 ? `+${fmtM(t.apron_2_space)}` : fmtM(t.apron_2_space)}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {t.frozen_first_round_pick ? "❄️ FROZEN" : "Active"}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {t.can_aggregate_salaries_in_trade ? "Allowed" : "🚫 BANNED"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
