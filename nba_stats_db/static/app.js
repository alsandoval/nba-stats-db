/**
 * app.js - Frontend logic for NBA Stats Database & Analytics Web Application
 */

const API_BASE = "";

// Global State
let currentSeasons = ["2023-24", "2022-23"];
let currentTeams = [];
let radarChartInstance = null;
let teamBarChartInstance = null;
let playerTrendChartInstance = null;
let currentSqlResults = null;

// --- Initialization ---

document.addEventListener("DOMContentLoaded", () => {
  initNav();
  initStatus();
  initSyncTracker();
  initDashboardEvents();
  initPlayerCompare();
  initTeamCompare();
  initPlayerExplorer();
  initLeaders();
  initSqlPlayground();
  initEndpointsExplorer();
  initLiveTicker();
  initAIChartStudio();
  initCapology();
});

// --- Navigation ---

function initNav() {
  const buttons = document.querySelectorAll(".nav-btn");
  const panes = document.querySelectorAll(".tab-pane");

  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      buttons.forEach(b => b.classList.remove("active"));
      panes.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const target = btn.dataset.target;
      const pane = document.getElementById(target);
      if (pane) pane.classList.add("active");

      // Trigger redraw of charts on tab switch if needed
      if (target === "player-compare" && radarChartInstance) {
        radarChartInstance.resize();
      } else if (target === "team-compare" && teamBarChartInstance) {
        teamBarChartInstance.resize();
      } else if (target === "player-explorer" && playerTrendChartInstance) {
        playerTrendChartInstance.resize();
      } else if (target === "ai-chart-studio" && aiChartInstance) {
        aiChartInstance.resize();
      }
    });
  });
}

// --- Status & KPIs ---

async function initStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/status`);
    const data = await res.json();

    document.getElementById("db-status-text").textContent = `Online (${data.db_size_mb} MB)`;
    document.getElementById("db-status-badge").title = data.db_path;

    if (data.table_counts) {
      document.getElementById("kpi-games").textContent = (data.table_counts.games || 0).toLocaleString();
      document.getElementById("kpi-boxscores").textContent = (data.table_counts.player_game_logs || 0).toLocaleString();
      document.getElementById("kpi-players").textContent = (data.table_counts.players || 0).toLocaleString();
      document.getElementById("kpi-size").textContent = `${data.db_size_mb} MB`;
    }

    if (data.seasons && data.seasons.length > 0) {
      currentSeasons = data.seasons;
      populateSeasonDropdowns();
    }

    // Load initial dashboard data
    loadDashboard();
  } catch (err) {
    document.getElementById("db-status-text").textContent = "API Offline";
    console.error("Failed to connect to API:", err);
  }
}

// --- Live Historical Download Tracker ---

let syncTrackerInterval = null;

function initSyncTracker() {
  pollSyncProgress();
  // Poll every 2 seconds while download is active
  syncTrackerInterval = setInterval(pollSyncProgress, 2000);
}

async function pollSyncProgress() {
  try {
    const res = await fetch(`${API_BASE}/api/sync-progress`);
    if (!res.ok) return;
    const data = await res.json();
    renderSyncTracker(data);

    if (data.is_complete && syncTrackerInterval) {
      // Slow down polling once all 79 seasons are downloaded
      clearInterval(syncTrackerInterval);
      syncTrackerInterval = setInterval(pollSyncProgress, 15000);
    }
  } catch (err) {
    console.debug("Sync tracker poll error:", err);
  }
}

function renderSyncTracker(data) {
  // Progress Bar
  const fill = document.getElementById("tracker-progress-fill");
  if (fill) fill.style.width = `${data.percent}%`;

  const percentBadge = document.getElementById("tracker-percent-badge");
  if (percentBadge) percentBadge.textContent = `${data.percent}%`;

  const statusBadge = document.getElementById("tracker-status-badge");
  const pulse = document.getElementById("tracker-pulse");

  if (data.is_complete) {
    if (statusBadge) {
      statusBadge.textContent = "100% Downloaded";
      statusBadge.className = "badge badge-done";
    }
    if (pulse) pulse.classList.add("done");
  } else {
    if (statusBadge) {
      statusBadge.textContent = `Downloading ${data.current_season}...`;
      statusBadge.className = "badge badge-accent";
    }
    if (pulse) pulse.classList.remove("done");
  }

  // Meta stats
  const seasonsText = document.getElementById("tracker-seasons-text");
  if (seasonsText) seasonsText.textContent = `${data.completed_count} / ${data.total_seasons} Seasons`;

  const currSeasonEl = document.getElementById("tracker-current-season");
  if (currSeasonEl) currSeasonEl.textContent = data.is_complete ? "Complete (1946-2025)" : data.current_season;

  const boxscoresText = document.getElementById("tracker-boxscores-text");
  if (boxscoresText) boxscoresText.textContent = (data.total_boxscores || 0).toLocaleString();

  const dbsizeText = document.getElementById("tracker-dbsize-text");
  if (dbsizeText) dbsizeText.textContent = `${data.db_size_mb} MB`;

  // Also sync KPI cards on dashboard
  const kpiGames = document.getElementById("kpi-games");
  if (kpiGames) kpiGames.textContent = (data.total_games || 0).toLocaleString();

  const kpiBoxscores = document.getElementById("kpi-boxscores");
  if (kpiBoxscores) kpiBoxscores.textContent = (data.total_boxscores || 0).toLocaleString();

  const kpiSize = document.getElementById("kpi-size");
  if (kpiSize) kpiSize.textContent = `${data.db_size_mb} MB`;

  // Render Seasons Matrix Chips
  const matrixContainer = document.getElementById("seasons-matrix-container");
  if (matrixContainer && data.seasons) {
    // Only re-render if count changed or empty
    matrixContainer.innerHTML = data.seasons.map(s => {
      let icon = "";
      if (s.status === "completed") icon = '<i class="fa-solid fa-check"></i> ';
      else if (s.status === "downloading") icon = '<i class="fa-solid fa-spinner fa-spin"></i> ';

      return `<span class="season-chip-status ${s.status}" title="Season ${s.season}: ${s.status}">${icon}${s.season}</span>`;
    }).join("");
  }
}

function populateSeasonDropdowns() {
  const dropdownIds = [
    "standings-season-select",
    "scorers-season-select",
    "pcompare-season-select",
    "tcompare-season-select",
    "leaders-season-select",
  ];

  dropdownIds.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = "";
    currentSeasons.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = `Season ${s}`;
      el.appendChild(opt);
    });
  });
}

// --- Dashboard ---

function initDashboardEvents() {
  const standingsSeason = document.getElementById("standings-season-select");
  standingsSeason.addEventListener("change", () => loadStandings());

  const pillBtns = document.querySelectorAll(".pill-btn");
  pillBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      pillBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      loadStandings(btn.dataset.conf);
    });
  });

  const scorersSeason = document.getElementById("scorers-season-select");
  scorersSeason.addEventListener("change", () => loadTopScorers());
}

async function loadDashboard() {
  loadStandings("East");
  loadTopScorers();
  loadRecentGames();
}

async function loadStandings(conf = "East") {
  const season = document.getElementById("standings-season-select").value || currentSeasons[0];
  const tbody = document.querySelector("#standings-table tbody");
  tbody.innerHTML = `<tr><td colspan="9" class="text-center">Loading standings...</td></tr>`;

  try {
    const res = await fetch(`${API_BASE}/api/standings?season=${season}&conference=${conf}`);
    const data = await res.json();

    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="9" class="text-center">No records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.map(r => `
      <tr>
        <td><strong>#${r.Rank}</strong></td>
        <td><strong>${r.Team}</strong></td>
        <td>${r.W}</td>
        <td>${r.L}</td>
        <td>${r["Win%"].toFixed(3)}</td>
        <td>${r.Home}</td>
        <td>${r.Road}</td>
        <td>${r.L10}</td>
        <td><span class="${r.Diff >= 0 ? 'text-emerald' : 'text-red'}">${r.Diff >= 0 ? '+' : ''}${r.Diff}</span></td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center">Error loading standings.</td></tr>`;
  }
}

async function loadTopScorers() {
  const season = document.getElementById("scorers-season-select").value || currentSeasons[0];
  const tbody = document.querySelector("#dashboard-scorers-table tbody");
  tbody.innerHTML = `<tr><td colspan="9" class="text-center">Loading scorers...</td></tr>`;

  try {
    const res = await fetch(`${API_BASE}/api/leaders?category=pts&season=${season}&limit=8`);
    const data = await res.json();

    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="9" class="text-center">No records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.map((r, i) => `
      <tr>
        <td><strong>#${i + 1}</strong></td>
        <td><strong>${r.Player}</strong></td>
        <td><span class="tag-pill">${r.Team}</span></td>
        <td>${r.GP}</td>
        <td><strong class="text-emerald">${r.PPG}</strong></td>
        <td>${r.RPG}</td>
        <td>${r.APG}</td>
        <td>${r["FG%"]}%</td>
        <td>${r["3P%"]}%</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center">Error loading scorers.</td></tr>`;
  }
}

async function loadRecentGames() {
  const container = document.getElementById("recent-games-container");
  try {
    const res = await fetch(`${API_BASE}/api/games/recent?limit=8`);
    const data = await res.json();

    if (!data.length) {
      container.innerHTML = `<div class="text-muted">No recent games available.</div>`;
      return;
    }

    container.innerHTML = data.map(g => `
      <div class="game-card">
        <div class="game-date-badge">${g.Date} &bull; ${g.Matchup}</div>
        <div class="game-teams-row">
          <span class="${g.Winner === g.HomeTeam ? 'game-winner' : ''}">${g.HomeTeam} ${g.HomePTS}</span>
          <span class="text-muted">-</span>
          <span class="${g.Winner === g.AwayTeam ? 'game-winner' : ''}">${g.AwayPTS} ${g.AwayTeam}</span>
        </div>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<div class="text-muted">Error loading games.</div>`;
  }
}

// --- Player Comparison ---

function initPlayerCompare() {
  setupAutocomplete("pcompare-input-1", "pcompare-list-1");
  setupAutocomplete("pcompare-input-2", "pcompare-list-2");

  document.getElementById("btn-run-pcompare").addEventListener("click", () => runPlayerComparison());
  document.getElementById("pcompare-season-select").addEventListener("change", () => runPlayerComparison());

  // Run initial comparison
  setTimeout(() => runPlayerComparison(), 400);
}

function setPlayerComparison(p1, p2) {
  document.getElementById("pcompare-input-1").value = p1;
  document.getElementById("pcompare-input-2").value = p2;
  runPlayerComparison();
}

async function runPlayerComparison() {
  const p1 = document.getElementById("pcompare-input-1").value.trim();
  const p2 = document.getElementById("pcompare-input-2").value.trim();
  const season = document.getElementById("pcompare-season-select").value || currentSeasons[0];

  if (!p1 || !p2) return;

  try {
    const res = await fetch(`${API_BASE}/api/compare/players?player1=${encodeURIComponent(p1)}&player2=${encodeURIComponent(p2)}&season=${season}`);
    const data = await res.json();

    if (data.error) {
      alert(data.error);
      return;
    }

    renderPlayerComparison(data);
  } catch (err) {
    console.error("Comparison error:", err);
  }
}

function renderPlayerComparison(data) {
  const p1 = data.player1;
  const p2 = data.player2;

  document.getElementById("p1-header-name").textContent = `${p1.name} (${p1.team || 'N/A'})`;
  document.getElementById("p2-header-name").textContent = `${p2.name} (${p2.team || 'N/A'})`;

  // Metric rows with winner highlight
  const metrics = [
    { label: "Points Per Game (PPG)", key: "ppg", higherIsBetter: true },
    { label: "Rebounds Per Game (RPG)", key: "rpg", higherIsBetter: true },
    { label: "Assists Per Game (APG)", key: "apg", higherIsBetter: true },
    { label: "Steals Per Game (SPG)", key: "spg", higherIsBetter: true },
    { label: "Blocks Per Game (BPG)", key: "bpg", higherIsBetter: true },
    { label: "Field Goal % (FG%)", key: "fg_pct", higherIsBetter: true, suffix: "%" },
    { label: "3-Point % (3P%)", key: "fg3_pct", higherIsBetter: true, suffix: "%" },
    { label: "Free Throw % (FT%)", key: "ft_pct", higherIsBetter: true, suffix: "%" },
    { label: "True Shooting % (TS%)", key: "ts_pct", higherIsBetter: true, suffix: "%" },
    { label: "Usage % (USG%)", key: "usg_pct", higherIsBetter: true, suffix: "%" },
    { label: "Offensive Rating", key: "off_rating", higherIsBetter: true },
    { label: "Defensive Rating", key: "def_rating", higherIsBetter: false }, // lower is better
    { label: "Net Rating", key: "net_rating", higherIsBetter: true },
    { label: "Player Impact (PIE)", key: "pie", higherIsBetter: true, suffix: "%" },
    { label: "Minutes Per Game", key: "mpg", higherIsBetter: true },
    { label: "Games Played", key: "gp", higherIsBetter: true },
  ];

  const tbody = document.getElementById("pcompare-tbody");
  tbody.innerHTML = metrics.map(m => {
    const v1 = p1[m.key] !== undefined && p1[m.key] !== null ? p1[m.key] : "-";
    const v2 = p2[m.key] !== undefined && p2[m.key] !== null ? p2[m.key] : "-";

    let p1Win = false;
    let p2Win = false;

    if (typeof v1 === "number" && typeof v2 === "number" && v1 !== v2) {
      if (m.higherIsBetter) {
        p1Win = v1 > v2;
        p2Win = v2 > v1;
      } else {
        p1Win = v1 < v2;
        p2Win = v2 < v1;
      }
    }

    const s = m.suffix || "";
    return `
      <tr>
        <td class="${p1Win ? 'val-win' : ''}">${v1}${v1 !== '-' ? s : ''}</td>
        <td><strong>${m.label}</strong></td>
        <td class="${p2Win ? 'val-win' : ''}">${v2}${v2 !== '-' ? s : ''}</td>
      </tr>
    `;
  }).join("");

  // Render Radar Chart
  renderRadarChart(p1, p2);

  // Render Head-to-Head Section
  renderPlayerH2H(data.h2h, p1.name, p2.name);
}

function renderRadarChart(p1, p2) {
  const ctx = document.getElementById("pcompare-radar-chart").getContext("2d");
  if (radarChartInstance) radarChartInstance.destroy();

  // Normalize stats to 0-100 scale for radar
  const getScale = (val, max) => Math.min(100, Math.max(0, (val / max) * 100));

  const labels = ["Scoring", "Rebounds", "Assists", "Defense (Stl+Blk)", "Efficiency (TS%)", "Impact (PIE)"];

  const p1Data = [
    getScale(p1.ppg || 0, 35),
    getScale(p1.rpg || 0, 14),
    getScale(p1.apg || 0, 11),
    getScale((p1.spg || 0) + (p1.bpg || 0), 3.5),
    getScale(p1.ts_pct || 0, 70),
    getScale(p1.pie || 0, 22),
  ];

  const p2Data = [
    getScale(p2.ppg || 0, 35),
    getScale(p2.rpg || 0, 14),
    getScale(p2.apg || 0, 11),
    getScale((p2.spg || 0) + (p2.bpg || 0), 3.5),
    getScale(p2.ts_pct || 0, 70),
    getScale(p2.pie || 0, 22),
  ];

  radarChartInstance = new Chart(ctx, {
    type: "radar",
    data: {
      labels: labels,
      datasets: [
        {
          label: p1.name,
          data: p1Data,
          backgroundColor: "rgba(59, 130, 246, 0.25)",
          borderColor: "#3b82f6",
          pointBackgroundColor: "#3b82f6",
          pointBorderColor: "#fff",
        },
        {
          label: p2.name,
          data: p2Data,
          backgroundColor: "rgba(239, 68, 68, 0.25)",
          borderColor: "#ef4444",
          pointBackgroundColor: "#ef4444",
          pointBorderColor: "#fff",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      scales: {
        r: {
          angleLines: { color: "rgba(255, 255, 255, 0.1)" },
          grid: { color: "rgba(255, 255, 255, 0.08)" },
          pointLabels: { color: "#94a3b8", font: { size: 11, weight: "bold" } },
          ticks: { display: false, max: 100, min: 0 },
        },
      },
      plugins: {
        legend: {
          labels: { color: "#f8fafc", font: { weight: "bold" } },
        },
      },
    },
  });
}

function renderPlayerH2H(h2h, p1Name, p2Name) {
  const badge = document.getElementById("h2h-record-badge");
  badge.textContent = `${p1Name}: ${h2h.player1_wins}W - ${p2Name}: ${h2h.player2_wins}W`;

  document.getElementById("h2h-p1-label").textContent = `${p1Name} Line`;
  document.getElementById("h2h-p2-label").textContent = `${p2Name} Line`;

  const tbody = document.getElementById("pcompare-h2h-tbody");
  if (!h2h.games || h2h.games.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No direct regular season / playoff matchups found in the database.</td></tr>`;
    return;
  }

  tbody.innerHTML = h2h.games.map(g => `
    <tr>
      <td>${g.date}</td>
      <td><strong>${g.matchup}</strong></td>
      <td><strong>${g.p1_pts} pts</strong>, ${g.p1_reb} reb, ${g.p1_ast} ast</td>
      <td><strong>${g.p2_pts} pts</strong>, ${g.p2_reb} reb, ${g.p2_ast} ast</td>
      <td><span class="${g.p1_wl === 'W' ? 'text-emerald' : 'text-red'}">${g.p1_wl === 'W' ? p1Name + ' Won' : p2Name + ' Won'}</span></td>
    </tr>
  `).join("");
}

// --- Team Comparison ---

async function initTeamCompare() {
  const t1Select = document.getElementById("tcompare-select-1");
  const t2Select = document.getElementById("tcompare-select-2");

  try {
    const res = await fetch(`${API_BASE}/api/teams`);
    currentTeams = await res.json();

    t1Select.innerHTML = "";
    t2Select.innerHTML = "";

    currentTeams.forEach(t => {
      const opt1 = document.createElement("option");
      opt1.value = t.abbreviation;
      opt1.textContent = `${t.full_name} (${t.abbreviation})`;
      t1Select.appendChild(opt1);

      const opt2 = opt1.cloneNode(true);
      t2Select.appendChild(opt2);
    });

    // Defaults: BOS vs DAL
    t1Select.value = "BOS";
    t2Select.value = "DAL";

    document.getElementById("btn-run-tcompare").addEventListener("click", () => runTeamComparison());
    document.getElementById("tcompare-season-select").addEventListener("change", () => runTeamComparison());

    runTeamComparison();
  } catch (err) {
    console.error("Failed to load teams:", err);
  }
}

function setTeamComparison(t1, t2) {
  document.getElementById("tcompare-select-1").value = t1;
  document.getElementById("tcompare-select-2").value = t2;
  runTeamComparison();
}

async function runTeamComparison() {
  const t1 = document.getElementById("tcompare-select-1").value;
  const t2 = document.getElementById("tcompare-select-2").value;
  const season = document.getElementById("tcompare-season-select").value || currentSeasons[0];

  try {
    const res = await fetch(`${API_BASE}/api/compare/teams?team1=${t1}&team2=${t2}&season=${season}`);
    const data = await res.json();
    renderTeamComparison(data);
  } catch (err) {
    console.error("Team comparison error:", err);
  }
}

function renderTeamComparison(data) {
  const t1 = data.team1;
  const t2 = data.team2;

  document.getElementById("t1-header-name").textContent = `${t1.name} (${t1.abbr})`;
  document.getElementById("t2-header-name").textContent = `${t2.name} (${t2.abbr})`;

  const metrics = [
    { label: "Wins - Losses", v1: `${t1.w}-${t1.l}`, v2: `${t2.w}-${t2.l}`, win1: t1.w > t2.w, win2: t2.w > t1.w },
    { label: "Win %", v1: (t1.win_pct || 0).toFixed(3), v2: (t2.win_pct || 0).toFixed(3), win1: t1.win_pct > t2.win_pct, win2: t2.win_pct > t1.win_pct },
    { label: "Conference Rank", v1: `#${t1.conf_rank || '-'}`, v2: `#${t2.conf_rank || '-'}`, win1: t1.conf_rank < t2.conf_rank, win2: t2.conf_rank < t1.conf_rank },
    { label: "Points Per Game (PPG)", v1: t1.ppg || '-', v2: t2.ppg || '-', win1: t1.ppg > t2.ppg, win2: t2.ppg > t1.ppg },
    { label: "Opponent PPG", v1: t1.opp_ppg || '-', v2: t2.opp_ppg || '-', win1: t1.opp_ppg < t2.opp_ppg, win2: t2.opp_ppg < t1.opp_ppg },
    { label: "Point Differential", v1: t1.diff >= 0 ? `+${t1.diff}` : t1.diff, v2: t2.diff >= 0 ? `+${t2.diff}` : t2.diff, win1: t1.diff > t2.diff, win2: t2.diff > t1.diff },
    { label: "Offensive Rating", v1: t1.off_rating || '-', v2: t2.off_rating || '-', win1: t1.off_rating > t2.off_rating, win2: t2.off_rating > t1.off_rating },
    { label: "Defensive Rating", v1: t1.def_rating || '-', v2: t2.def_rating || '-', win1: t1.def_rating < t2.def_rating, win2: t2.def_rating < t1.def_rating },
    { label: "Net Rating", v1: t1.net_rating || '-', v2: t2.net_rating || '-', win1: t1.net_rating > t2.net_rating, win2: t2.net_rating > t1.net_rating },
    { label: "Pace", v1: t1.pace || '-', v2: t2.pace || '-', win1: false, win2: false },
    { label: "True Shooting %", v1: t1.ts_pct ? `${t1.ts_pct}%` : '-', v2: t2.ts_pct ? `${t2.ts_pct}%` : '-', win1: t1.ts_pct > t2.ts_pct, win2: t2.ts_pct > t1.ts_pct },
    { label: "Home Record", v1: t1.home_record || '-', v2: t2.home_record || '-', win1: false, win2: false },
    { label: "Road Record", v1: t1.road_record || '-', v2: t2.road_record || '-', win1: false, win2: false },
  ];

  const tbody = document.getElementById("tcompare-tbody");
  tbody.innerHTML = metrics.map(m => `
    <tr>
      <td class="${m.win1 ? 'val-win' : ''}">${m.v1}</td>
      <td><strong>${m.label}</strong></td>
      <td class="${m.win2 ? 'val-win' : ''}">${m.v2}</td>
    </tr>
  `).join("");

  // Bar Chart
  renderTeamBarChart(t1, t2);

  // Head-to-Head Table
  renderTeamH2H(data.h2h, t1.abbr, t2.abbr);
}

function renderTeamBarChart(t1, t2) {
  const ctx = document.getElementById("tcompare-bar-chart").getContext("2d");
  if (teamBarChartInstance) teamBarChartInstance.destroy();

  const labels = ["Off Rating", "Def Rating", "Net Rating", "True Shooting %"];
  const d1 = [t1.off_rating || 0, t1.def_rating || 0, t1.net_rating || 0, t1.ts_pct || 0];
  const d2 = [t2.off_rating || 0, t2.def_rating || 0, t2.net_rating || 0, t2.ts_pct || 0];

  teamBarChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: t1.abbr,
          data: d1,
          backgroundColor: "#3b82f6",
          borderRadius: 6,
        },
        {
          label: t2.abbr,
          data: d2,
          backgroundColor: "#f97316",
          borderRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      scales: {
        x: { grid: { display: false }, ticks: { color: "#94a3b8" } },
        y: { grid: { color: "rgba(255,255,255,0.06)" }, ticks: { color: "#94a3b8" } },
      },
      plugins: {
        legend: { labels: { color: "#f8fafc" } },
      },
    },
  });
}

function renderTeamH2H(h2h, t1Abbr, t2Abbr) {
  const badge = document.getElementById("tcompare-h2h-badge");
  badge.textContent = `${t1Abbr}: ${h2h.team1_wins}W - ${t2Abbr}: ${h2h.team2_wins}W`;

  const tbody = document.getElementById("tcompare-h2h-tbody");
  if (!h2h.games || h2h.games.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No matchups between these teams found in the database.</td></tr>`;
    return;
  }

  tbody.innerHTML = h2h.games.map(g => `
    <tr>
      <td>${g.Date}</td>
      <td><strong>${g.Matchup}</strong></td>
      <td>${g.HomePTS}</td>
      <td>${g.AwayPTS}</td>
      <td><span class="badge ${g.Winner === t1Abbr ? 'badge-blue' : 'badge-orange'}">${g.Winner}</span></td>
    </tr>
  `).join("");
}

// --- Player Explorer ---

function initPlayerExplorer() {
  setupAutocomplete("pexplore-input", "pexplore-list");
  document.getElementById("btn-run-pexplore").addEventListener("click", () => runPlayerExplorer());

  // Run initial exploration
  setTimeout(() => runPlayerExplorer(), 500);
}

async function runPlayerExplorer() {
  const query = document.getElementById("pexplore-input").value.trim();
  if (!query) return;

  try {
    const res = await fetch(`${API_BASE}/api/players/${encodeURIComponent(query)}`);
    const data = await res.json();
    if (data.error) {
      alert(data.error);
      return;
    }
    renderPlayerProfile(data);
  } catch (err) {
    console.error("Player Explorer error:", err);
  }
}

function renderPlayerProfile(data) {
  const name = data.name;
  const p = data.profile;

  document.getElementById("player-banner-name").textContent = name;
  const initials = name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
  document.getElementById("player-avatar-initials").textContent = initials;

  document.getElementById("player-tag-team").textContent = p.team_name ? `${p.team_city} ${p.team_name}` : "NBA";
  document.getElementById("player-tag-status").textContent = p.roster_status || "Active";
  document.getElementById("player-tag-years").textContent = p.from_year && p.to_year ? `Career: ${p.from_year} - ${p.to_year}` : "NBA Player";

  // Seasons table
  const stbody = document.querySelector("#player-seasons-table tbody");
  stbody.innerHTML = (data.seasons || []).map(s => `
    <tr>
      <td><strong>${s.season}</strong></td>
      <td>${s.season_type}</td>
      <td>${s.team_abbreviation || '-'}</td>
      <td>${s.gp}</td>
      <td>${s.mpg}</td>
      <td><strong class="text-emerald">${s.ppg}</strong></td>
      <td>${s.rpg}</td>
      <td>${s.apg}</td>
      <td>${s.spg}</td>
      <td>${s.bpg}</td>
      <td>${s.fg_pct}%</td>
      <td>${s.fg3_pct}%</td>
      <td>${s.ft_pct}%</td>
      <td>${s.plus_minus >= 0 ? '+' : ''}${s.plus_minus}</td>
    </tr>
  `).join("");

  // Game logs table
  const gltbody = document.querySelector("#player-gamelogs-table tbody");
  gltbody.innerHTML = (data.recent_games || []).map(g => `
    <tr>
      <td>${g.Date}</td>
      <td><strong>${g.Matchup}</strong></td>
      <td><span class="${g.WL === 'W' ? 'text-emerald' : 'text-red'}">${g.WL}</span></td>
      <td>${g.MIN}</td>
      <td><strong>${g.PTS}</strong></td>
      <td>${g.REB}</td>
      <td>${g.AST}</td>
      <td>${g.STL}</td>
      <td>${g.BLK}</td>
      <td>${g.FGM_A}</td>
      <td>${g["FG%"]}%</td>
      <td>${g["3PM_A"]}</td>
      <td>${g["+/-"] >= 0 ? '+' : ''}${g["+/-"]}</td>
    </tr>
  `).join("");

  // Trend Chart
  renderPlayerTrendChart(data.recent_games || []);
}

function renderPlayerTrendChart(logs) {
  const ctx = document.getElementById("player-trend-chart").getContext("2d");
  if (playerTrendChartInstance) playerTrendChartInstance.destroy();

  // Reverse so oldest of recent is on left
  const chronological = [...logs].reverse();
  const dates = chronological.map(g => g.Date.slice(5)); // MM-DD
  const pts = chronological.map(g => g.PTS);
  const reb = chronological.map(g => g.REB);
  const ast = chronological.map(g => g.AST);

  playerTrendChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        {
          label: "Points",
          data: pts,
          borderColor: "#f97316",
          backgroundColor: "rgba(249, 115, 22, 0.1)",
          tension: 0.3,
          fill: true,
        },
        {
          label: "Rebounds",
          data: reb,
          borderColor: "#3b82f6",
          tension: 0.3,
        },
        {
          label: "Assists",
          data: ast,
          borderColor: "#10b981",
          tension: 0.3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8" } },
        y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8" } },
      },
      plugins: {
        legend: { labels: { color: "#f8fafc" } },
      },
    },
  });
}

// --- Leaderboards ---

function initLeaders() {
  const pills = document.querySelectorAll("#leaders-cat-pills .cat-pill");
  pills.forEach(pill => {
    pill.addEventListener("click", () => {
      pills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      loadLeaders();
    });
  });

  document.getElementById("leaders-season-select").addEventListener("change", () => loadLeaders());
  document.getElementById("leaders-type-select").addEventListener("change", () => loadLeaders());
}

async function loadLeaders() {
  const activePill = document.querySelector("#leaders-cat-pills .cat-pill.active");
  const cat = activePill ? activePill.dataset.cat : "pts";
  const season = document.getElementById("leaders-season-select").value || currentSeasons[0];
  const type = document.getElementById("leaders-type-select").value || "Regular Season";

  const catHeader = document.getElementById("leader-cat-header");
  catHeader.textContent = activePill ? activePill.textContent : "Stat";

  const tbody = document.querySelector("#leaders-table tbody");
  tbody.innerHTML = `<tr><td colspan="11" class="text-center">Loading leaders...</td></tr>`;

  try {
    const res = await fetch(`${API_BASE}/api/leaders?category=${cat}&season=${season}&season_type=${encodeURIComponent(type)}&limit=15`);
    const data = await res.json();

    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="11" class="text-center">No records found.</td></tr>`;
      return;
    }

    // Identify dynamic stat key
    const statKey = Object.keys(data[0])[4]; // 5th column in query

    tbody.innerHTML = data.map((r, i) => `
      <tr>
        <td><strong>#${i + 1}</strong></td>
        <td><strong>${r.Player}</strong></td>
        <td><span class="tag-pill">${r.Team}</span></td>
        <td>${r.GP}</td>
        <td>${r.MPG}</td>
        <td><strong class="text-emerald">${r[statKey]}</strong></td>
        <td>${r.PPG}</td>
        <td>${r.RPG}</td>
        <td>${r.APG}</td>
        <td>${r["FG%"]}%</td>
        <td>${r["3P%"]}%</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="11" class="text-center">Error loading leaders.</td></tr>`;
  }
}

// --- SQL Playground ---

function initSqlPlayground() {
  const templateSelect = document.getElementById("sql-templates-select");
  const textarea = document.getElementById("sql-input");

  const templates = {
    triple_doubles: `SELECT 
    p.full_name AS Player,
    l.game_date AS Date,
    l.matchup AS Matchup,
    l.pts AS PTS,
    l.reb AS REB,
    l.ast AS AST,
    l.stl AS STL,
    l.blk AS BLK,
    l.wl AS W_L
FROM player_game_logs l
JOIN players p ON l.player_id = p.player_id
WHERE (
    (CASE WHEN l.pts >= 10 THEN 1 ELSE 0 END) +
    (CASE WHEN l.reb >= 10 THEN 1 ELSE 0 END) +
    (CASE WHEN l.ast >= 10 THEN 1 ELSE 0 END) +
    (CASE WHEN l.stl >= 10 THEN 1 ELSE 0 END) +
    (CASE WHEN l.blk >= 10 THEN 1 ELSE 0 END)
) >= 3
ORDER BY l.game_date DESC
LIMIT 20;`,
    high_scores: `SELECT 
    p.full_name AS Player,
    l.game_date AS Date,
    l.matchup AS Matchup,
    l.pts AS PTS,
    l.reb AS REB,
    l.ast AS AST,
    ROUND(l.fgm, 0) || '/' || ROUND(l.fga, 0) AS FG,
    ROUND(l.fg3m, 0) || '/' || ROUND(l.fg3a, 0) AS \`3PT\`,
    ROUND(l.fg_pct * 100, 1) AS \`FG%\`
FROM player_game_logs l
JOIN players p ON l.player_id = p.player_id
WHERE l.pts >= 50
ORDER BY l.pts DESC;`,
    best_3pt_teams: `SELECT 
    t.full_name AS Team,
    COUNT(g.id) AS Games,
    ROUND(AVG(g.fg3m), 1) AS \`3PM_Per_Game\`,
    ROUND(AVG(g.fg3_pct) * 100, 1) AS \`Team_3P%\`,
    ROUND(AVG(g.pts), 1) AS PPG
FROM team_game_logs g
JOIN teams t ON g.team_id = t.team_id
GROUP BY t.team_id
ORDER BY \`Team_3P%\` DESC;`,
    clutch_home: `SELECT 
    t.full_name AS Team,
    s.season,
    s.home_record AS \`Home_W_L\`,
    s.w AS Total_Wins,
    s.l AS Total_Losses,
    ROUND(s.win_pct, 3) AS Win_Pct
FROM team_season_stats s
JOIN teams t ON s.team_id = t.team_id
WHERE s.season_type = 'Regular Season'
ORDER BY s.win_pct DESC
LIMIT 10;`,
    efficiency_kings: `SELECT 
    p.full_name AS Player,
    s.season,
    s.team_abbreviation AS Team,
    s.gp AS GP,
    ROUND(s.pts, 1) AS PPG,
    ROUND(a.ts_pct * 100, 1) AS \`TrueShooting%\`,
    ROUND(a.off_rating, 1) AS OffRating,
    ROUND(a.net_rating, 1) AS NetRating
FROM player_season_stats s
JOIN players p ON s.player_id = p.player_id
JOIN player_advanced_stats a 
    ON s.player_id = a.player_id 
   AND s.season = a.season 
   AND s.season_type = a.season_type
WHERE s.pts >= 20.0 AND a.ts_pct >= 0.60
ORDER BY a.ts_pct DESC;`
  };

  templateSelect.addEventListener("change", () => {
    const val = templateSelect.value;
    if (templates[val]) {
      textarea.value = templates[val];
    }
  });

  document.getElementById("btn-run-sql").addEventListener("click", () => executeSql());
  document.getElementById("btn-export-csv").addEventListener("click", () => exportCsv());
}

async function executeSql() {
  const sql = document.getElementById("sql-input").value.trim();
  const statusEl = document.getElementById("sql-status-text");
  const thead = document.getElementById("sql-thead-tr");
  const tbody = document.getElementById("sql-tbody");

  if (!sql) return;

  statusEl.textContent = "Executing query...";
  tbody.innerHTML = `<tr><td class="text-center">Running SQL query...</td></tr>`;
  thead.innerHTML = "";

  try {
    const res = await fetch(`${API_BASE}/api/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: sql }),
    });

    const data = await res.json();

    if (data.error) {
      statusEl.textContent = "Error";
      tbody.innerHTML = `<tr><td class="text-red">Error: ${data.error}</td></tr>`;
      return;
    }

    currentSqlResults = data;
    statusEl.textContent = `Returned ${data.total_rows} rows in ${data.duration_ms} ms.`;

    // Render Table Header
    thead.innerHTML = data.columns.map(col => `<th>${col}</th>`).join("");

    // Render Table Body
    tbody.innerHTML = data.rows.map(row => `
      <tr>
        ${data.columns.map(col => `<td>${row[col] !== null && row[col] !== undefined ? row[col] : '-'}</td>`).join("")}
      </tr>
    `).join("");
  } catch (err) {
    statusEl.textContent = "Query failed";
    tbody.innerHTML = `<tr><td class="text-red">Network/Execution Error: ${err.message}</td></tr>`;
  }
}

function exportCsv() {
  if (!currentSqlResults || !currentSqlResults.rows || currentSqlResults.rows.length === 0) {
    alert("No data available to export. Run a query first!");
    return;
  }

  const cols = currentSqlResults.columns;
  const rows = currentSqlResults.rows;

  let csv = cols.join(",") + "\n";
  rows.forEach(r => {
    const line = cols.map(c => {
      let v = r[c];
      if (v === null || v === undefined) return '""';
      v = String(v).replace(/"/g, '""');
      return `"${v}"`;
    }).join(",");
    csv += line + "\n";
  });

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `nba_query_export_${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// --- Autocomplete Helper ---

function setupAutocomplete(inputId, listId) {
  const input = document.getElementById(inputId);
  const list = document.getElementById(listId);

  let debounceTimer = null;

  input.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();

    if (q.length < 2) {
      list.style.display = "none";
      return;
    }

    debounceTimer = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/players/search?q=${encodeURIComponent(q)}`);
        const players = await res.json();

        if (!players.length) {
          list.style.display = "none";
          return;
        }

        list.innerHTML = players.map(p => `
          <div class="autocomplete-item" data-name="${p.full_name}">
            <strong>${p.full_name}</strong> ${p.is_active ? '<span class="tag-pill">Active</span>' : ''}
          </div>
        `).join("");

        list.style.display = "block";

        list.querySelectorAll(".autocomplete-item").forEach(item => {
          item.addEventListener("click", () => {
            input.value = item.dataset.name;
            list.style.display = "none";
          });
        });
      } catch (err) {
        console.error("Autocomplete error:", err);
      }
    }, 250);
  });

  // Close when clicking outside
  document.addEventListener("click", (e) => {
    if (!input.contains(e.target) && !list.contains(e.target)) {
      list.style.display = "none";
    }
  });
}

// --- Endpoints Explorer ---

let allEndpointsData = [];
let activeEpCategory = "ALL";
let activeEpStatus = "ALL";
let epSearchQuery = "";
let epPollingInterval = null;

async function initEndpointsExplorer() {
  const container = document.getElementById("ep-cards-container");
  if (!container) return;

  // Search input
  const searchInput = document.getElementById("ep-search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      epSearchQuery = e.target.value.trim().toLowerCase();
      renderEndpointsCards();
    });
  }

  // Category filter chips
  const chips = document.querySelectorAll("#ep-category-chips .chip");
  chips.forEach(chip => {
    chip.addEventListener("click", () => {
      chips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      activeEpCategory = chip.dataset.category || "ALL";
      renderEndpointsCards();
    });
  });

  // Status filter dropdown
  const statusFilter = document.getElementById("ep-status-filter");
  if (statusFilter) {
    statusFilter.addEventListener("change", (e) => {
      activeEpStatus = e.target.value;
      renderEndpointsCards();
    });
  }

  // Download all endpoints button
  const btnDownloadAll = document.getElementById("btn-download-all-ep");
  if (btnDownloadAll) {
    btnDownloadAll.addEventListener("click", triggerDownloadAllEndpoints);
  }

  // Modal close buttons
  const btnCloseModal = document.getElementById("btn-close-ep-modal");
  const modal = document.getElementById("ep-detail-modal");
  if (btnCloseModal && modal) {
    btnCloseModal.addEventListener("click", () => {
      modal.style.display = "none";
    });
    modal.addEventListener("click", (e) => {
      if (e.target === modal) modal.style.display = "none";
    });
  }

  // Copy SQL button in modal
  const btnCopySql = document.getElementById("btn-copy-modal-sql");
  if (btnCopySql) {
    btnCopySql.addEventListener("click", () => {
      const sqlCode = document.getElementById("modal-sql-code")?.innerText || "";
      navigator.clipboard.writeText(sqlCode).then(() => {
        btnCopySql.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
        setTimeout(() => {
          btnCopySql.innerHTML = '<i class="fa-solid fa-copy"></i> Copy Query';
        }, 2000);
      });
    });
  }

  // Initial load
  await loadEndpointsData();
}

async function loadEndpointsData() {
  try {
    const res = await fetch(`${API_BASE}/api/endpoints`);
    const data = await res.json();
    allEndpointsData = data.endpoints || [];

    // Update KPI counters
    const kpiTotal = document.getElementById("kpi-ep-total");
    const kpiSucceeded = document.getElementById("kpi-ep-succeeded");
    const kpiRows = document.getElementById("kpi-ep-rows");
    const kpiTables = document.getElementById("kpi-ep-tables");

    if (kpiTotal) kpiTotal.innerText = data.total || allEndpointsData.length;
    if (kpiSucceeded) kpiSucceeded.innerText = data.succeeded || 0;
    if (kpiRows) kpiRows.innerText = (data.total_rows || 0).toLocaleString();

    // Count total tables created
    let tableCount = 0;
    allEndpointsData.forEach(ep => {
      tableCount += ep.result_sets_count || 0;
    });
    if (kpiTables) kpiTables.innerText = tableCount;

    renderEndpointsCards();
  } catch (err) {
    console.error("Failed to load endpoints catalog:", err);
  }
}

function renderEndpointsCards() {
  const container = document.getElementById("ep-cards-container");
  if (!container) return;

  const filtered = allEndpointsData.filter(ep => {
    // Category match
    if (activeEpCategory !== "ALL" && ep.category !== activeEpCategory) return false;

    // Status match
    const st = (ep.status || "PENDING").toUpperCase();
    if (activeEpStatus !== "ALL" && st !== activeEpStatus) return false;

    // Search query match
    if (epSearchQuery) {
      const name = (ep.endpoint_name || "").toLowerCase();
      const doc = (ep.docstring || "").toLowerCase();
      const cat = (ep.category || "").toLowerCase();
      if (!name.includes(epSearchQuery) && !doc.includes(epSearchQuery) && !cat.includes(epSearchQuery)) {
        return false;
      }
    }

    return true;
  });

  if (!filtered.length) {
    container.innerHTML = `
      <div class="glass-card" style="grid-column: 1 / -1; padding: 2rem; text-align: center;">
        <i class="fa-solid fa-filter-circle-xmark fa-2x text-muted mb-2"></i>
        <p class="text-secondary">No endpoints found matching current filters.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(ep => {
    const st = (ep.status || "PENDING").toUpperCase();
    let badgeClass = "badge-outline";
    let badgeText = st;
    let badgeIcon = "fa-clock";

    if (st === "SUCCESS") {
      badgeClass = "badge-done";
      badgeText = `Downloaded (${(ep.total_rows || 0).toLocaleString()} rows)`;
      badgeIcon = "fa-circle-check";
    } else if (st === "EMPTY") {
      badgeClass = "badge-accent";
      badgeText = "Empty Dataset";
      badgeIcon = "fa-circle-exclamation";
    } else if (st === "DEPRECATED") {
      badgeClass = "badge-outline text-muted";
      badgeText = "Deprecated by NBA";
      badgeIcon = "fa-ban";
    } else if (st === "ERROR") {
      badgeClass = "badge-outline text-red";
      badgeText = "Error";
      badgeIcon = "fa-triangle-exclamation";
    }

    return `
      <div class="ep-card" id="card-${ep.endpoint_name}">
        <div>
          <div class="ep-card-header">
            <div>
              <div class="ep-card-title">${ep.endpoint_name}</div>
              <div class="ep-card-category"><i class="fa-solid fa-tag"></i> ${ep.category}</div>
            </div>
            <span class="badge ${badgeClass}"><i class="fa-solid ${badgeIcon}"></i> ${badgeText}</span>
          </div>
          <div class="ep-card-doc mt-2">${ep.docstring || "Standard NBA Stats API endpoint."}</div>
        </div>

        <div>
          <div class="ep-card-meta">
            <span><i class="fa-solid fa-table"></i> ${ep.result_sets_count || 0} Tables</span>
            <span><i class="fa-solid fa-layer-group"></i> ${(ep.total_rows || 0).toLocaleString()} Rows</span>
          </div>
          <div class="ep-card-actions mt-2">
            <button class="btn btn-outline" onclick="viewEndpointDetail('${ep.endpoint_name}')">
              <i class="fa-solid fa-magnifying-glass-chart"></i> View Data
            </button>
            <button class="btn btn-primary" id="btn-dl-${ep.endpoint_name}" onclick="downloadSingleEndpoint('${ep.endpoint_name}')">
              <i class="fa-solid fa-cloud-arrow-down"></i> Download
            </button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

async function viewEndpointDetail(epName) {
  try {
    const res = await fetch(`${API_BASE}/api/endpoints/${encodeURIComponent(epName)}`);
    const data = await res.json();

    const modal = document.getElementById("ep-detail-modal");
    if (!modal) return;

    document.getElementById("modal-ep-title").innerText = data.endpoint_name;
    document.getElementById("modal-ep-category").innerText = data.category;
    document.getElementById("modal-ep-doc").innerText = data.docstring || "No description provided.";
    document.getElementById("modal-ep-rows").innerText = (data.total_rows || 0).toLocaleString();
    document.getElementById("modal-ep-tables-count").innerText = (data.datasets || []).length;
    document.getElementById("modal-ep-params").innerText = (data.required_params || []).join(", ") || "None (Defaults)";
    document.getElementById("modal-ep-date").innerText = data.last_downloaded_at ? new Date(data.last_downloaded_at).toLocaleString() : "Never";

    const badge = document.getElementById("modal-ep-badge");
    const st = (data.status || "PENDING").toUpperCase();
    badge.className = `badge ${st === "SUCCESS" ? "badge-done" : st === "EMPTY" ? "badge-accent" : "badge-outline"}`;
    badge.innerText = st;

    // Render dataset tabs
    const tabsBar = document.getElementById("modal-dataset-tabs");
    const datasets = data.datasets || [];

    if (!datasets.length) {
      tabsBar.innerHTML = `<span class="text-secondary text-sm">No dataset tables generated yet. Click "Download" to fetch live data.</span>`;
      document.getElementById("modal-table-thead").innerHTML = "";
      document.getElementById("modal-table-tbody").innerHTML = `<tr><td class="text-center text-muted">No data available.</td></tr>`;
      document.getElementById("modal-sql-code").innerText = `-- Download endpoint to generate SQL table.`;
    } else {
      tabsBar.innerHTML = datasets.map((ds, i) => `
        <button class="dataset-tab-btn ${i === 0 ? 'active' : ''}" data-idx="${i}">
          ${ds.dataset_name} (${ds.row_count} rows)
        </button>
      `).join("");

      const tabButtons = tabsBar.querySelectorAll(".dataset-tab-btn");
      tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
          tabButtons.forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          const idx = parseInt(btn.dataset.idx, 10);
          showDatasetTable(datasets[idx]);
        });
      });

      // Show first dataset table by default
      showDatasetTable(datasets[0]);
    }

    modal.style.display = "flex";
  } catch (err) {
    console.error("Failed to fetch endpoint details:", err);
    alert(`Could not load details for ${epName}: ${err.message}`);
  }
}

function showDatasetTable(dataset) {
  if (!dataset) return;
  const cols = dataset.columns || [];
  const rows = dataset.preview_rows || [];
  const tblName = dataset.table_name || "";

  // Update sample SQL
  const sqlBox = document.getElementById("modal-sql-code");
  if (sqlBox) {
    sqlBox.innerText = `SELECT * FROM ${tblName} LIMIT 20;`;
  }

  // Update table header
  const thead = document.getElementById("modal-table-thead");
  thead.innerHTML = cols.map(c => `<th>${c}</th>`).join("");

  // Update table body
  const tbody = document.getElementById("modal-table-tbody");
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="${cols.length || 1}" class="text-center text-muted">Empty dataset table.</td></tr>`;
    return;
  }

  tbody.innerHTML = rows.map(r => `
    <tr>
      ${cols.map(c => `<td>${r[c] !== null && r[c] !== undefined ? r[c] : '-'}</td>`).join("")}
    </tr>
  `).join("");
}

async function downloadSingleEndpoint(epName) {
  const btn = document.getElementById(`btn-dl-${epName}`);
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Downloading...`;
  }

  try {
    const res = await fetch(`${API_BASE}/api/endpoints/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ endpoint: epName, force: true }),
    });
    const result = await res.json();

    // Poll until single download finishes
    const checkTimer = setInterval(async () => {
      const stRes = await fetch(`${API_BASE}/api/endpoints/download/status`);
      const stData = await stRes.json();
      if (!stData.is_running) {
        clearInterval(checkTimer);
        await loadEndpointsData();
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> Download`;
        }
      }
    }, 1000);
  } catch (err) {
    console.error(`Failed to download ${epName}:`, err);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> Download`;
    }
  }
}

async function triggerDownloadAllEndpoints() {
  const btn = document.getElementById("btn-download-all-ep");
  if (btn) btn.disabled = true;

  try {
    const payload = {};
    if (activeEpCategory !== "ALL") {
      payload.category = activeEpCategory;
    }

    const res = await fetch(`${API_BASE}/api/endpoints/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    // Show progress banner
    const banner = document.getElementById("ep-download-card");
    if (banner) banner.style.display = "block";

    // Poll status
    if (epPollingInterval) clearInterval(epPollingInterval);
    epPollingInterval = setInterval(pollEndpointDownloadStatus, 1500);
  } catch (err) {
    console.error("Failed to trigger batch endpoint download:", err);
    if (btn) btn.disabled = false;
  }
}

async function pollEndpointDownloadStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/endpoints/download/status`);
    const data = await res.json();

    const banner = document.getElementById("ep-download-card");
    const fill = document.getElementById("ep-download-progress-fill");
    const pctBadge = document.getElementById("ep-download-percent-badge");
    const stBadge = document.getElementById("ep-download-status-badge");
    const countEl = document.getElementById("ep-progress-count");
    const currEl = document.getElementById("ep-progress-current");
    const succEl = document.getElementById("ep-progress-succeeded");
    const otherEl = document.getElementById("ep-progress-other");

    const pct = data.percent || 0.0;
    if (fill) fill.style.width = `${pct}%`;
    if (pctBadge) pctBadge.innerText = `${pct.toFixed(1)}%`;
    if (countEl) countEl.innerText = `${data.current_index || 0} / ${data.total || 138}`;
    if (currEl) currEl.innerText = data.current_endpoint || "-";
    if (succEl) succEl.innerText = data.succeeded || 0;
    if (otherEl) otherEl.innerText = (data.empty || 0) + (data.deprecated || 0);

    if (!data.is_running) {
      clearInterval(epPollingInterval);
      epPollingInterval = null;
      if (stBadge) {
        stBadge.innerText = "Completed!";
        stBadge.className = "badge badge-done";
      }
      const btn = document.getElementById("btn-download-all-ep");
      if (btn) btn.disabled = false;
      await loadEndpointsData();
    }
  } catch (err) {
    console.error("Error polling download status:", err);
  }
}

// Expose helper on window
window.app = {
  setPlayerComparison,
  setTeamComparison,
  viewEndpointDetail,
  downloadSingleEndpoint,
  toggleLiveDemo,
  toggleLiveScheduler,
  openLiveGameModal,
  fetchAndRenderLiveScores,
};

// ==========================================================================
// Real-time Live Scores Ticker & Game Detail Controller
// ==========================================================================

let isLiveDemoMode = false;
let livePollingInterval = null;
let currentActiveGame = null;

function initLiveTicker() {
  const track = document.getElementById("live-ticker-track");
  const scrollLeftBtn = document.getElementById("ticker-arrow-left");
  const scrollRightBtn = document.getElementById("ticker-arrow-right");
  const refreshBtn = document.getElementById("btn-live-refresh");
  const schedulerBtn = document.getElementById("btn-live-scheduler");
  const demoBtn = document.getElementById("btn-live-demo");

  // Scroll arrows
  if (scrollLeftBtn && track) {
    scrollLeftBtn.addEventListener("click", () => {
      track.scrollBy({ left: -220, behavior: "smooth" });
    });
  }
  if (scrollRightBtn && track) {
    scrollRightBtn.addEventListener("click", () => {
      track.scrollBy({ left: 220, behavior: "smooth" });
    });
  }

  // Refresh button
  if (refreshBtn) {
    refreshBtn.addEventListener("click", async () => {
      const icon = refreshBtn.querySelector("i");
      if (icon) icon.classList.add("fa-spin");
      try {
        await fetch(`${API_BASE}/api/live/refresh`, { method: "POST" });
        await fetchAndRenderLiveScores(true);
      } finally {
        setTimeout(() => {
          if (icon) icon.classList.remove("fa-spin");
        }, 600);
      }
    });
  }

  // Scheduler Daemon Toggle
  if (schedulerBtn) {
    schedulerBtn.addEventListener("click", toggleLiveScheduler);
  }

  // Demo Mode Toggle
  if (demoBtn) {
    demoBtn.addEventListener("click", toggleLiveDemo);
  }

  // Modal events
  const closeModalBtn = document.getElementById("btn-close-live-modal");
  const modalOverlay = document.getElementById("live-game-modal");
  if (closeModalBtn) {
    closeModalBtn.addEventListener("click", closeLiveGameModal);
  }
  if (modalOverlay) {
    modalOverlay.addEventListener("click", (e) => {
      if (e.target === modalOverlay) closeLiveGameModal();
    });
  }

  // Modal tabs
  const tabBoxscore = document.getElementById("btn-tab-boxscore");
  const tabPbp = document.getElementById("btn-tab-pbp");
  if (tabBoxscore && tabPbp) {
    tabBoxscore.addEventListener("click", () => switchLiveModalTab("boxscore"));
    tabPbp.addEventListener("click", () => switchLiveModalTab("pbp"));
  }

  // Initial load
  checkLiveSchedulerStatus();
  fetchAndRenderLiveScores();

  // Polling loop (adjusts cadence if live games exist)
  startLivePolling(20000);
}

function startLivePolling(ms = 20000) {
  if (livePollingInterval) clearInterval(livePollingInterval);
  livePollingInterval = setInterval(() => {
    fetchAndRenderLiveScores();
  }, ms);
}

async function checkLiveSchedulerStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/live/scheduler`);
    const data = await res.json();
    updateSchedulerUI(data.is_running, data.current_interval_seconds);
  } catch (err) {
    console.debug("Failed checking scheduler status:", err);
  }
}

function updateSchedulerUI(isRunning, interval) {
  const schedulerBtn = document.getElementById("btn-live-scheduler");
  const badgeText = document.getElementById("scheduler-badge-text");
  if (!schedulerBtn || !badgeText) return;

  if (isRunning) {
    schedulerBtn.classList.add("active");
    badgeText.innerText = `Daemon: ON (${interval || 20}s)`;
  } else {
    schedulerBtn.classList.remove("active");
    badgeText.innerText = "Daemon: OFF";
  }
}

async function toggleLiveScheduler() {
  const schedulerBtn = document.getElementById("btn-live-scheduler");
  const isCurrentlyActive = schedulerBtn && schedulerBtn.classList.contains("active");
  const action = isCurrentlyActive ? "stop" : "start";

  try {
    const res = await fetch(`${API_BASE}/api/live/scheduler/${action}`, { method: "POST" });
    const data = await res.json();
    const sched = data.scheduler || {};
    updateSchedulerUI(sched.is_running, sched.current_interval_seconds);
  } catch (err) {
    console.error("Failed toggling scheduler:", err);
  }
}

function toggleLiveDemo() {
  isLiveDemoMode = !isLiveDemoMode;
  const demoBtn = document.getElementById("btn-live-demo");
  const demoText = document.getElementById("demo-badge-text");

  if (isLiveDemoMode) {
    if (demoBtn) demoBtn.classList.add("demo-active");
    if (demoText) demoText.innerText = "Demo: ON";
  } else {
    if (demoBtn) demoBtn.classList.remove("demo-active");
    if (demoText) demoText.innerText = "Demo";
  }
  fetchAndRenderLiveScores(true);
}

async function fetchAndRenderLiveScores(forceRefresh = false) {
  try {
    const params = new URLSearchParams();
    if (forceRefresh) params.set("refresh", "1");
    if (isLiveDemoMode) params.set("demo", "1");

    const url = `${API_BASE}/api/live/scores${params.toString() ? "?" + params.toString() : ""}`;
    const res = await fetch(url);
    const data = await res.json();

    renderLiveTicker(data);

    // If modal is open for a live game, refresh modal details
    if (currentActiveGame && document.getElementById("live-game-modal") && document.getElementById("live-game-modal").style.display !== "none") {
      const updated = (data.games || []).find(g => g.game_id === currentActiveGame.game_id);
      if (updated) {
        currentActiveGame = updated;
        renderLiveModalHeader(updated);
      }
    }
  } catch (err) {
    console.error("Failed fetching live scores:", err);
  }
}

function renderLiveTicker(data) {
  const track = document.getElementById("live-ticker-track");
  const dot = document.getElementById("live-indicator-dot");
  const label = document.getElementById("live-indicator-label");
  if (!track) return;

  const games = data.games || [];
  const liveCount = data.live_games_count || 0;

  // Indicator pulse
  if (liveCount > 0) {
    if (dot) dot.className = "live-indicator-dot live-active";
    if (label) label.innerText = `LIVE (${liveCount})`;
  } else {
    if (dot) dot.className = "live-indicator-dot";
    if (label) label.innerText = "NBA LIVE";
  }

  if (games.length === 0) {
    track.innerHTML = `
      <div class="live-ticker-empty">
        <i class="fa-regular fa-calendar"></i>
        <span>No games currently live (Offseason)</span>
        <button class="live-tool-btn demo-active ml-2" onclick="window.app.toggleLiveDemo()" style="padding:0.2rem 0.5rem; font-size:0.7rem;">
          <i class="fa-solid fa-flask"></i> Enable Demo Feed
        </button>
      </div>
    `;
    return;
  }

  track.innerHTML = games.map(g => {
    const isLive = g.game_status === 2;
    const isUpcoming = g.game_status === 1;
    const isFinal = g.game_status === 3;

    let statusClass = "status-final";
    let statusText = g.game_status_text || "Final";
    if (isLive) {
      statusClass = "status-live";
      statusText = `LIVE ${g.game_clock || ""} ${g.period ? "Q" + g.period : ""}`.trim();
    } else if (isUpcoming) {
      statusClass = "status-upcoming";
      statusText = g.game_status_text || "Upcoming";
    }

    const homeScore = parseInt(g.home_team.score || 0, 10);
    const awayScore = parseInt(g.away_team.score || 0, 10);
    const awayLeading = awayScore > homeScore;
    const homeLeading = homeScore > awayScore;

    let leaderSnippet = "";
    if (g.game_leaders) {
      const hl = g.game_leaders.homeLeaders;
      const al = g.game_leaders.awayLeaders;
      if (hl && hl.name && al && al.name) {
        leaderSnippet = `<div class="live-card-leader" title="${escapeHtml(al.name)} ${al.points}p / ${escapeHtml(hl.name)} ${hl.points}p"><i class="fa-solid fa-bolt"></i> ${escapeHtml(al.name.split(' ').pop())} ${al.points}p • ${escapeHtml(hl.name.split(' ').pop())} ${hl.points}p</div>`;
      }
    }

    return `
      <div class="live-game-card ${isLive ? 'card-is-live' : ''}" data-game-id="${escapeHtml(g.game_id)}">
        <div class="live-card-top">
          <span class="live-status-pill ${statusClass}">${escapeHtml(statusText)}</span>
          ${isLive ? '<i class="fa-solid fa-satellite-dish text-red" style="font-size:0.7rem;"></i>' : ''}
        </div>
        <div class="live-card-teams">
          <div class="live-team-row ${awayLeading ? 'leading' : ''}">
            <span class="live-team-name">${escapeHtml(g.away_team.tricode || 'AWAY')}</span>
            <span class="live-team-score">${awayScore}</span>
          </div>
          <div class="live-team-row ${homeLeading ? 'leading' : ''}">
            <span class="live-team-name">${escapeHtml(g.home_team.tricode || 'HOME')}</span>
            <span class="live-team-score">${homeScore}</span>
          </div>
        </div>
        ${leaderSnippet}
      </div>
    `;
  }).join("");

  // Attach card click handlers
  track.querySelectorAll(".live-game-card").forEach(card => {
    card.addEventListener("click", () => {
      const gid = card.dataset.gameId;
      const selected = games.find(g => g.game_id === gid);
      if (selected) openLiveGameModal(selected);
    });
  });
}

function openLiveGameModal(game) {
  currentActiveGame = game;
  const modal = document.getElementById("live-game-modal");
  if (!modal) return;

  renderLiveModalHeader(game);
  switchLiveModalTab("boxscore");
  loadLiveGameBoxscore(game.game_id);

  modal.style.display = "flex";
}

function renderLiveModalHeader(game) {
  const title = document.getElementById("modal-live-title");
  const stBadge = document.getElementById("modal-live-status-badge");
  const clkBadge = document.getElementById("modal-live-clock-badge");
  const banner = document.getElementById("modal-live-banner");
  const leadersContainer = document.getElementById("modal-live-leaders");

  const isLive = game.game_status === 2;
  const awayScore = game.away_team.score || 0;
  const homeScore = game.home_team.score || 0;

  if (title) title.innerText = `${game.away_team.tricode || 'AWAY'} vs ${game.home_team.tricode || 'HOME'}`;

  if (stBadge) {
    stBadge.innerText = game.game_status_text || (isLive ? "LIVE" : "Finished");
    stBadge.className = isLive ? "badge badge-accent" : "badge";
  }

  if (clkBadge) {
    clkBadge.innerText = game.game_clock ? `Clock: ${game.game_clock}` : (game.period ? `Period: Q${game.period}` : "");
    clkBadge.style.display = clkBadge.innerText ? "inline-block" : "none";
  }

  if (banner) {
    banner.innerHTML = `
      <div class="live-banner-team">
        <span class="team-tricode">${escapeHtml(game.away_team.tricode || '')}</span>
        <span class="team-city">${escapeHtml(game.away_team.team_name || '')}</span>
        <span class="live-banner-score">${awayScore}</span>
      </div>
      <div class="live-banner-center">
        <span class="live-banner-status ${isLive ? 'text-red' : ''}">
          ${isLive ? '<i class="fa-solid fa-circle-dot"></i> ' : ''}${escapeHtml(game.game_status_text || '')}
        </span>
        <span class="live-banner-clock">${escapeHtml(game.game_clock || '')}</span>
      </div>
      <div class="live-banner-team">
        <span class="team-tricode">${escapeHtml(game.home_team.tricode || '')}</span>
        <span class="team-city">${escapeHtml(game.home_team.team_name || '')}</span>
        <span class="live-banner-score">${homeScore}</span>
      </div>
    `;
  }

  // Leaders
  if (leadersContainer) {
    if (game.game_leaders && (game.game_leaders.homeLeaders || game.game_leaders.awayLeaders)) {
      const hl = game.game_leaders.homeLeaders || {};
      const al = game.game_leaders.awayLeaders || {};
      leadersContainer.innerHTML = `
        <div class="live-leader-box">
          <div>
            <div class="live-leader-name">${escapeHtml(al.name || 'Away Leader')}</div>
            <div class="live-leader-team">${escapeHtml(game.away_team.tricode || '')} Leader</div>
          </div>
          <div class="live-leader-stats">${al.points || 0} PTS • ${al.rebounds || 0} REB • ${al.assists || 0} AST</div>
        </div>
        <div class="live-leader-box">
          <div>
            <div class="live-leader-name">${escapeHtml(hl.name || 'Home Leader')}</div>
            <div class="live-leader-team">${escapeHtml(game.home_team.tricode || '')} Leader</div>
          </div>
          <div class="live-leader-stats">${hl.points || 0} PTS • ${hl.rebounds || 0} REB • ${hl.assists || 0} AST</div>
        </div>
      `;
      leadersContainer.style.display = "grid";
    } else {
      leadersContainer.style.display = "none";
    }
  }
}

function closeLiveGameModal() {
  const modal = document.getElementById("live-game-modal");
  if (modal) modal.style.display = "none";
  currentActiveGame = null;
}

function switchLiveModalTab(tab) {
  const tabBox = document.getElementById("btn-tab-boxscore");
  const tabPbp = document.getElementById("btn-tab-pbp");
  const paneBox = document.getElementById("live-modal-boxscore-pane");
  const panePbp = document.getElementById("live-modal-pbp-pane");

  if (tab === "boxscore") {
    if (tabBox) tabBox.classList.add("active");
    if (tabPbp) tabPbp.classList.remove("active");
    if (paneBox) paneBox.style.display = "block";
    if (panePbp) panePbp.style.display = "none";
  } else {
    if (tabBox) tabBox.classList.remove("active");
    if (tabPbp) tabPbp.classList.add("active");
    if (paneBox) paneBox.style.display = "none";
    if (panePbp) panePbp.style.display = "block";
    if (currentActiveGame) {
      loadLiveGamePbp(currentActiveGame.game_id);
    }
  }
}

async function loadLiveGameBoxscore(gameId) {
  const tbody = document.getElementById("live-modal-boxscore-tbody");
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="11" class="text-center py-4"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading live boxscore...</td></tr>`;

  try {
    const res = await fetch(`${API_BASE}/api/live/game/${gameId}`);
    const data = await res.json();

    const gameObj = data.game || {};
    const homePlayers = (gameObj.homeTeam && gameObj.homeTeam.players) || [];
    const awayPlayers = (gameObj.awayTeam && gameObj.awayTeam.players) || [];
    const allPlayers = [
      ...awayPlayers.map(p => ({ ...p, teamTricode: (gameObj.awayTeam && gameObj.awayTeam.teamTricode) || 'AWAY' })),
      ...homePlayers.map(p => ({ ...p, teamTricode: (gameObj.homeTeam && gameObj.homeTeam.teamTricode) || 'HOME' }))
    ];

    if (allPlayers.length === 0) {
      // If demo or empty live boxscore, show demo rows if in demo mode
      if (isLiveDemoMode || (currentActiveGame && currentActiveGame.is_demo)) {
        renderDemoBoxscore(tbody);
        return;
      }
      tbody.innerHTML = `<tr><td colspan="11" class="text-center py-3 text-secondary">No player boxscore records available for this game state.</td></tr>`;
      return;
    }

    tbody.innerHTML = allPlayers.map(p => {
      const stats = p.statistics || {};
      const min = stats.minutes ? stats.minutes.replace("PT", "").replace("M", ":").replace("S", "") : "0:00";
      return `
        <tr>
          <td><strong>${escapeHtml(p.name || p.familyName || 'Player')}</strong> <span class="text-muted" style="font-size:0.75rem;">#${p.jerseyNum || ''}</span></td>
          <td><span class="badge badge-outline">${escapeHtml(p.teamTricode)}</span></td>
          <td>${escapeHtml(p.position || '-')}</td>
          <td>${min}</td>
          <td><strong>${stats.points || 0}</strong></td>
          <td>${stats.reboundsTotal || 0}</td>
          <td>${stats.assists || 0}</td>
          <td>${stats.fieldGoalsMade || 0}/${stats.fieldGoalsAttempted || 0}</td>
          <td>${stats.threePointersMade || 0}/${stats.threePointersAttempted || 0}</td>
          <td>${stats.freeThrowsMade || 0}/${stats.freeThrowsAttempted || 0}</td>
          <td class="${(stats.plusMinusPoints || 0) > 0 ? 'text-green' : ((stats.plusMinusPoints || 0) < 0 ? 'text-red' : '')}">
            ${(stats.plusMinusPoints || 0) > 0 ? '+' : ''}${stats.plusMinusPoints || 0}
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    console.error("Failed loading live boxscore:", err);
    renderDemoBoxscore(tbody);
  }
}

function renderDemoBoxscore(tbody) {
  const demoPlayers = [
    { name: "Nikola Jokic", team: "DEN", pos: "C", min: "28:15", pts: 29, reb: 13, ast: 11, fg: "12/17", fg3: "1/3", ft: "4/4", pm: "+12" },
    { name: "Jamal Murray", team: "DEN", pos: "G", min: "26:40", pts: 21, reb: 4, ast: 6, fg: "8/15", fg3: "3/7", ft: "2/2", pm: "+8" },
    { name: "LeBron James", team: "LAL", pos: "F", min: "29:10", pts: 21, reb: 8, ast: 5, fg: "9/16", fg3: "1/4", ft: "2/3", pm: "-4" },
    { name: "Anthony Davis", team: "LAL", pos: "F-C", min: "31:00", pts: 17, reb: 9, ast: 2, fg: "6/14", fg3: "0/1", ft: "5/6", pm: "-6" },
  ];

  tbody.innerHTML = demoPlayers.map(p => `
    <tr>
      <td><strong>${escapeHtml(p.name)}</strong></td>
      <td><span class="badge badge-outline">${escapeHtml(p.team)}</span></td>
      <td>${p.pos}</td>
      <td>${p.min}</td>
      <td><strong>${p.pts}</strong></td>
      <td>${p.reb}</td>
      <td>${p.ast}</td>
      <td>${p.fg}</td>
      <td>${p.fg3}</td>
      <td>${p.ft}</td>
      <td class="${p.pm.startsWith('+') ? 'text-green' : 'text-red'}">${p.pm}</td>
    </tr>
  `).join("");
}

async function loadLiveGamePbp(gameId) {
  const timeline = document.getElementById("live-modal-pbp-timeline");
  if (!timeline) return;
  timeline.innerHTML = `<div class="text-center py-4 text-secondary"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading play-by-play actions...</div>`;

  try {
    const res = await fetch(`${API_BASE}/api/live/game/${gameId}/playbyplay`);
    const data = await res.json();
    const actions = (data.game && data.game.actions) || [];

    if (actions.length === 0) {
      if (isLiveDemoMode || (currentActiveGame && currentActiveGame.is_demo)) {
        renderDemoPbp(timeline);
        return;
      }
      timeline.innerHTML = `<div class="text-center py-4 text-secondary">No play-by-play events recorded yet.</div>`;
      return;
    }

    // Show latest actions first
    const reversed = [...actions].reverse();
    timeline.innerHTML = reversed.slice(0, 50).map(act => {
      const isScore = act.isFieldGoal || act.pointsTotal > 0;
      const clock = act.clock ? act.clock.replace("PT", "").replace("M", ":").replace("S", "") : "";
      return `
        <div class="live-pbp-item ${isScore ? 'score-change' : ''}">
          <span class="live-pbp-clock">${escapeHtml(clock)} Q${act.period || 1}</span>
          <span class="live-pbp-score">${act.scoreAway || 0} - ${act.scoreHome || 0}</span>
          <span class="live-pbp-desc">${escapeHtml(act.description || act.subType || 'Play action')}</span>
        </div>
      `;
    }).join("");

  } catch (err) {
    console.error("Failed loading play-by-play:", err);
    renderDemoPbp(timeline);
  }
}

function renderDemoPbp(timeline) {
  const demoPlays = [
    { clock: "04:12 Q3", score: "80 - 87", desc: "Nikola Jokic makes 11-foot floating jump shot (DEN +7)" },
    { clock: "04:35 Q3", score: "80 - 85", desc: "LeBron James defensive rebound" },
    { clock: "04:52 Q3", score: "80 - 85", desc: "Jamal Murray misses 26-foot three point pullup jump shot" },
    { clock: "05:10 Q3", score: "80 - 85", desc: "Anthony Davis makes 6-foot hook shot (LAL)" },
    { clock: "05:28 Q3", score: "78 - 85", desc: "Nikola Jokic bad pass turnover" },
    { clock: "05:45 Q3", score: "78 - 85", desc: "Aaron Gordon cutting dunk assisted by Nikola Jokic" },
  ];

  timeline.innerHTML = demoPlays.map(p => `
    <div class="live-pbp-item score-change">
      <span class="live-pbp-clock">${p.clock}</span>
      <span class="live-pbp-score">${p.score}</span>
      <span class="live-pbp-desc">${escapeHtml(p.desc)}</span>
    </div>
  `).join("");
}


// =========================================================
// AI Chart Studio & Conversational Stats Agent
// =========================================================

// Official NBA Team Color Palette
const NBA_TEAM_COLORS = {
  ATL: { primary: "#E03A3E", secondary: "#C1D32F", name: "Atlanta Hawks" },
  BOS: { primary: "#007A33", secondary: "#BA9653", name: "Boston Celtics" },
  BKN: { primary: "#000000", secondary: "#FFFFFF", name: "Brooklyn Nets" },
  CHA: { primary: "#1D1160", secondary: "#00788C", name: "Charlotte Hornets" },
  CHI: { primary: "#CE1141", secondary: "#000000", name: "Chicago Bulls" },
  CLE: { primary: "#860038", secondary: "#041E42", name: "Cleveland Cavaliers" },
  DAL: { primary: "#00538C", secondary: "#002B5E", name: "Dallas Mavericks" },
  DEN: { primary: "#0E2240", secondary: "#FEC524", name: "Denver Nuggets" },
  DET: { primary: "#1D428A", secondary: "#C8102E", name: "Detroit Pistons" },
  GSW: { primary: "#1D428A", secondary: "#FFC72C", name: "Golden State Warriors" },
  HOU: { primary: "#CE1141", secondary: "#000000", name: "Houston Rockets" },
  IND: { primary: "#002D62", secondary: "#FDBB30", name: "Indiana Pacers" },
  LAC: { primary: "#C8102E", secondary: "#1D428A", name: "LA Clippers" },
  LAL: { primary: "#552583", secondary: "#FDB927", name: "Los Angeles Lakers" },
  MEM: { primary: "#5D76A9", secondary: "#12173F", name: "Memphis Grizzlies" },
  MIA: { primary: "#98002E", secondary: "#F9A01B", name: "Miami Heat" },
  MIL: { primary: "#00471B", secondary: "#EEE1C6", name: "Milwaukee Bucks" },
  MIN: { primary: "#0C2340", secondary: "#236192", name: "Minnesota Timberwolves" },
  NOP: { primary: "#0C2340", secondary: "#C8102E", name: "New Orleans Pelicans" },
  NYK: { primary: "#006BB6", secondary: "#F58426", name: "New York Knicks" },
  OKC: { primary: "#007AC1", secondary: "#EF3B24", name: "Oklahoma City Thunder" },
  ORL: { primary: "#0077C0", secondary: "#C4CED4", name: "Orlando Magic" },
  PHI: { primary: "#006BB6", secondary: "#ED174C", name: "Philadelphia 76ers" },
  PHX: { primary: "#1D1160", secondary: "#E56020", name: "Phoenix Suns" },
  POR: { primary: "#E03A3E", secondary: "#000000", name: "Portland Trail Blazers" },
  SAC: { primary: "#5A2D81", secondary: "#63727A", name: "Sacramento Kings" },
  SAS: { primary: "#C4CED4", secondary: "#000000", name: "San Antonio Spurs" },
  TOR: { primary: "#CE1141", secondary: "#000000", name: "Toronto Raptors" },
  UTA: { primary: "#002B5C", secondary: "#00471B", name: "Utah Jazz" },
  WAS: { primary: "#002B5C", secondary: "#E31837", name: "Washington Wizards" }
};

const DEFAULT_CHART_COLORS = [
  "#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ec4899",
  "#06b6d4", "#f97316", "#a855f7", "#14b8a6", "#6366f1"
];

// Global Studio State
let aiChartInstance = null;
let currentAiChartSpec = null;
let currentAiData = [];
let currentAiSql = "";
let currentAiSort = "none"; // "none" | "desc" | "asc"
let currentAiTypeOverride = "auto";
let aiConversationHistory = [];

function initAIChartStudio() {
  // Restore persisted settings
  const savedKey = localStorage.getItem("nba_ai_gemini_key") || "";
  const savedModel = localStorage.getItem("nba_ai_model") || "gemini-flash-latest";
  const keyInput = document.getElementById("ai-settings-apikey");
  const modelSelect = document.getElementById("ai-settings-model");
  if (keyInput) keyInput.value = savedKey;
  if (modelSelect) modelSelect.value = savedModel;

  // Restore chat history from localStorage
  try {
    const savedChat = localStorage.getItem("nba_ai_chat_history");
    if (savedChat) {
      aiConversationHistory = JSON.parse(savedChat);
      rebuildChatStream();
    }
  } catch (e) {
    aiConversationHistory = [];
  }

  // Load presets
  loadAIPresets();

  // Wire Chat Form Submission
  const chatForm = document.getElementById("ai-chat-form");
  const promptInput = document.getElementById("ai-prompt-input");
  if (chatForm && promptInput) {
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = promptInput.value.trim();
      if (!text) return;
      promptInput.value = "";
      sendAIQuery(text);
    });

    // Submit on Enter (Shift+Enter for new line)
    promptInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event("submit"));
      }
    });
  }

  // Wire Clear Chat Button
  const clearBtn = document.getElementById("btn-clear-chat");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (confirm("Clear conversation history and current chart?")) {
        aiConversationHistory = [];
        localStorage.removeItem("nba_ai_chat_history");
        const stream = document.getElementById("ai-chat-stream");
        if (stream) {
          stream.innerHTML = `
            <div class="ai-msg assistant">
              <div class="ai-msg-avatar"><i class="fa-solid fa-robot"></i></div>
              <div class="ai-msg-body">
                <p><strong>Chat cleared!</strong></p>
                <p>Ask an NBA stats question or pick a prompt chip above to get started.</p>
              </div>
            </div>
          `;
        }
        resetChartDisplay();
      }
    });
  }

  // Wire AI Settings Modal
  const settingsBtn = document.getElementById("btn-ai-settings");
  const settingsModal = document.getElementById("ai-settings-modal");
  const closeSettingsBtn = document.getElementById("btn-close-ai-settings");
  const saveSettingsBtn = document.getElementById("btn-save-ai-settings");
  const testKeyBtn = document.getElementById("btn-test-ai-key");

  if (settingsBtn && settingsModal) {
    settingsBtn.addEventListener("click", () => {
      settingsModal.style.display = "flex";
      const statusRow = document.getElementById("ai-key-status");
      if (statusRow) statusRow.style.display = "none";
    });
  }

  if (closeSettingsBtn && settingsModal) {
    closeSettingsBtn.addEventListener("click", () => {
      settingsModal.style.display = "none";
    });
  }

  if (saveSettingsBtn && settingsModal) {
    saveSettingsBtn.addEventListener("click", () => {
      const keyVal = (document.getElementById("ai-settings-apikey").value || "").trim();
      const modelVal = document.getElementById("ai-settings-model").value;
      localStorage.setItem("nba_ai_gemini_key", keyVal);
      localStorage.setItem("nba_ai_model", modelVal);
      settingsModal.style.display = "none";
      showStudioToast("Settings saved successfully!");
    });
  }

  if (testKeyBtn) {
    testKeyBtn.addEventListener("click", async () => {
      const keyVal = (document.getElementById("ai-settings-apikey").value || "").trim();
      const modelVal = document.getElementById("ai-settings-model").value;
      const statusRow = document.getElementById("ai-key-status");
      if (!statusRow) return;

      statusRow.style.display = "block";
      statusRow.className = "settings-validation-row";
      statusRow.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Validating key with Google Gemini...`;

      try {
        const resp = await fetch(`${API_BASE}/api/chart-agent/validate-key`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ api_key: keyVal, model: modelVal })
        });
        const res = await resp.json();
        if (res.valid) {
          statusRow.className = "settings-validation-row success";
          statusRow.innerHTML = `<i class="fa-solid fa-circle-check"></i> Connection verified! Key is functional.`;
        } else {
          statusRow.className = "settings-validation-row error";
          statusRow.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Validation failed: ${escapeHtml(res.message)}`;
        }
      } catch (err) {
        statusRow.className = "settings-validation-row error";
        statusRow.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Network error connecting to backend.`;
      }
    });
  }

  // Wire Chart Type Switcher Buttons
  const typeSelector = document.getElementById("chart-type-selector");
  if (typeSelector) {
    const typeButtons = typeSelector.querySelectorAll(".type-btn");
    typeButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        typeButtons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentAiTypeOverride = btn.dataset.type;
        if (currentAiChartSpec && currentAiData.length > 0) {
          renderAIChart();
        }
      });
    });
  }

  // Wire Sort Toggle Button
  const sortBtn = document.getElementById("btn-toggle-sort");
  if (sortBtn) {
    sortBtn.addEventListener("click", () => {
      if (currentAiSort === "none") currentAiSort = "desc";
      else if (currentAiSort === "desc") currentAiSort = "asc";
      else currentAiSort = "none";

      sortBtn.classList.toggle("active", currentAiSort !== "none");
      sortBtn.innerHTML = currentAiSort === "asc"
        ? `<i class="fa-solid fa-arrow-up-short-wide"></i> <span>Sort (Asc)</span>`
        : currentAiSort === "desc"
        ? `<i class="fa-solid fa-arrow-down-wide-short"></i> <span>Sort (Desc)</span>`
        : `<i class="fa-solid fa-arrow-down-wide-short"></i> <span>Sort</span>`;

      if (currentAiChartSpec && currentAiData.length > 0) {
        renderAIChart();
      }
    });
  }

  // Wire Export PNG
  const pngBtn = document.getElementById("btn-export-png");
  if (pngBtn) {
    pngBtn.addEventListener("click", exportChartPNG);
  }

  // Wire Export CSV
  const csvBtn = document.getElementById("btn-export-csv");
  if (csvBtn) {
    csvBtn.addEventListener("click", exportDataCSV);
  }

  // Wire Details Tabs (Analysis, Data Table, SQL)
  const detailTabs = document.querySelectorAll(".details-tab-btn");
  const detailPanes = document.querySelectorAll(".ai-pane");
  detailTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      detailTabs.forEach(t => t.classList.remove("active"));
      detailPanes.forEach(p => p.classList.remove("active"));
      tab.classList.add("active");
      const pane = document.getElementById(tab.dataset.pane);
      if (pane) pane.classList.add("active");
    });
  });

  // Wire Copy SQL Button
  const copySqlBtn = document.getElementById("btn-copy-ai-sql");
  if (copySqlBtn) {
    copySqlBtn.addEventListener("click", () => {
      if (!currentAiSql) return;
      navigator.clipboard.writeText(currentAiSql).then(() => {
        copySqlBtn.innerHTML = `<i class="fa-solid fa-check"></i> Copied!`;
        setTimeout(() => {
          copySqlBtn.innerHTML = `<i class="fa-solid fa-copy"></i> Copy SQL`;
        }, 2000);
      });
    });
  }

  // Wire Open in SQL Playground Button
  const openPlaygroundBtn = document.getElementById("btn-open-in-playground");
  if (openPlaygroundBtn) {
    openPlaygroundBtn.addEventListener("click", () => {
      if (!currentAiSql) return;
      const editor = document.getElementById("sql-editor");
      if (editor) editor.value = currentAiSql;
      // Switch to sql-playground tab
      const playgroundNavBtn = document.querySelector('.nav-btn[data-target="sql-playground"]');
      if (playgroundNavBtn) playgroundNavBtn.click();
      const runBtn = document.getElementById("btn-run-sql");
      if (runBtn) runBtn.click();
    });
  }
}

async function loadAIPresets() {
  const container = document.getElementById("ai-preset-chips");
  if (!container) return;

  try {
    const resp = await fetch(`${API_BASE}/api/chart-agent/presets`);
    const presets = await resp.json();
    if (!presets || presets.length === 0) return;

    container.innerHTML = presets.map(p => `
      <button class="ai-preset-chip" data-prompt="${escapeHtml(p.prompt)}" title="${escapeHtml(p.prompt)}">
        <i class="fa-solid fa-chart-line"></i> ${escapeHtml(p.title)}
      </button>
    `).join("");

    container.querySelectorAll(".ai-preset-chip").forEach(btn => {
      btn.addEventListener("click", () => {
        const prompt = btn.dataset.prompt;
        sendAIQuery(prompt, true);
      });
    });
  } catch (err) {
    console.error("Failed loading AI presets:", err);
  }
}

async function sendAIQuery(promptText, isPreset = false) {
  const stream = document.getElementById("ai-chat-stream");
  const sendBtn = document.getElementById("btn-ai-send");
  const statusHint = document.getElementById("ai-status-hint");

  // Append user message
  appendChatMessage("user", promptText);

  // Append loading indicator
  const loadingId = "ai-loading-" + Date.now();
  if (stream) {
    const loadDiv = document.createElement("div");
    loadDiv.id = loadingId;
    loadDiv.className = "ai-msg assistant";
    loadDiv.innerHTML = `
      <div class="ai-msg-avatar"><i class="fa-solid fa-robot fa-spin"></i></div>
      <div class="ai-msg-body">
        <p><i class="fa-solid fa-circle-notch fa-spin"></i> Analyzing NBA database & generating chart...</p>
      </div>
    `;
    stream.appendChild(loadDiv);
    stream.scrollTop = stream.scrollHeight;
  }

  if (sendBtn) sendBtn.disabled = true;
  if (statusHint) statusHint.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Processing query...`;

  const apiKey = localStorage.getItem("nba_ai_gemini_key") || "";
  const model = localStorage.getItem("nba_ai_model") || "gemini-flash-latest";

  try {
    const resp = await fetch(`${API_BASE}/api/chart-agent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: promptText,
        history: aiConversationHistory.slice(-8), // Keep recent context
        api_key: apiKey,
        model: model
      })
    });

    const result = await resp.json();

    // Remove loading indicator
    const loadElem = document.getElementById(loadingId);
    if (loadElem) loadElem.remove();

    if (result.success && result.chartSpec) {
      // Store state
      currentAiChartSpec = result.chartSpec;
      currentAiData = result.data || [];
      currentAiSql = result.sql || result.chartSpec.sqlQuery || "";

      // Add to conversation history
      aiConversationHistory.push({ role: "user", content: promptText });
      aiConversationHistory.push({ role: "model", content: result.narrative || "Chart generated." });
      try {
        localStorage.setItem("nba_ai_chat_history", JSON.stringify(aiConversationHistory));
      } catch (e) {}

      // Append assistant message
      appendChatMessage("assistant", result.narrative, {
        isDemo: result.isDemo,
        demoNotice: result.demoNotice,
        rowCount: currentAiData.length
      });

      // Render chart, table, SQL
      renderAIChart();
      renderAIDataTable(currentAiData);
      renderAISql(currentAiSql);
      renderAINarrative(result.narrative);

    } else {
      // Show error in chat
      appendChatMessage("assistant", null, {
        error: result.error || "Could not generate a chart for this query. Try rephrasing or checking your API key."
      });
    }

  } catch (err) {
    const loadElem = document.getElementById(loadingId);
    if (loadElem) loadElem.remove();
    appendChatMessage("assistant", null, {
      error: `Network error connecting to AI agent: ${err.message}`
    });
  } finally {
    if (sendBtn) sendBtn.disabled = false;
    if (statusHint) statusHint.innerHTML = `<i class="fa-solid fa-sparkles"></i> Powered by Gemini`;
  }
}

function appendChatMessage(role, text, meta = {}) {
  const stream = document.getElementById("ai-chat-stream");
  if (!stream) return;

  const msgDiv = document.createElement("div");
  msgDiv.className = `ai-msg ${role}`;

  const avatarHtml = role === "user"
    ? `<div class="ai-msg-avatar"><i class="fa-solid fa-user"></i></div>`
    : `<div class="ai-msg-avatar"><i class="fa-solid fa-robot"></i></div>`;

  let bodyHtml = "";
  if (role === "user") {
    bodyHtml = `<div class="ai-msg-body">${escapeHtml(text)}</div>`;
  } else {
    if (meta.error) {
      bodyHtml = `
        <div class="ai-msg-body">
          <div class="ai-msg-error">
            <i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(meta.error)}
          </div>
          <p class="ai-msg-hint">Tip: Check if your question matches columns in players, player_season_stats, or team_season_stats.</p>
        </div>
      `;
    } else {
      let demoAlert = "";
      if (meta.isDemo && meta.demoNotice) {
        demoAlert = `<div class="ai-msg-hint" style="color: #f59e0b;"><i class="fa-solid fa-circle-info"></i> ${escapeHtml(meta.demoNotice)}</div>`;
      }
      bodyHtml = `
        <div class="ai-msg-body">
          <p>${escapeHtml(text)}</p>
          ${demoAlert}
          <div class="ai-msg-meta">
            <span><i class="fa-solid fa-table-cells"></i> ${meta.rowCount || 0} rows queried</span>
            <span>&bull;</span>
            <span><i class="fa-solid fa-chart-simple"></i> Chart updated</span>
          </div>
        </div>
      `;
    }
  }

  msgDiv.innerHTML = `${avatarHtml}${bodyHtml}`;
  stream.appendChild(msgDiv);
  stream.scrollTop = stream.scrollHeight;
}

function rebuildChatStream() {
  const stream = document.getElementById("ai-chat-stream");
  if (!stream) return;

  stream.innerHTML = "";
  aiConversationHistory.forEach(msg => {
    appendChatMessage(msg.role === "user" ? "user" : "assistant", msg.content);
  });
}

function renderAIChart() {
  if (!currentAiChartSpec || !currentAiData) return;

  const canvas = document.getElementById("ai-main-chart");
  const emptyState = document.getElementById("ai-chart-empty");
  const titleElem = document.getElementById("ai-chart-title");
  const subtitleElem = document.getElementById("ai-chart-subtitle");
  const typeBadge = document.getElementById("ai-chart-type-badge");

  if (!canvas) return;

  // Hide empty state
  if (emptyState) emptyState.style.display = "none";

  // Update header text
  const spec = currentAiChartSpec;
  if (titleElem) titleElem.textContent = spec.title || "NBA Analytics Chart";
  if (subtitleElem) subtitleElem.textContent = spec.subtitle || "";

  // Determine effective chart type
  let effectiveType = spec.chartType || "bar";
  if (currentAiTypeOverride !== "auto") {
    effectiveType = currentAiTypeOverride;
  }
  if (typeBadge) {
    typeBadge.style.display = "inline-block";
    typeBadge.textContent = effectiveType.toUpperCase();
  }

  // Work with a copy of data for sorting
  let chartData = [...currentAiData];
  const primaryMetric = (spec.metrics && spec.metrics.length > 0) ? spec.metrics[0].key : null;

  if (currentAiSort !== "none" && primaryMetric) {
    chartData.sort((a, b) => {
      const valA = parseFloat(a[primaryMetric]) || 0;
      const valB = parseFloat(b[primaryMetric]) || 0;
      return currentAiSort === "asc" ? valA - valB : valB - valA;
    });
  }

  // Destroy previous Chart instance
  if (aiChartInstance) {
    aiChartInstance.destroy();
    aiChartInstance = null;
  }

  const ctx = canvas.getContext("2d");
  const labelKey = (spec.dimensions && spec.dimensions.labelKey) || "full_name";
  const teamKey = (spec.dimensions && spec.dimensions.teamKey) || "team_abbreviation";
  const groupKey = (spec.dimensions && spec.dimensions.groupKey) || null;

  // Build Chart.js Configuration based on chart type
  let config = null;

  if (effectiveType === "horizontalBar") {
    config = buildBarChartConfig(chartData, spec, labelKey, teamKey, true);
  } else if (effectiveType === "bar") {
    config = buildBarChartConfig(chartData, spec, labelKey, teamKey, false);
  } else if (effectiveType === "line") {
    config = buildLineChartConfig(chartData, spec, labelKey, groupKey);
  } else if (effectiveType === "scatter") {
    config = buildScatterChartConfig(chartData, spec);
  } else if (effectiveType === "radar") {
    config = buildRadarChartConfig(chartData, spec, labelKey);
  } else {
    // Default fallback to bar
    config = buildBarChartConfig(chartData, spec, labelKey, teamKey, false);
  }

  try {
    aiChartInstance = new Chart(ctx, config);
  } catch (err) {
    console.error("Error creating Chart.js instance:", err);
  }
}

function buildBarChartConfig(data, spec, labelKey, teamKey, isHorizontal) {
  const labels = data.map(d => d[labelKey] || "Unknown");
  const metrics = spec.metrics || [{ key: "pts", label: "Points", format: "decimal1", axis: "y" }];

  const datasets = metrics.map((m, idx) => {
    // Color logic: if single metric and teamKey available, color each bar by official NBA team color
    let bgColors;
    let borderColors;

    if (metrics.length === 1 && teamKey) {
      bgColors = data.map(d => {
        const tricode = (d[teamKey] || "").toUpperCase();
        return NBA_TEAM_COLORS[tricode] ? NBA_TEAM_COLORS[tricode].primary : DEFAULT_CHART_COLORS[0];
      });
      borderColors = data.map(d => {
        const tricode = (d[teamKey] || "").toUpperCase();
        return NBA_TEAM_COLORS[tricode] ? NBA_TEAM_COLORS[tricode].secondary : "#ffffff";
      });
    } else {
      const col = DEFAULT_CHART_COLORS[idx % DEFAULT_CHART_COLORS.length];
      bgColors = col;
      borderColors = col;
    }

    const ds = {
      label: m.label || m.key,
      data: data.map(d => parseFloat(d[m.key]) || 0),
      backgroundColor: bgColors,
      borderColor: borderColors,
      borderWidth: 1.5,
      borderRadius: 4
    };

    if (isHorizontal) {
      ds.xAxisID = (m.axis === "y1" || m.axis === "x1") ? "x1" : "x";
    } else {
      ds.yAxisID = (m.axis === "y1") ? "y1" : "y";
    }

    return ds;
  });

  // Check for benchmark lines
  if (spec.benchmarks && spec.benchmarks.length > 0 && !isHorizontal) {
    spec.benchmarks.forEach(bm => {
      datasets.push({
        label: bm.label || "Benchmark",
        data: labels.map(() => bm.value),
        type: "line",
        borderColor: bm.color || "#f59e0b",
        borderWidth: 2,
        borderDash: [6, 6],
        pointRadius: 0,
        fill: false,
        yAxisID: "y"
      });
    });
  }

  let scales = {};
  const hasSecondary = metrics.some(m => m.axis === "y1" || m.axis === "x1");

  if (isHorizontal) {
    scales.y = {
      grid: { color: "rgba(255, 255, 255, 0.05)" },
      ticks: { color: "#94a3b8", font: { size: 11 } }
    };
    scales.x = {
      position: "bottom",
      grid: { color: "rgba(255, 255, 255, 0.05)" },
      ticks: { color: "#94a3b8", font: { size: 11 } }
    };
    if (hasSecondary) {
      scales.x1 = {
        position: "top",
        grid: { drawOnChartArea: false },
        ticks: { color: "#a855f7", font: { size: 11 } }
      };
    }
  } else {
    scales.x = {
      grid: { color: "rgba(255, 255, 255, 0.05)" },
      ticks: { color: "#94a3b8", font: { size: 11 } }
    };
    scales.y = {
      position: "left",
      grid: { color: "rgba(255, 255, 255, 0.05)" },
      ticks: { color: "#94a3b8", font: { size: 11 } }
    };
    if (hasSecondary) {
      scales.y1 = {
        position: "right",
        grid: { drawOnChartArea: false },
        ticks: { color: "#a855f7", font: { size: 11 } }
      };
    }
  }

  return {
    type: "bar",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: isHorizontal ? "y" : "x",
      plugins: {
        legend: {
          display: metrics.length > 1,
          labels: { color: "#cbd5e1", font: { size: 12 } }
        },
        tooltip: {
          backgroundColor: "rgba(15, 23, 42, 0.95)",
          titleColor: "#f8fafc",
          bodyColor: "#cbd5e1",
          borderColor: "rgba(255, 255, 255, 0.1)",
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: (ctx) => {
              const val = ctx.raw;
              const m = metrics[ctx.datasetIndex] || {};
              if (m.format === "percent") return ` ${ctx.dataset.label}: ${val}%`;
              return ` ${ctx.dataset.label}: ${val}`;
            }
          }
        }
      },
      scales: scales
    }
  };
}

function buildLineChartConfig(data, spec, labelKey, groupKey) {
  let labels = [];
  let datasets = [];

  if (groupKey) {
    // Multi-line grouped by entity (e.g. player name)
    const groups = {};
    const labelSet = new Set();

    data.forEach(d => {
      const g = d[groupKey] || "Other";
      const l = d[labelKey] || "";
      labelSet.add(l);
      if (!groups[g]) groups[g] = {};
      const metricKey = (spec.metrics && spec.metrics[0]) ? spec.metrics[0].key : "pts";
      groups[g][l] = parseFloat(d[metricKey]) || 0;
    });

    labels = Array.from(labelSet).sort();

    let colorIdx = 0;
    Object.keys(groups).forEach(g => {
      const col = DEFAULT_CHART_COLORS[colorIdx % DEFAULT_CHART_COLORS.length];
      colorIdx++;
      datasets.push({
        label: g,
        data: labels.map(l => groups[g][l] !== undefined ? groups[g][l] : null),
        borderColor: col,
        backgroundColor: col + "33",
        borderWidth: 2.5,
        tension: 0.3,
        pointRadius: 4,
        pointHoverRadius: 6,
        fill: false
      });
    });

  } else {
    // Single line progression
    labels = data.map(d => d[labelKey] || "");
    const metrics = spec.metrics || [{ key: "pts", label: "Points" }];

    metrics.forEach((m, idx) => {
      const col = DEFAULT_CHART_COLORS[idx % DEFAULT_CHART_COLORS.length];
      datasets.push({
        label: m.label || m.key,
        data: data.map(d => parseFloat(d[m.key]) || 0),
        borderColor: col,
        backgroundColor: col + "22",
        borderWidth: 2.5,
        tension: 0.3,
        pointRadius: 4,
        pointHoverRadius: 6,
        fill: true
      });
    });
  }

  // Benchmark line support
  if (spec.benchmarks && spec.benchmarks.length > 0) {
    spec.benchmarks.forEach(bm => {
      datasets.push({
        label: bm.label || "Benchmark",
        data: labels.map(() => bm.value),
        borderColor: bm.color || "#f59e0b",
        borderWidth: 2,
        borderDash: [6, 6],
        pointRadius: 0,
        fill: false
      });
    });
  }

  return {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          labels: { color: "#cbd5e1", font: { size: 12 } }
        },
        tooltip: {
          backgroundColor: "rgba(15, 23, 42, 0.95)",
          titleColor: "#f8fafc",
          bodyColor: "#cbd5e1",
          borderColor: "rgba(255, 255, 255, 0.1)",
          borderWidth: 1,
          padding: 10
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8", font: { size: 11 } }
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8", font: { size: 11 } }
        }
      }
    }
  };
}

function buildScatterChartConfig(data, spec) {
  const sc = spec.scatterConfig || {};
  const xKey = (sc.xMetric && sc.xMetric.key) || (spec.metrics && spec.metrics[0] ? spec.metrics[0].key : "pace");
  const yKey = (sc.yMetric && sc.yMetric.key) || (spec.metrics && spec.metrics[1] ? spec.metrics[1].key : "net_rating");
  const xLabel = (sc.xMetric && sc.xMetric.label) || xKey.toUpperCase();
  const yLabel = (sc.yMetric && sc.yMetric.label) || yKey.toUpperCase();
  const labelKey = sc.labelKey || (spec.dimensions && spec.dimensions.labelKey) || "full_name";
  const teamKey = sc.teamKey || (spec.dimensions && spec.dimensions.teamKey) || "team_abbreviation";

  const points = data.map(d => {
    const tricode = (d[teamKey] || "").toUpperCase();
    const col = NBA_TEAM_COLORS[tricode] ? NBA_TEAM_COLORS[tricode].primary : "#3b82f6";
    return {
      x: parseFloat(d[xKey]) || 0,
      y: parseFloat(d[yKey]) || 0,
      label: d[labelKey] || d[teamKey] || "Point",
      team: d[teamKey] || "",
      color: col
    };
  });

  return {
    type: "scatter",
    data: {
      datasets: [{
        label: `${xLabel} vs ${yLabel}`,
        data: points,
        backgroundColor: points.map(p => p.color),
        borderColor: "#ffffff",
        borderWidth: 1,
        pointRadius: 7,
        pointHoverRadius: 10
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(15, 23, 42, 0.95)",
          titleColor: "#f8fafc",
          bodyColor: "#cbd5e1",
          borderColor: "rgba(255, 255, 255, 0.1)",
          borderWidth: 1,
          padding: 10,
          callbacks: {
            title: (items) => {
              if (!items.length) return "";
              const pt = items[0].raw;
              return `${pt.label} ${pt.team ? `(${pt.team})` : ''}`;
            },
            label: (ctx) => {
              const pt = ctx.raw;
              return [
                ` ${xLabel}: ${pt.x}`,
                ` ${yLabel}: ${pt.y}`
              ];
            }
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: xLabel, color: "#94a3b8" },
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8" }
        },
        y: {
          title: { display: true, text: yLabel, color: "#94a3b8" },
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8" }
        }
      }
    }
  };
}

function buildRadarChartConfig(data, spec, labelKey) {
  const metrics = spec.metrics || [
    { key: "pts", label: "Points" },
    { key: "reb", label: "Rebounds" },
    { key: "ast", label: "Assists" },
    { key: "stl", label: "Steals" },
    { key: "blk", label: "Blocks" }
  ];

  const labels = metrics.map(m => m.label || m.key);

  const datasets = data.map((d, idx) => {
    const name = d[labelKey] || `Player ${idx + 1}`;
    const tricode = (d["team_abbreviation"] || "").toUpperCase();
    const col = NBA_TEAM_COLORS[tricode]
      ? NBA_TEAM_COLORS[tricode].primary
      : DEFAULT_CHART_COLORS[idx % DEFAULT_CHART_COLORS.length];

    return {
      label: name,
      data: metrics.map(m => parseFloat(d[m.key]) || 0),
      backgroundColor: col + "33",
      borderColor: col,
      borderWidth: 2,
      pointBackgroundColor: col,
      pointRadius: 4,
      pointHoverRadius: 6
    };
  });

  return {
    type: "radar",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          labels: { color: "#cbd5e1", font: { size: 12 } }
        },
        tooltip: {
          backgroundColor: "rgba(15, 23, 42, 0.95)",
          titleColor: "#f8fafc",
          bodyColor: "#cbd5e1",
          borderColor: "rgba(255, 255, 255, 0.1)",
          borderWidth: 1,
          padding: 10
        }
      },
      scales: {
        r: {
          angleLines: { color: "rgba(255, 255, 255, 0.1)" },
          grid: { color: "rgba(255, 255, 255, 0.08)" },
          pointLabels: { color: "#f8fafc", font: { size: 11, weight: "600" } },
          ticks: { color: "#94a3b8", backdropColor: "transparent" }
        }
      }
    }
  };
}

function renderAIDataTable(data) {
  const countBadge = document.getElementById("ai-data-count");
  const thead = document.getElementById("ai-table-thead");
  const tbody = document.getElementById("ai-table-tbody");

  if (!thead || !tbody) return;

  if (countBadge) countBadge.textContent = data ? data.length : 0;

  if (!data || data.length === 0) {
    thead.innerHTML = "";
    tbody.innerHTML = `<tr><td class="text-center text-muted">No data rows returned.</td></tr>`;
    return;
  }

  const columns = Object.keys(data[0]);
  thead.innerHTML = columns.map(c => `<th>${escapeHtml(c)}</th>`).join("");

  tbody.innerHTML = data.map(row => `
    <tr>
      ${columns.map(c => `<td>${row[c] !== null && row[c] !== undefined ? escapeHtml(String(row[c])) : '-'}</td>`).join("")}
    </tr>
  `).join("");
}

function renderAISql(sql) {
  const codeElem = document.getElementById("ai-sql-code");
  if (codeElem) {
    codeElem.textContent = sql || "-- No SQL query generated";
  }
}

function renderAINarrative(narrative) {
  const narrativeElem = document.getElementById("ai-narrative-text");
  if (narrativeElem) {
    narrativeElem.textContent = narrative || "Statistical analysis will appear here.";
  }
}

function resetChartDisplay() {
  if (aiChartInstance) {
    aiChartInstance.destroy();
    aiChartInstance = null;
  }
  currentAiChartSpec = null;
  currentAiData = [];
  currentAiSql = "";

  const emptyState = document.getElementById("ai-chart-empty");
  if (emptyState) emptyState.style.display = "flex";

  const titleElem = document.getElementById("ai-chart-title");
  const subtitleElem = document.getElementById("ai-chart-subtitle");
  const typeBadge = document.getElementById("ai-chart-type-badge");
  if (titleElem) titleElem.textContent = "Select a query or type a prompt to generate a chart";
  if (subtitleElem) subtitleElem.textContent = "Visualizations will render here dynamically";
  if (typeBadge) typeBadge.style.display = "none";

  renderAIDataTable([]);
  renderAISql("");
  renderAINarrative("");
}

function exportChartPNG() {
  if (!aiChartInstance) {
    alert("Please generate a chart before exporting.");
    return;
  }
  const link = document.createElement("a");
  link.download = `nba-chart-${Date.now()}.png`;
  link.href = aiChartInstance.toBase64Image();
  link.click();
}

function exportDataCSV() {
  if (!currentAiData || currentAiData.length === 0) {
    alert("No data available to export.");
    return;
  }

  const columns = Object.keys(currentAiData[0]);
  const headerRow = columns.join(",");
  const dataRows = currentAiData.map(row => {
    return columns.map(c => {
      let val = row[c] !== null && row[c] !== undefined ? String(row[c]) : "";
      if (val.includes(",") || val.includes('"')) {
        val = `"${val.replace(/"/g, '""')}"`;
      }
      return val;
    }).join(",");
  });

  const csvContent = "data:text/csv;charset=utf-8," + [headerRow, ...dataRows].join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `nba-data-${Date.now()}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function showStudioToast(msg) {
  const toast = document.createElement("div");
  toast.style.cssText = `
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #10b981;
    color: #fff;
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 0.88rem;
    font-weight: 600;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
    z-index: 9999;
    animation: fadeIn 0.2s ease;
  `;
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3000);
}

// ==========================================================================
// CAPOLOGY, CONTRACT VALUATION & TRADE MACHINE JAVASCRIPT MODULE
// ==========================================================================

const capState = {
  season: "2023-24",
  activeSubtab: "trade-machine-view",
  allTeams: [],
  teamRosterCache: {},
  tradeTeams: [
    { id: 1, team: "LAL", sendingPlayerIds: [], cashSent: 0 },
    { id: 2, team: "BOS", sendingPlayerIds: [], cashSent: 0 }
  ],
  lastTradeResult: null,
  activeScenarioName: "Official Baseline"
};

function initCapology() {
  const capSeasonSelect = document.getElementById("capology-season-select");
  if (capSeasonSelect) {
    capSeasonSelect.addEventListener("change", (e) => {
      capState.season = e.target.value;
      capState.teamRosterCache = {}; // invalidate cache on season change
      refreshActiveCapSubtab();
    });
  }

  // Subtab Navigation Pills
  const pills = document.querySelectorAll(".cap-pill");
  pills.forEach(pill => {
    pill.addEventListener("click", () => {
      pills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      const targetSubtab = pill.dataset.subtab;
      capState.activeSubtab = targetSubtab;

      document.querySelectorAll(".cap-subtab-pane").forEach(pane => {
        pane.classList.remove("active");
        pane.style.display = "none";
      });

      const activePane = document.getElementById(targetSubtab);
      if (activePane) {
        activePane.classList.add("active");
        activePane.style.display = "block";
      }

      refreshActiveCapSubtab();
    });
  });

  // Load Teams & Initialize Components
  loadCapologyTeams().then(() => {
    initTradeMachine();
    initCapSheets();
    initContractValues();
    initWaiveStretch();
    initScenarioSandbox();
  });
}

function refreshActiveCapSubtab() {
  if (capState.activeSubtab === "trade-machine-view") {
    renderTradeTeamsGrid();
  } else if (capState.activeSubtab === "cap-sheets-view") {
    const teamSelect = document.getElementById("cap-team-select");
    if (teamSelect && teamSelect.value) {
      loadTeamCapSheet(teamSelect.value);
    }
  } else if (capState.activeSubtab === "contract-values-view") {
    loadContractValuation();
  } else if (capState.activeSubtab === "waive-stretch-view") {
    populateWaivePlayerSelect();
  }
}

async function loadCapologyTeams() {
  try {
    const res = await fetch(`/api/capology/teams?season=${capState.season}`);
    const data = await res.json();
    if (data.success && data.teams) {
      capState.allTeams = data.teams;
      // Populate team dropdowns
      const capTeamSelect = document.getElementById("cap-team-select");
      const cvTeamFilter = document.getElementById("cv-team-filter");
      
      if (capTeamSelect) {
        capTeamSelect.innerHTML = capState.allTeams.map(t => 
          `<option value="${t.abbreviation}">${t.abbreviation} - ${t.full_name} (${t.tier})</option>`
        ).join("");
      }
      if (cvTeamFilter) {
        cvTeamFilter.innerHTML = '<option value="">All Teams (League-wide)</option>' + 
          capState.allTeams.map(t => `<option value="${t.abbreviation}">${t.abbreviation} - ${t.full_name}</option>`).join("");
      }
    }
  } catch (err) {
    console.error("Error loading capology teams:", err);
  }
}

async function getTeamRoster(teamAbbr) {
  if (capState.teamRosterCache[teamAbbr]) {
    return capState.teamRosterCache[teamAbbr];
  }
  try {
    const res = await fetch(`/api/capology/team/${teamAbbr}?season=${capState.season}`);
    const data = await res.json();
    if (data.success) {
      capState.teamRosterCache[teamAbbr] = data;
      return data;
    }
  } catch (err) {
    console.error("Error fetching team roster:", err);
  }
  return { contracts: [], cap_sheet: {} };
}

// ==========================================================================
// 1. TRADE MACHINE SUBMODULE
// ==========================================================================

function initTradeMachine() {
  renderTradeTeamsGrid();

  // Add Team Button
  const btnAddTeam = document.getElementById("btn-add-trade-team");
  if (btnAddTeam) {
    btnAddTeam.addEventListener("click", () => {
      if (capState.tradeTeams.length >= 4) {
        showStudioToast("Maximum of 4 teams allowed in a multi-team trade.");
        return;
      }
      const existing = capState.tradeTeams.map(t => t.team);
      const available = capState.allTeams.find(t => !existing.includes(t.abbreviation));
      const newTeam = available ? available.abbreviation : "OKC";
      capState.tradeTeams.push({
        id: Date.now(),
        team: newTeam,
        sendingPlayerIds: [],
        cashSent: 0
      });
      renderTradeTeamsGrid();
    });
  }

  // Run Simulation Button
  const btnRunSim = document.getElementById("btn-run-trade-sim");
  if (btnRunSim) {
    btnRunSim.addEventListener("click", runTradeSimulation);
  }

  // Preset scenarios
  const p1 = document.getElementById("preset-trade-1");
  if (p1) p1.addEventListener("click", () => loadTradePreset(1));
  const p2 = document.getElementById("preset-trade-2");
  if (p2) p2.addEventListener("click", () => loadTradePreset(2));
  const p3 = document.getElementById("preset-trade-3");
  if (p3) p3.addEventListener("click", () => loadTradePreset(3));
  const p4 = document.getElementById("preset-trade-4");
  if (p4) p4.addEventListener("click", () => loadTradePreset(4));
}

async function renderTradeTeamsGrid() {
  const container = document.getElementById("trade-teams-container");
  if (!container) return;

  container.innerHTML = "";

  for (let i = 0; i < capState.tradeTeams.length; i++) {
    const tConfig = capState.tradeTeams[i];
    const teamData = await getTeamRoster(tConfig.team);
    const capSheet = teamData.cap_sheet || {};
    const contracts = teamData.contracts || [];

    const card = document.createElement("div");
    card.className = "trade-team-card";
    card.id = `trade-card-${tConfig.id}`;

    // Options for team select
    const teamOptionsHtml = capState.allTeams.map(t => 
      `<option value="${t.abbreviation}" ${t.abbreviation === tConfig.team ? "selected" : ""}>${t.abbreviation} - ${t.full_name}</option>`
    ).join("");

    // Options for player select (excluding already selected)
    const availablePlayers = contracts.filter(c => !tConfig.sendingPlayerIds.includes(c.player_id));
    const playerOptionsHtml = availablePlayers.map(c => 
      `<option value="${c.player_id}">${c.player_name} ($${(c.cap_hit/1e6).toFixed(2)}M - ${c.contract_type})</option>`
    ).join("");

    // Badge styling
    let tierBadgeClass = "badge-under-cap";
    if (capSheet.tier_code === "SECOND_APRON") tierBadgeClass = "badge-apron-second";
    else if (capSheet.tier_code === "FIRST_APRON") tierBadgeClass = "badge-apron-first";
    else if (capSheet.tier_code === "TAXPAYER") tierBadgeClass = "badge-apron-taxpayer";

    // Sending players list
    const sendingPlayersHtml = tConfig.sendingPlayerIds.map(pid => {
      const p = contracts.find(c => c.player_id === pid) || { player_name: "Player #" + pid, cap_hit: 0 };
      
      // Destination dropdown if > 2 teams
      let destHtml = "";
      if (capState.tradeTeams.length > 2) {
        const otherTeams = capState.tradeTeams.filter(t => t.team !== tConfig.team);
        destHtml = `<select class="dropdown-input dropdown-input-sm trade-dest-select" data-pid="${pid}" style="width: 90px; margin-right: 8px;">
          ${otherTeams.map(ot => `<option value="${ot.team}">${ot.team}</option>`).join("")}
        </select>`;
      }

      return `
        <div class="trade-player-card">
          <div class="trade-player-meta">
            <span class="trade-player-name">${p.player_name}</span>
            <span class="trade-player-salary">$${(p.cap_hit/1e6).toFixed(2)}M Cap Hit</span>
          </div>
          <div style="display: flex; align-items: center;">
            ${destHtml}
            <button class="btn-remove-trade-player" onclick="removeTradePlayer(${tConfig.id}, ${pid})" title="Remove Player">&times;</button>
          </div>
        </div>
      `;
    }).join("");

    const removeTeamBtnHtml = capState.tradeTeams.length > 2 ? 
      `<button class="btn btn-sm btn-outline-danger" onclick="removeTradeTeam(${tConfig.id})" title="Remove Team"><i class="fa-solid fa-trash"></i></button>` : "";

    card.innerHTML = `
      <div class="trade-team-card-header">
        <div style="display: flex; align-items: center; gap: 8px; flex: 1;">
          <select class="dropdown-input" onchange="changeTradeTeam(${tConfig.id}, this.value)" style="font-weight: 700;">
            ${teamOptionsHtml}
          </select>
          <span class="badge ${tierBadgeClass}">${capSheet.tier || "Over Cap"}</span>
        </div>
        ${removeTeamBtnHtml}
      </div>

      <div class="trade-team-metrics" style="font-size: 0.8rem; color: var(--text-secondary); display: flex; justify-content: space-between;">
        <span>Payroll: <strong style="color:#fff;">$${((capSheet.total_payroll || 0)/1e6).toFixed(2)}M</strong></span>
        <span>Tax Bill: <strong style="color:#f87171;">$${((capSheet.tax_bill || 0)/1e6).toFixed(2)}M</strong></span>
      </div>

      <div class="trade-players-section">
        <div style="font-size: 0.8rem; font-weight: 600; margin-bottom: 6px; display: flex; justify-content: space-between;">
          <span>Sending Out (${tConfig.sendingPlayerIds.length} players):</span>
          <span>Salary: $${(tConfig.sendingPlayerIds.reduce((sum, pid) => {
            const p = contracts.find(c => c.player_id === pid);
            return sum + (p ? p.cap_hit : 0);
          }, 0) / 1e6).toFixed(2)}M</span>
        </div>

        <div class="trade-players-list mb-2">
          ${sendingPlayersHtml || '<span class="text-secondary" style="font-size: 0.8rem; text-align: center; margin: auto;">No players added to trade yet</span>'}
        </div>

        <div class="add-player-row" style="display: flex; gap: 6px;">
          <select class="dropdown-input" id="player-select-${tConfig.id}" style="font-size: 0.82rem; flex: 1;">
            <option value="">-- Add Player to Trade --</option>
            ${playerOptionsHtml}
          </select>
          <button class="btn btn-secondary btn-sm" onclick="addTradePlayer(${tConfig.id})"><i class="fa-solid fa-plus"></i></button>
        </div>
      </div>
    `;

    container.appendChild(card);
  }
}

window.changeTradeTeam = function(id, newTeam) {
  const t = capState.tradeTeams.find(item => item.id === id);
  if (t) {
    t.team = newTeam;
    t.sendingPlayerIds = [];
    renderTradeTeamsGrid();
  }
};

window.removeTradeTeam = function(id) {
  capState.tradeTeams = capState.tradeTeams.filter(t => t.id !== id);
  renderTradeTeamsGrid();
};

window.addTradePlayer = function(id) {
  const select = document.getElementById(`player-select-${id}`);
  if (!select || !select.value) return;
  const pid = parseInt(select.value);
  const t = capState.tradeTeams.find(item => item.id === id);
  if (t && !t.sendingPlayerIds.includes(pid)) {
    t.sendingPlayerIds.push(pid);
    renderTradeTeamsGrid();
  }
};

window.removeTradePlayer = function(id, pid) {
  const t = capState.tradeTeams.find(item => item.id === id);
  if (t) {
    t.sendingPlayerIds = t.sendingPlayerIds.filter(p => p !== pid);
    renderTradeTeamsGrid();
  }
};

async function runTradeSimulation() {
  const resultsPanel = document.getElementById("trade-results-panel");
  if (!resultsPanel) return;

  // Build trade payload
  const teamsPayload = {};
  for (const tConfig of capState.tradeTeams) {
    const destinations = {};
    // Check if destination selects exist
    document.querySelectorAll(`.trade-dest-select`).forEach(sel => {
      const pid = parseInt(sel.dataset.pid);
      if (tConfig.sendingPlayerIds.includes(pid)) {
        destinations[pid] = sel.value;
      }
    });

    teamsPayload[tConfig.team] = {
      sending_player_ids: tConfig.sendingPlayerIds,
      cash_sent: tConfig.cashSent || 0.0,
      target_player_destinations: destinations
    };
  }

  resultsPanel.style.display = "block";
  resultsPanel.innerHTML = '<div style="padding: 2rem; text-align: center;"><i class="fa-solid fa-circle-notch fa-spin fa-2x"></i><p class="mt-2">Simulating trade against 2023 CBA rules...</p></div>';

  try {
    const res = await fetch("/api/capology/trade/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ teams: teamsPayload, season: capState.season })
    });
    const data = await res.json();
    capState.lastTradeResult = data;
    renderTradeResults(data);
  } catch (err) {
    resultsPanel.innerHTML = `<div class="trade-result-banner invalid">Failed to evaluate trade: ${err.message}</div>`;
  }
}

function renderTradeResults(res) {
  const resultsPanel = document.getElementById("trade-results-panel");
  if (!resultsPanel) return;

  const isValid = res.is_valid;
  const bannerClass = isValid ? "valid" : "invalid";
  const icon = isValid ? '<i class="fa-solid fa-circle-check fa-2x"></i>' : '<i class="fa-solid fa-triangle-exclamation fa-2x"></i>';
  const statusTitle = isValid ? "100% CBA LEGAL TRADE" : "TRADE FAILS 2023 CBA REGULATIONS";

  // Build per-team cards
  let teamCardsHtml = "";
  for (const [tabbr, tInfo] of Object.entries(res.team_results || {})) {
    const teamValid = tInfo.is_valid;
    const teamBadge = teamValid ? '<span class="badge badge-accent">PASS</span>' : '<span class="badge badge-danger">FAIL</span>';
    
    // Violations
    let violationsHtml = "";
    if (tInfo.violations && tInfo.violations.length > 0) {
      violationsHtml = `
        <div class="trade-violations-list">
          <strong><i class="fa-solid fa-ban"></i> CBA Violations:</strong>
          <ul style="margin: 4px 0 0 16px;">
            ${tInfo.violations.map(v => `<li>${v}</li>`).join("")}
          </ul>
        </div>
      `;
    }

    // Warnings
    let warningsHtml = "";
    if (tInfo.warnings && tInfo.warnings.length > 0) {
      warningsHtml = `
        <div class="trade-warnings-list">
          <strong><i class="fa-solid fa-triangle-exclamation"></i> Notices & Warnings:</strong>
          <ul style="margin: 4px 0 0 16px;">
            ${tInfo.warnings.map(w => `<li>${w}</li>`).join("")}
          </ul>
        </div>
      `;
    }

    // TPE notice
    let tpeHtml = "";
    if (tInfo.generated_tpe > 0) {
      tpeHtml = `<div class="trade-metric-row"><span style="color:#34d399;">🎟️ Generated TPE:</span><strong style="color:#34d399;">+$${(tInfo.generated_tpe/1e6).toFixed(2)}M</strong></div>`;
    }

    teamCardsHtml += `
      <div class="trade-result-team-box">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; margin-bottom: 0.75rem;">
          <h4>${tabbr}</h4>
          ${teamBadge}
        </div>
        <div class="trade-metric-row"><span>Rule Applied:</span><strong>${tInfo.cba_rule_applied}</strong></div>
        <div class="trade-metric-row"><span>Outgoing Salary:</span><strong>$${(tInfo.outgoing_salary/1e6).toFixed(2)}M</strong></div>
        <div class="trade-metric-row"><span>Incoming Salary:</span><strong>$${(tInfo.incoming_salary/1e6).toFixed(2)}M</strong></div>
        <div class="trade-metric-row"><span>Max Allowed Incoming:</span><strong>$${(tInfo.max_allowed_incoming/1e6).toFixed(2)}M</strong></div>
        <div class="trade-metric-row"><span>Net Salary Change:</span><strong style="color: ${tInfo.net_salary_change >= 0 ? '#f87171' : '#34d399'};">${tInfo.net_salary_change >= 0 ? '+' : ''}${(tInfo.net_salary_change/1e6).toFixed(2)}M</strong></div>
        <div class="trade-metric-row"><span>Payroll Impact:</span><span>$${(tInfo.pre_trade_payroll/1e6).toFixed(2)}M &rarr; <strong>$${(tInfo.post_trade_payroll/1e6).toFixed(2)}M</strong></span></div>
        <div class="trade-metric-row"><span>Luxury Tax Bill:</span><span>$${(tInfo.pre_trade_tax/1e6).toFixed(2)}M &rarr; <strong>$${(tInfo.post_trade_tax/1e6).toFixed(2)}M</strong> (${tInfo.tax_difference >= 0 ? '+' : ''}$${(tInfo.tax_difference/1e6).toFixed(2)}M)</span></div>
        <div class="trade-metric-row"><span>Apron Tier:</span><span>${tInfo.pre_trade_tier} &rarr; <strong>${tInfo.post_trade_tier}</strong></span></div>
        <div class="trade-metric-row"><span>Roster Size:</span><span>${tInfo.pre_roster_count} &rarr; <strong>${tInfo.post_roster_count} / 15</strong></span></div>
        ${tpeHtml}
        ${violationsHtml}
        ${warningsHtml}
      </div>
    `;
  }

  // Action buttons at bottom of results
  let commitBtnHtml = "";
  if (isValid) {
    commitBtnHtml = `
      <div style="margin-top: 1.5rem; text-align: right; display: flex; justify-content: flex-end; gap: 10px;">
        <button class="btn btn-secondary" onclick="openSaveScenarioModal()"><i class="fa-solid fa-floppy-disk"></i> Save as Scenario</button>
        <button class="btn btn-warning" onclick="commitTradeToActive()"><i class="fa-solid fa-bolt"></i> Commit Trade to Active Rosters</button>
      </div>
    `;
  }

  resultsPanel.innerHTML = `
    <div class="trade-result-banner ${bannerClass}">
      <div style="display: flex; align-items: center; gap: 1rem;">
        ${icon}
        <div>
          <h3 style="margin: 0; font-size: 1.25rem;">${statusTitle}</h3>
          <p style="margin: 4px 0 0; font-size: 0.88rem;">${res.summary}</p>
        </div>
      </div>
    </div>
    <div class="trade-result-teams-grid">
      ${teamCardsHtml}
    </div>
    ${commitBtnHtml}
  `;
}

async function loadTradePreset(presetNum) {
  if (presetNum === 1) {
    // Lakers & Celtics Star Trade
    capState.tradeTeams = [
      { id: 1, team: "LAL", sendingPlayerIds: [1629060], cashSent: 0 }, // Rui Hachimura $15.7M
      { id: 2, team: "BOS", sendingPlayerIds: [1628401], cashSent: 0 }  // Derrick White $18.3M
    ];
  } else if (presetNum === 2) {
    // Warriors 2nd apron aggregation violation (Illegal)
    capState.tradeTeams = [
      { id: 1, team: "GSW", sendingPlayerIds: [202691, 101108], cashSent: 0 }, // Klay + CP3 bundled for star
      { id: 2, team: "MIA", sendingPlayerIds: [202710], cashSent: 0 }          // Jimmy Butler $45M
    ];
  } else if (presetNum === 3) {
    // Spurs cap space absorption
    capState.tradeTeams = [
      { id: 1, team: "SAS", sendingPlayerIds: [1630170], cashSent: 0 }, // Vassell
      { id: 2, team: "UTA", sendingPlayerIds: [1628378], cashSent: 0 }  // John Collins
    ];
  } else if (presetNum === 4) {
    // 3-team trade: LAL, BOS, OKC
    capState.tradeTeams = [
      { id: 1, team: "LAL", sendingPlayerIds: [1629636], cashSent: 0 }, // Austin Reaves
      { id: 2, team: "BOS", sendingPlayerIds: [1630202], cashSent: 0 }, // Payton Pritchard
      { id: 3, team: "OKC", sendingPlayerIds: [1630598], cashSent: 0 }  // Aaron Wiggins
    ];
  }
  renderTradeTeamsGrid();
  setTimeout(runTradeSimulation, 400);
}

window.commitTradeToActive = async function() {
  if (!capState.lastTradeResult || !capState.lastTradeResult.is_valid) {
    showStudioToast("Cannot commit an invalid trade.");
    return;
  }
  try {
    const res = await fetch("/api/capology/scenarios/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        trade_result: capState.lastTradeResult,
        season: capState.season
      })
    });
    const data = await res.json();
    if (data.success) {
      showStudioToast("Trade successfully committed to active rosters!");
      capState.teamRosterCache = {};
      capState.activeScenarioName = "Custom Trade Applied";
      updateScenarioStatusBadge();
      renderTradeTeamsGrid();
      // Reset sending lists
      capState.tradeTeams.forEach(t => t.sendingPlayerIds = []);
      const resultsPanel = document.getElementById("trade-results-panel");
      if (resultsPanel) resultsPanel.style.display = "none";
    } else {
      alert("Error applying trade: " + (data.error || "Unknown error"));
    }
  } catch (err) {
    alert("Error applying trade: " + err.message);
  }
};

// ==========================================================================
// 2. TEAM CAP SHEETS & TAX METERS SUBMODULE
// ==========================================================================

function initCapSheets() {
  const teamSelect = document.getElementById("cap-team-select");
  if (teamSelect) {
    teamSelect.addEventListener("change", (e) => {
      loadTeamCapSheet(e.target.value);
    });
  }
  // Load initial team
  if (capState.allTeams.length > 0) {
    loadTeamCapSheet(capState.allTeams[0].abbreviation);
  } else {
    loadTeamCapSheet("BOS");
  }
}

async function loadTeamCapSheet(teamAbbr) {
  try {
    const res = await fetch(`/api/capology/team/${teamAbbr}?season=${capState.season}`);
    const data = await res.json();
    if (!data.success) return;

    const sheet = data.cap_sheet || {};
    const contracts = data.contracts || [];
    const deadMoney = data.dead_money || [];
    const tpes = data.trade_exceptions || [];

    // Update Quick Chips
    const chipsDiv = document.getElementById("team-quick-chips");
    if (chipsDiv) {
      chipsDiv.innerHTML = `
        <span class="badge badge-outline">${sheet.tier || "Over Cap"}</span>
        <span class="badge ${sheet.is_repeater ? 'badge-danger' : 'badge-accent'}">${sheet.is_repeater ? 'Repeater Taxpayer' : 'Standard Rates'}</span>
      `;
    }

    // Update KPIs
    const kpiActive = document.getElementById("kpi-active-payroll");
    if (kpiActive) kpiActive.textContent = `$${((sheet.active_salary || 0)/1e6).toFixed(2)}M`;
    const kpiCapSpace = document.getElementById("kpi-cap-space");
    if (kpiCapSpace) kpiCapSpace.textContent = `$${((sheet.cap_space || 0)/1e6).toFixed(2)}M`;
    const kpiApron2 = document.getElementById("kpi-apron2-room");
    if (kpiApron2) kpiApron2.textContent = `$${((sheet.second_apron_room || 0)/1e6).toFixed(2)}M`;
    const kpiTax = document.getElementById("kpi-tax-bill");
    if (kpiTax) kpiTax.textContent = `$${((sheet.tax_bill || 0)/1e6).toFixed(2)}M`;
    const kpiTotal = document.getElementById("kpi-total-cost");
    if (kpiTotal) kpiTotal.textContent = `$${((sheet.total_team_cost || 0)/1e6).toFixed(2)}M`;

    // Update Cap Meter Visual Bar (Max scale $230M)
    const maxScale = 230000000.0;
    const activePct = Math.min(100, ((sheet.active_salary || 0) / maxScale) * 100);
    const deadPct = Math.min(100 - activePct, ((sheet.dead_money || 0) / maxScale) * 100);

    const fillActive = document.getElementById("cap-fill-active");
    if (fillActive) fillActive.style.width = `${activePct}%`;
    const fillDead = document.getElementById("cap-fill-dead");
    if (fillDead) {
      fillDead.style.left = `${activePct}%`;
      fillDead.style.width = `${deadPct}%`;
    }

    const pointerText = document.getElementById("meter-pointer-text");
    if (pointerText) {
      pointerText.textContent = `Total Payroll: $${((sheet.total_payroll || 0)/1e6).toFixed(2)}M (${sheet.tier})`;
    }

    // Penalties Box
    const penBox = document.getElementById("cap-penalties-box");
    if (penBox) {
      if (sheet.penalties && sheet.penalties.length > 0) {
        penBox.style.display = "block";
        penBox.innerHTML = `
          <strong><i class="fa-solid fa-triangle-exclamation"></i> Active CBA Apron Penalties:</strong>
          <ul style="margin: 6px 0 0 18px;">
            ${sheet.penalties.map(p => `<li>${p}</li>`).join("")}
          </ul>
        `;
      } else {
        penBox.style.display = "none";
      }
    }

    // Contracts Table
    const tbody = document.getElementById("team-contracts-tbody");
    if (tbody) {
      tbody.innerHTML = contracts.map(c => {
        const y23 = c.all_years?.["2023-24"]?.cap_hit ? `$${(c.all_years["2023-24"].cap_hit/1e6).toFixed(2)}M` : "-";
        const y24 = c.all_years?.["2024-25"]?.cap_hit ? `$${(c.all_years["2024-25"].cap_hit/1e6).toFixed(2)}M` : "-";
        const y25 = c.all_years?.["2025-26"]?.cap_hit ? `$${(c.all_years["2025-26"].cap_hit/1e6).toFixed(2)}M` : "-";
        const y26 = c.all_years?.["2026-27"]?.cap_hit ? `$${(c.all_years["2026-27"].cap_hit/1e6).toFixed(2)}M` : "-";
        const opt = c.option_type ? `<span class="badge badge-outline">${c.option_type}</span>` : "-";

        return `
          <tr>
            <td><strong>${c.player_name}</strong></td>
            <td><span class="badge badge-secondary">${c.contract_type}</span></td>
            <td>${y23}</td>
            <td>${y24}</td>
            <td>${y25}</td>
            <td>${y26}</td>
            <td>${opt}</td>
            <td><i class="fa-solid fa-check text-success"></i> Fully Guaranteed</td>
          </tr>
        `;
      }).join("");
    }

    // Dead money table
    const deadTbody = document.getElementById("dead-money-tbody");
    if (deadTbody) {
      if (deadMoney.length > 0) {
        deadTbody.innerHTML = deadMoney.map(dm => `
          <tr>
            <td>${dm.player_name}</td>
            <td>${dm.season}</td>
            <td>$${(dm.amount/1e6).toFixed(2)}M</td>
            <td>${dm.is_stretched ? 'Yes (Stretched)' : 'No'}</td>
          </tr>
        `).join("");
      } else {
        deadTbody.innerHTML = '<tr><td colspan="4" class="text-secondary text-center">No dead money obligations</td></tr>';
      }
    }

    // TPE table
    const tpeTbody = document.getElementById("tpe-tbody");
    if (tpeTbody) {
      if (tpes.length > 0) {
        tpeTbody.innerHTML = tpes.map(t => `
          <tr>
            <td>${t.source_player || 'Trade Surplus'}</td>
            <td><strong style="color: #34d399;">$${(t.amount/1e6).toFixed(2)}M</strong></td>
            <td>${t.expires_date || '1 Year'}</td>
            <td>${t.notes || '-'}</td>
          </tr>
        `).join("");
      } else {
        tpeTbody.innerHTML = '<tr><td colspan="4" class="text-secondary text-center">No active trade exceptions</td></tr>';
      }
    }

  } catch (err) {
    console.error("Error loading team cap sheet:", err);
  }
}

// ==========================================================================
// 3. CONTRACT VALUATION & WAR SUBMODULE
// ==========================================================================

function initContractValues() {
  const teamF = document.getElementById("cv-team-filter");
  const tierF = document.getElementById("cv-tier-filter");
  const sortF = document.getElementById("cv-sort-filter");
  const orderF = document.getElementById("cv-order-filter");

  [teamF, tierF, sortF, orderF].forEach(el => {
    if (el) el.addEventListener("change", loadContractValuation);
  });

  loadContractValuation();
}

async function loadContractValuation() {
  const team = document.getElementById("cv-team-filter")?.value || "";
  const tier = document.getElementById("cv-tier-filter")?.value || "";
  const sort = document.getElementById("cv-sort-filter")?.value || "surplus_value";
  const order = document.getElementById("cv-order-filter")?.value || "desc";

  const tbody = document.getElementById("contract-valuation-tbody");
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading valuation models...</td></tr>';

  try {
    let url = `/api/capology/valuation?season=${capState.season}&sort_by=${sort}&order=${order}&limit=100`;
    if (team) url += `&team=${encodeURIComponent(team)}`;
    if (tier) url += `&tier=${encodeURIComponent(tier)}`;

    const res = await fetch(url);
    const data = await res.json();
    if (!data.success || !data.players) return;

    if (data.players.length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4">No contracts matching filter criteria.</td></tr>';
      return;
    }

    tbody.innerHTML = data.players.map((p, idx) => {
      let tierBadgeClass = "badge-tier-fair";
      if (p.value_tier === "Super Bargain") tierBadgeClass = "badge-tier-super-bargain";
      else if (p.value_tier === "High Surplus Value") tierBadgeClass = "badge-tier-high-surplus";
      else if (p.value_tier === "Overpaid") tierBadgeClass = "badge-tier-overpaid";
      else if (p.value_tier === "Toxic Contract") tierBadgeClass = "badge-tier-toxic";

      const surplusColor = p.surplus_value >= 0 ? "#34d399" : "#f87171";

      return `
        <tr>
          <td>#${idx + 1}</td>
          <td><strong>${p.player_name}</strong></td>
          <td><span class="badge badge-secondary">${p.team_abbreviation}</span></td>
          <td>$${(p.cap_hit/1e6).toFixed(2)}M</td>
          <td>${p.box_lebron ? p.box_lebron.toFixed(2) : '0.00'}</td>
          <td><strong>${p.wins_added ? p.wins_added.toFixed(1) : '0.0'}</strong></td>
          <td>$${(p.fair_market_value/1e6).toFixed(2)}M</td>
          <td><strong style="color: ${surplusColor};">${p.surplus_value >= 0 ? '+' : ''}${(p.surplus_value/1e6).toFixed(2)}M</strong></td>
          <td>${p.roi_pct}%</td>
          <td><span class="${tierBadgeClass}">${p.value_tier}</span></td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    console.error("Error loading contract valuation:", err);
  }
}

// ==========================================================================
// 4. WAIVE & STRETCH CALCULATOR SUBMODULE
// ==========================================================================

function initWaiveStretch() {
  populateWaivePlayerSelect();

  const btnCalc = document.getElementById("btn-calc-stretch");
  if (btnCalc) {
    btnCalc.addEventListener("click", runWaiveStretchCalculation);
  }
}

async function populateWaivePlayerSelect() {
  const select = document.getElementById("ws-player-select");
  if (!select) return;

  try {
    const res = await fetch(`/api/capology/valuation?season=${capState.season}&limit=200`);
    const data = await res.json();
    if (data.success && data.players) {
      select.innerHTML = '<option value="">-- Choose Player --</option>' + 
        data.players.map(p => `<option value="${p.player_id}">${p.player_name} (${p.team_abbreviation}) - $${(p.cap_hit/1e6).toFixed(2)}M</option>`).join("");
    }
  } catch (err) {
    console.error("Error populating waive players:", err);
  }
}

async function runWaiveStretchCalculation() {
  const select = document.getElementById("ws-player-select");
  const seasonSelect = document.getElementById("ws-season-select");
  const resultsBox = document.getElementById("ws-results-box");
  if (!select || !select.value || !resultsBox) {
    showStudioToast("Please select a player to waive and stretch.");
    return;
  }

  const pid = parseInt(select.value);
  const ssn = seasonSelect ? seasonSelect.value : capState.season;

  try {
    const res = await fetch("/api/capology/events/waive-stretch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_id: pid, season: ssn })
    });
    const data = await res.json();
    if (data.success && data.stretch_result) {
      const sr = data.stretch_result;
      resultsBox.style.display = "block";
      resultsBox.innerHTML = `
        <div class="kpi-grid mb-4">
          <div class="kpi-card">
            <div class="kpi-icon orange"><i class="fa-solid fa-money-bill"></i></div>
            <div class="kpi-info">
              <span class="kpi-label">Total Guaranteed Stretched</span>
              <span class="kpi-value">$${(sr.total_guaranteed_stretched/1e6).toFixed(2)}M</span>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-icon blue"><i class="fa-solid fa-calendar-days"></i></div>
            <div class="kpi-info">
              <span class="kpi-label">Stretch Duration (2N + 1)</span>
              <span class="kpi-value">${sr.stretch_seasons_count} Seasons</span>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-icon purple"><i class="fa-solid fa-calculator"></i></div>
            <div class="kpi-info">
              <span class="kpi-label">Annual Dead Cap Hit</span>
              <span class="kpi-value">$${(sr.annual_cap_hit/1e6).toFixed(2)}M / yr</span>
            </div>
          </div>
        </div>

        <h4 class="mb-2"><i class="fa-solid fa-calendar-check"></i> Stretched Dead Money Amortization Schedule:</h4>
        <div class="table-container">
          <table class="data-table">
            <thead><tr><th>Season</th><th>Annual Stretched Dead Cap Charge</th></tr></thead>
            <tbody>
              ${sr.schedule.map(row => `
                <tr>
                  <td><strong>${row.season}</strong></td>
                  <td><strong style="color:#f87171;">$${(row.annual_hit/1e6).toFixed(2)}M</strong></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    }
  } catch (err) {
    resultsBox.innerHTML = `<div class="trade-result-banner invalid">${err.message}</div>`;
  }
}

// ==========================================================================
// 5. SCENARIO SANDBOX SUBMODULE
// ==========================================================================

function initScenarioSandbox() {
  const btnSave = document.getElementById("btn-cap-save-scenario");
  if (btnSave) btnSave.addEventListener("click", openSaveScenarioModal);

  const btnLoad = document.getElementById("btn-cap-load-scenario");
  if (btnLoad) btnLoad.addEventListener("click", openLoadScenarioModal);

  const btnReset = document.getElementById("btn-cap-reset-baseline");
  if (btnReset) btnReset.addEventListener("click", confirmResetToBaseline);

  // Modal Closers
  const closeSave = document.getElementById("btn-close-save-scenario");
  if (closeSave) closeSave.addEventListener("click", () => document.getElementById("save-scenario-modal").style.display = "none");
  const cancelSave = document.getElementById("btn-cancel-save-scenario");
  if (cancelSave) cancelSave.addEventListener("click", () => document.getElementById("save-scenario-modal").style.display = "none");

  const closeLoad = document.getElementById("btn-close-load-scenario");
  if (closeLoad) closeLoad.addEventListener("click", () => document.getElementById("load-scenario-modal").style.display = "none");

  const confirmSave = document.getElementById("btn-confirm-save-scenario");
  if (confirmSave) confirmSave.addEventListener("click", saveCurrentScenario);
}

function updateScenarioStatusBadge() {
  const badge = document.getElementById("scenario-active-text");
  if (badge) badge.textContent = capState.activeScenarioName;
}

function openSaveScenarioModal() {
  const modal = document.getElementById("save-scenario-modal");
  if (modal) modal.style.display = "flex";
}

async function saveCurrentScenario() {
  const nameInput = document.getElementById("scenario-name-input");
  const descInput = document.getElementById("scenario-desc-input");
  const name = nameInput ? nameInput.value.trim() : "Custom Scenario";
  const desc = descInput ? descInput.value.trim() : "";

  if (!name) {
    alert("Please enter a scenario name.");
    return;
  }

  const payload = {
    name: name,
    description: desc,
    state: {
      season: capState.season,
      tradeTeams: capState.tradeTeams,
      lastTradeResult: capState.lastTradeResult
    }
  };

  try {
    const res = await fetch("/api/capology/scenarios/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      showStudioToast(`Scenario '${name}' saved successfully!`);
      capState.activeScenarioName = name;
      updateScenarioStatusBadge();
      document.getElementById("save-scenario-modal").style.display = "none";
    }
  } catch (err) {
    alert("Error saving scenario: " + err.message);
  }
}

async function openLoadScenarioModal() {
  const modal = document.getElementById("load-scenario-modal");
  const tbody = document.getElementById("saved-scenarios-tbody");
  if (!modal || !tbody) return;

  modal.style.display = "flex";
  tbody.innerHTML = '<tr><td colspan="4" class="text-center py-3"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading saved scenarios...</td></tr>';

  try {
    const res = await fetch("/api/capology/scenarios");
    const data = await res.json();
    if (data.success && data.scenarios) {
      if (data.scenarios.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center py-3 text-secondary">No saved scenarios found.</td></tr>';
        return;
      }
      tbody.innerHTML = data.scenarios.map(s => `
        <tr>
          <td><strong>${s.name}</strong></td>
          <td>${s.description || '-'}</td>
          <td>${s.updated_at ? s.updated_at.slice(0, 10) : '-'}</td>
          <td>
            <button class="btn btn-sm btn-primary" onclick="loadSavedScenario('${s.scenario_id}')">Load</button>
            <button class="btn btn-sm btn-outline-danger" onclick="deleteSavedScenario('${s.scenario_id}')"><i class="fa-solid fa-trash"></i></button>
          </td>
        </tr>
      `).join("");
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-danger">Failed to load scenarios: ${err.message}</td></tr>`;
  }
}

window.loadSavedScenario = async function(sid) {
  try {
    const res = await fetch(`/api/capology/scenarios/${sid}`);
    const data = await res.json();
    if (data.success && data.scenario) {
      const scn = data.scenario;
      capState.activeScenarioName = scn.name;
      updateScenarioStatusBadge();
      if (scn.state) {
        if (scn.state.season) capState.season = scn.state.season;
        if (scn.state.tradeTeams) capState.tradeTeams = scn.state.tradeTeams;
      }
      document.getElementById("load-scenario-modal").style.display = "none";
      showStudioToast(`Loaded scenario: ${scn.name}`);
      renderTradeTeamsGrid();
    }
  } catch (err) {
    alert("Error loading scenario: " + err.message);
  }
};

window.deleteSavedScenario = async function(sid) {
  if (!confirm("Are you sure you want to delete this scenario?")) return;
  try {
    const res = await fetch(`/api/capology/scenarios/${sid}`, { method: "DELETE" });
    const data = await res.json();
    if (data.success) {
      showStudioToast("Scenario deleted.");
      openLoadScenarioModal();
    }
  } catch (err) {
    alert("Error deleting scenario: " + err.message);
  }
};

async function confirmResetToBaseline() {
  if (!confirm("Are you sure you want to reset all team rosters, contracts, and cap sheets back to the official baseline?")) {
    return;
  }
  try {
    const res = await fetch("/api/capology/scenarios/reset", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      showStudioToast("Successfully restored official baseline contracts & rosters!");
      capState.teamRosterCache = {};
      capState.activeScenarioName = "Official Baseline";
      updateScenarioStatusBadge();
      refreshActiveCapSubtab();
    }
  } catch (err) {
    alert("Error resetting to baseline: " + err.message);
  }
}


