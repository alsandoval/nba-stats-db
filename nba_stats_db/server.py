"""
server.py - Flask REST API and static web server for NBA Stats Database & Frontend.
"""

import os
import sys
import time
import logging
from typing import Any, Dict
from flask import Flask, jsonify, request, send_from_directory
import pandas as pd

# Ensure UTF-8 output
if sys.stdout.encoding != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .database import NBADatabase
from .queries import NBAQueryHelper
from .ingestion import NBADataIngestor

logger = logging.getLogger(__name__)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
db = NBADatabase()
helper = NBAQueryHelper(db=db)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# --- Static Frontend Serving ---


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


# --- REST API Endpoints ---


@app.route("/api/status", methods=["GET"])
def api_status():
    """Returns database summary, table counts, available seasons, and database file size."""
    counts = db.get_table_counts()
    seasons = helper.get_available_seasons()
    db_size_bytes = os.path.getsize(db.db_path) if os.path.exists(db.db_path) else 0
    db_size_mb = round(db_size_bytes / (1024 * 1024), 2)

    return jsonify(
        {
            "status": "online",
            "db_path": db.db_path,
            "db_size_mb": db_size_mb,
            "table_counts": counts,
            "seasons": seasons,
        }
    )


@app.route("/api/sync-progress", methods=["GET"])
def api_sync_progress():
    """Returns real-time download progress for the 78-year historical dataset."""
    all_seasons = [f"{y}-{str(y+1)[-2:]}" for y in range(2024, 1945, -1)]
    total_seasons = len(all_seasons)

    # Get distinct ingested seasons from player_season_stats or games
    df = db.query_df("SELECT DISTINCT season FROM player_season_stats")
    ingested_set = set(df["season"].tolist()) if not df.empty else set()

    # Determine current/next downloading season
    current_season = None
    for s in all_seasons:
        if s not in ingested_set:
            current_season = s
            break

    counts = db.get_table_counts()
    db_size_bytes = os.path.getsize(db.db_path) if os.path.exists(db.db_path) else 0
    db_size_mb = round(db_size_bytes / (1024 * 1024), 2)

    completed_count = len(ingested_set)
    percent = round((completed_count / total_seasons) * 100, 1)

    season_statuses = []
    for s in all_seasons:
        if s in ingested_set:
            status = "completed"
        elif s == current_season:
            status = "downloading"
        else:
            status = "pending"
        season_statuses.append({"season": s, "status": status})

    return jsonify(
        {
            "total_seasons": total_seasons,
            "completed_count": completed_count,
            "percent": percent,
            "is_complete": completed_count >= total_seasons,
            "current_season": current_season or "Complete",
            "total_games": counts.get("games", 0),
            "total_boxscores": counts.get("player_game_logs", 0),
            "db_size_mb": db_size_mb,
            "seasons": season_statuses,
        }
    )


@app.route("/api/teams", methods=["GET"])
def api_teams():
    """Returns all 30 NBA franchises."""
    sql = "SELECT team_id, full_name, abbreviation, nickname, city, state, year_founded FROM teams ORDER BY full_name ASC"
    df = db.query_df(sql)
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/teams/<team_abbr>", methods=["GET"])
def api_team_detail(team_abbr):
    """Returns team profile, current roster, and season records."""
    season = request.args.get("season", "2023-24")
    abbr = team_abbr.upper()

    team_sql = "SELECT * FROM teams WHERE abbreviation = ?"
    team_df = db.query_df(team_sql, (abbr,))
    if team_df.empty:
        return jsonify({"error": "Team not found"}), 404
    team = team_df.to_dict(orient="records")[0]

    # Team season stats
    stat_sql = "SELECT * FROM team_season_stats WHERE team_id = ? AND season = ?"
    stat_df = db.query_df(stat_sql, (team["team_id"], season))
    team["stats"] = stat_df.to_dict(orient="records")[0] if not stat_df.empty else {}

    # Team advanced stats
    adv_sql = "SELECT * FROM team_advanced_stats WHERE team_id = ? AND season = ?"
    adv_df = db.query_df(adv_sql, (team["team_id"], season))
    team["advanced"] = adv_df.to_dict(orient="records")[0] if not adv_df.empty else {}

    # Roster
    roster_sql = """
    SELECT p.player_id, p.full_name, s.gp, s.pts, s.reb, s.ast, s.min
    FROM player_season_stats s
    JOIN players p ON s.player_id = p.player_id
    WHERE s.team_id = ? AND s.season = ? AND s.season_type = 'Regular Season'
    ORDER BY s.min DESC
    """
    roster_df = db.query_df(roster_sql, (team["team_id"], season))
    team["roster"] = roster_df.to_dict(orient="records")

    return jsonify(team)


@app.route("/api/players/search", methods=["GET"])
def api_player_search():
    """Autocomplete search for players."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    df = helper.search_players(q)
    return jsonify(df.head(20).to_dict(orient="records"))


@app.route("/api/players/<player_name>", methods=["GET"])
def api_player_profile(player_name):
    """Comprehensive profile for a player."""
    profile = helper.get_player_profile(player_name)
    if not profile:
        return jsonify({"error": "Player not found"}), 404
    return jsonify(profile)


@app.route("/api/standings", methods=["GET"])
def api_standings():
    """League standings by season and optional conference."""
    season = request.args.get("season", "2023-24")
    conference = request.args.get("conference", None)
    season_type = request.args.get("season_type", "Regular Season")
    df = helper.get_standings(season=season, conference=conference, season_type=season_type)
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/leaders", methods=["GET"])
def api_leaders():
    """Category leaderboards."""
    category = request.args.get("category", "pts")
    season = request.args.get("season", "2023-24")
    season_type = request.args.get("season_type", "Regular Season")
    limit = int(request.args.get("limit", 15))
    df = helper.get_leaders_by_category(
        category=category, season=season, season_type=season_type, limit=limit
    )
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/games/recent", methods=["GET"])
def api_recent_games():
    """Recent games with scores."""
    limit = int(request.args.get("limit", 15))
    df = helper.get_recent_games(limit=limit)
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/games/<game_id>", methods=["GET"])
def api_game_detail(game_id):
    """Full box score for a single game."""
    # Game info
    g_sql = """
    SELECT g.*, ht.full_name AS home_name, ht.abbreviation AS home_abbr,
                vt.full_name AS away_name, vt.abbreviation AS away_abbr
    FROM games g
    JOIN teams ht ON g.home_team_id = ht.team_id
    JOIN teams vt ON g.visitor_team_id = vt.team_id
    WHERE g.game_id = ?
    """
    gdf = db.query_df(g_sql, (game_id,))
    if gdf.empty:
        return jsonify({"error": "Game not found"}), 404
    game = gdf.to_dict(orient="records")[0]

    # Player logs
    pl_sql = """
    SELECT p.full_name, t.abbreviation AS team, l.*
    FROM player_game_logs l
    JOIN players p ON l.player_id = p.player_id
    JOIN teams t ON l.team_id = t.team_id
    WHERE l.game_id = ?
    ORDER BY l.pts DESC
    """
    pldf = db.query_df(pl_sql, (game_id,))
    game["players"] = pldf.to_dict(orient="records")

    return jsonify(game)


@app.route("/api/compare/players", methods=["GET"])
def api_compare_players():
    """Side-by-side comparison of two players."""
    p1 = request.args.get("player1", "").strip()
    p2 = request.args.get("player2", "").strip()
    season = request.args.get("season", "2023-24")

    if not p1 or not p2:
        return jsonify({"error": "Both player1 and player2 query parameters are required"}), 400

    comp = helper.compare_players(p1, p2, season=season)
    return jsonify(comp)


@app.route("/api/compare/teams", methods=["GET"])
def api_compare_teams():
    """Side-by-side comparison of two teams."""
    t1 = request.args.get("team1", "").strip()
    t2 = request.args.get("team2", "").strip()
    season = request.args.get("season", "2023-24")

    if not t1 or not t2:
        return jsonify({"error": "Both team1 and team2 query parameters are required"}), 400

    comp = helper.compare_teams(t1, t2, season=season)
    return jsonify(comp)


@app.route("/api/query", methods=["POST"])
def api_query():
    """Interactive SQL query execution with safety controls."""
    data = request.get_json() or {}
    sql = data.get("query", "").strip()

    if not sql:
        return jsonify({"error": "SQL query cannot be empty"}), 400

    # Safety check: allow SELECT queries only
    disallowed = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "REPLACE"]
    first_word = sql.split()[0].upper()
    if first_word != "SELECT" and first_word != "WITH":
        return jsonify({"error": "Only SELECT or WITH queries are permitted in playground."}), 400

    for word in disallowed:
        # Check for standalone tokens
        tokens = [t.strip(";").upper() for t in sql.split()]
        if word in tokens:
            return jsonify({"error": f"Disallowed statement keyword '{word}' detected."}), 400

    try:
        start_time = time.time()
        df = helper.execute_sql(sql)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Truncate output if too large
        total_rows = len(df)
        if total_rows > 500:
            df = df.head(500)

        return jsonify(
            {
                "columns": df.columns.tolist(),
                "rows": df.to_dict(orient="records"),
                "total_rows": total_rows,
                "displayed_rows": len(df),
                "duration_ms": duration_ms,
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    """Endpoint to trigger ingestion of an additional season."""
    data = request.get_json() or {}
    season = data.get("season", "2023-24")
    include_playoffs = data.get("include_playoffs", True)

    try:
        ingestor = NBADataIngestor(db=db)
        res = ingestor.ingest_season(season=season, include_playoffs=include_playoffs)
        return jsonify({"status": "success", "result": res, "counts": db.get_table_counts()})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


# --- NBA API Endpoints Catalog & Downloader Routes ---

_endpoint_job = {
    "is_running": False,
    "total": 0,
    "current_index": 0,
    "current_endpoint": None,
    "succeeded": 0,
    "empty": 0,
    "deprecated": 0,
    "error": 0,
    "skipped": 0,
    "percent": 0.0,
    "last_result": None,
}


@app.route("/api/endpoints", methods=["GET"])
def api_endpoints_list():
    """Returns all 138 NBA API endpoints from the database catalog."""
    category = request.args.get("category")
    status = request.args.get("status")
    catalog = db.get_endpoints_catalog(category=category, status=status)

    # Calculate summary metrics
    total = len(catalog)
    succeeded = sum(1 for e in catalog if e.get("status") == "SUCCESS")
    empty = sum(1 for e in catalog if e.get("status") == "EMPTY")
    deprecated = sum(1 for e in catalog if e.get("status") == "DEPRECATED")
    total_rows = sum(e.get("total_rows", 0) for e in catalog)

    return jsonify({
        "total": total,
        "succeeded": succeeded,
        "empty": empty,
        "deprecated": deprecated,
        "total_rows": total_rows,
        "endpoints": catalog,
    })


@app.route("/api/endpoints/<endpoint_name>", methods=["GET"])
def api_endpoint_detail(endpoint_name):
    """Returns full metadata, dataset tables, schema, and preview rows for an endpoint."""
    detail = db.get_endpoint_detail(endpoint_name)
    if not detail:
        return jsonify({"error": f"Endpoint '{endpoint_name}' not found"}), 404
    return jsonify(detail)


@app.route("/api/endpoints/download", methods=["POST"])
def api_endpoints_download():
    """Triggers background download of all endpoints or a filtered subset."""
    global _endpoint_job
    if _endpoint_job["is_running"]:
        return jsonify({"status": "already_running", "job": _endpoint_job})

    data = request.get_json() or {}
    category = data.get("category")
    endpoint_name = data.get("endpoint")
    force = data.get("force", False)
    delay = float(data.get("delay", 0.75))

    from .endpoints_downloader import NBAEndpointDownloader
    import threading

    def run_worker():
        global _endpoint_job
        downloader = NBAEndpointDownloader(db=db)
        _endpoint_job["is_running"] = True
        _endpoint_job["succeeded"] = 0
        _endpoint_job["empty"] = 0
        _endpoint_job["deprecated"] = 0
        _endpoint_job["error"] = 0
        _endpoint_job["skipped"] = 0
        _endpoint_job["current_index"] = 0

        try:
            if endpoint_name:
                _endpoint_job["total"] = 1
                _endpoint_job["current_endpoint"] = endpoint_name
                res = downloader.download_endpoint(endpoint_name, force=force)
                _endpoint_job["current_index"] = 1
                _endpoint_job["percent"] = 100.0
                _endpoint_job["last_result"] = res
                st = res.get("status", "").lower()
                if st == "success":
                    _endpoint_job["succeeded"] = 1
                elif st == "empty":
                    _endpoint_job["empty"] = 1
                elif st == "deprecated":
                    _endpoint_job["deprecated"] = 1
                else:
                    _endpoint_job["error"] = 1
            else:
                cats = [category] if category else None
                targets = [n for n, m in downloader.catalog.items() if not cats or m["category"] in cats]
                _endpoint_job["total"] = len(targets)

                def on_progress(idx, tot, name, res):
                    _endpoint_job["current_index"] = idx
                    _endpoint_job["current_endpoint"] = name
                    _endpoint_job["percent"] = round((idx / tot) * 100, 1)
                    _endpoint_job["last_result"] = res
                    st = res.get("status", "").lower()
                    if st == "success":
                        _endpoint_job["succeeded"] += 1
                    elif st == "empty":
                        _endpoint_job["empty"] += 1
                    elif st == "deprecated":
                        _endpoint_job["deprecated"] += 1
                    elif st == "skipped":
                        _endpoint_job["skipped"] += 1
                    else:
                        _endpoint_job["error"] += 1

                downloader.download_all_endpoints(
                    categories=cats,
                    force=force,
                    delay=delay,
                    on_progress=on_progress,
                )
        except Exception as e:
            logger.error("Endpoint download worker encountered error: %s", e)
        finally:
            _endpoint_job["is_running"] = False

    t = threading.Thread(target=run_worker, daemon=True)
    t.start()

    return jsonify({"status": "started", "category": category, "endpoint": endpoint_name})


@app.route("/api/endpoints/download/status", methods=["GET"])
def api_endpoints_download_status():
    """Returns current status of background endpoint download job."""
    return jsonify(_endpoint_job)


# --- Box LEBRON Predictive Analytics Routes ---

from .box_lebron import BoxLEBRONModel

lebron_model = BoxLEBRONModel(db=db)


@app.route("/api/lebron/leaderboard", methods=["GET"])
def api_lebron_leaderboard():
    """Returns the Box LEBRON leaderboard for a given season and sorting criterion."""
    season = request.args.get("season", "2023-24")
    season_type = request.args.get("season_type", "Regular Season")
    min_minutes = float(request.args.get("min_minutes", 500.0))
    limit = int(request.args.get("limit", 50))
    sort_by = request.args.get("sort_by", "box_lebron")

    df = helper.get_box_lebron_leaderboard(
        season=season,
        season_type=season_type,
        min_minutes=min_minutes,
        limit=limit,
        sort_by=sort_by,
    )
    if df.empty:
        # Automatically compute if missing
        lebron_model.save_season_box_lebron(season=season, season_type=season_type)
        df = helper.get_box_lebron_leaderboard(
            season=season,
            season_type=season_type,
            min_minutes=min_minutes,
            limit=limit,
            sort_by=sort_by,
        )

    return jsonify({
        "season": season,
        "season_type": season_type,
        "sort_by": sort_by,
        "total_players": len(df),
        "leaders": df.to_dict(orient="records"),
    })


@app.route("/api/lebron/player/<int:player_id>", methods=["GET"])
def api_lebron_player(player_id):
    """Returns career Box LEBRON progression for a player."""
    season_type = request.args.get("season_type", "Regular Season")
    df = helper.get_player_box_lebron_history(player_id=player_id, season_type=season_type)
    return jsonify({
        "player_id": player_id,
        "season_type": season_type,
        "history": df.to_dict(orient="records"),
    })


@app.route("/api/lebron/archetypes", methods=["GET"])
def api_lebron_archetypes():
    """Returns archetype breakdown and average Box LEBRON ratings."""
    season = request.args.get("season", "2023-24")
    season_type = request.args.get("season_type", "Regular Season")
    df = helper.get_box_lebron_archetype_distribution(season=season, season_type=season_type)
    return jsonify({
        "season": season,
        "season_type": season_type,
        "archetypes": df.to_dict(orient="records"),
    })


@app.route("/api/lebron/compute", methods=["POST"])
def api_lebron_compute():
    """Triggers computation of Box LEBRON ratings for a season or all seasons."""
    data = request.get_json() or {}
    season = data.get("season", "2023-24")
    compute_all = data.get("all_seasons", False)
    season_type = data.get("season_type", "Regular Season")

    if compute_all:
        results = lebron_model.compute_all_seasons(season_type=season_type)
        return jsonify({"status": "completed", "seasons_computed": len(results), "details": results})
    else:
        cnt = lebron_model.save_season_box_lebron(season=season, season_type=season_type)
        return jsonify({"status": "completed", "season": season, "records_stored": cnt})


@app.route("/api/lebron/train", methods=["POST"])
def api_lebron_train():
    """Triggers ML training on historical data with cross-validation."""
    from .trainer import BoxLEBRONTrainer
    data = request.get_json() or {}
    estimator = data.get("estimator", "ridge")
    cv = int(data.get("cv", 5))
    min_minutes = float(data.get("min_minutes", 400.0))
    recalculate = data.get("recalculate", False)

    trainer = BoxLEBRONTrainer(db=db)
    meta = trainer.train(estimator=estimator, cv=cv, min_minutes=min_minutes)
    trainer.save_model()

    # Reload active model in memory
    lebron_model.load_trained_weights()

    recalc_status = None
    if recalculate:
        recalc_res = lebron_model.compute_all_seasons()
        recalc_status = {"seasons_updated": len(recalc_res)}

    return jsonify({
        "status": "success",
        "model_type": meta["model_type"],
        "sample_size": meta["sample_size"],
        "offensive_metrics": meta["offensive_metrics"],
        "defensive_metrics": meta["defensive_metrics"],
        "offensive_weights": meta["offensive_weights"],
        "defensive_weights": meta["defensive_weights"],
        "recalculation": recalc_status,
    })


@app.route("/api/lebron/model-weights", methods=["GET"])
def api_lebron_model_weights():
    """Returns currently loaded Machine Learning weights and training metadata."""
    if lebron_model.trained_weights:
        return jsonify({"has_trained_weights": True, "weights": lebron_model.trained_weights})
    else:
        return jsonify({
            "has_trained_weights": False,
            "message": "No trained weights file found. Using default calibrated baseline equations.",
        })


# --- Unsupervised Position Clustering & 3D t-SNE Routes ---

from .clustering import PositionClusteringModel

clustering_model = PositionClusteringModel(db=db)


@app.route("/api/clustering/optimal-k", methods=["GET"])
def api_clustering_optimal_k():
    """Returns Silhouette scores and Inertia Elbow curve across k=3..12."""
    season = request.args.get("season", "2023-24")
    season_type = request.args.get("season_type", "Regular Season")
    min_minutes = float(request.args.get("min_minutes", 300.0))
    min_k = int(request.args.get("min_k", 3))
    max_k = int(request.args.get("max_k", 12))

    opt = clustering_model.find_optimal_k(
        k_range=(min_k, max_k), season=season, season_type=season_type, min_minutes=min_minutes
    )
    return jsonify(opt)


@app.route("/api/clustering/3d", methods=["GET"])
def api_clustering_3d():
    """Returns all players with 3D t-SNE coordinates, cluster IDs, and key metrics."""
    season = request.args.get("season", "2023-24")
    season_type = request.args.get("season_type", "Regular Season")
    cluster_id = request.args.get("cluster_id")
    cid = int(cluster_id) if cluster_id is not None else None
    min_minutes = float(request.args.get("min_minutes", 300.0))
    limit = int(request.args.get("limit", 600))

    df = helper.get_position_clusters(
        season=season, season_type=season_type, cluster_id=cid, min_minutes=min_minutes, limit=limit
    )
    if df.empty:
        # Run clustering if not yet computed in database
        clustering_model.fit_clusters(k=8, season=season, season_type=season_type, min_minutes=min_minutes)
        clustering_model.compute_3d_tsne()
        clustering_model.save_to_db()
        df = helper.get_position_clusters(
            season=season, season_type=season_type, cluster_id=cid, min_minutes=min_minutes, limit=limit
        )

    return jsonify({
        "season": season,
        "season_type": season_type,
        "total_players": len(df),
        "players": df.to_dict(orient="records"),
    })


@app.route("/api/clustering/clusters", methods=["GET"])
def api_clustering_clusters():
    """Returns cluster archetype names, descriptions, and centroid metrics."""
    season = request.args.get("season", "2023-24")
    season_type = request.args.get("season_type", "Regular Season")

    df_summaries = helper.get_cluster_summaries(season=season, season_type=season_type)
    if df_summaries.empty:
        clustering_model.fit_clusters(k=8, season=season, season_type=season_type)
        clustering_model.compute_3d_tsne()
        clustering_model.save_to_db()
        df_summaries = helper.get_cluster_summaries(season=season, season_type=season_type)

    return jsonify({
        "season": season,
        "season_type": season_type,
        "total_clusters": len(df_summaries),
        "clusters": df_summaries.to_dict(orient="records"),
        "profiles": clustering_model.cluster_profiles,
    })


@app.route("/api/clustering/run", methods=["POST"])
def api_clustering_run():
    """Triggers K-Means and 3D t-SNE execution with specified parameters."""
    data = request.get_json() or {}
    season = data.get("season", "2023-24")
    season_type = data.get("season_type", "Regular Season")
    k = data.get("k")
    min_minutes = float(data.get("min_minutes", 300.0))
    generate_viz = data.get("generate_viz", True)

    if k is None:
        opt = clustering_model.find_optimal_k(k_range=(4, 10), season=season, season_type=season_type, min_minutes=min_minutes)
        k = opt["optimal_k"]

    df = clustering_model.fit_clusters(k=int(k), season=season, season_type=season_type, min_minutes=min_minutes)
    clustering_model.compute_3d_tsne()
    saved_cnt = clustering_model.save_to_db()

    viz_path = None
    if generate_viz:
        viz_path = os.path.join(STATIC_DIR, "clustering_3d.html")
        clustering_model.generate_3d_plot_html(output_file=viz_path)

    return jsonify({
        "status": "success",
        "season": season,
        "k_clusters": k,
        "players_clustered": saved_cnt,
        "viz_generated": generate_viz,
        "profiles": clustering_model.cluster_profiles,
    })


# --- Live Scores & Real-Time Scheduler Routes ---

from .live_scores import NBALiveService
from .live_scheduler import NBALiveScheduler

live_service = NBALiveService(db=db)
live_scheduler = NBALiveScheduler(db=db)


@app.route("/api/live/scores", methods=["GET"])
def api_live_scores():
    """Returns today's live scores, quarter scores, game clock, and active leaders."""
    refresh = request.args.get("refresh", "0") == "1"
    demo = request.args.get("demo", "0") == "1"

    if refresh:
        raw_data = live_service.fetch_todays_scoreboard()
        live_service.save_live_scoreboard(raw_data)

    cached = live_service.get_cached_scoreboard()

    # If in offseason or no games today, provide demo games if requested
    if demo and cached.get("total_games", 0) == 0:
        demo_games = [
            {
                "game_id": "0022300001",
                "game_code": "20231024/LALDEN",
                "game_status": 2,
                "game_status_text": "Q3 04:12",
                "period": 3,
                "game_clock": "04:12",
                "home_team": {"team_id": 1610612743, "team_name": "Nuggets", "tricode": "DEN", "score": 87},
                "away_team": {"team_id": 1610612747, "team_name": "Lakers", "tricode": "LAL", "score": 80},
                "game_leaders": {
                    "homeLeaders": {"name": "Nikola Jokic", "points": 29, "rebounds": 13, "assists": 11},
                    "awayLeaders": {"name": "LeBron James", "points": 21, "rebounds": 8, "assists": 5}
                },
                "is_demo": True,
                "updated_at": "Live Demo"
            },
            {
                "game_id": "0022300002",
                "game_code": "20231024/PHXGSW",
                "game_status": 1,
                "game_status_text": "10:00 pm ET",
                "period": 0,
                "game_clock": "",
                "home_team": {"team_id": 1610612744, "team_name": "Warriors", "tricode": "GSW", "score": 0},
                "away_team": {"team_id": 1610612756, "team_name": "Suns", "tricode": "PHX", "score": 0},
                "is_demo": True,
                "updated_at": "Live Demo"
            }
        ]
        return jsonify({
            "total_games": len(demo_games),
            "live_games_count": 1,
            "is_offseason_demo": True,
            "scheduler_active": live_scheduler.get_status().get("is_running", False),
            "games": demo_games,
        })

    cached["scheduler_active"] = live_scheduler.get_status().get("is_running", False)
    return jsonify(cached)


@app.route("/api/live/game/<game_id>", methods=["GET"])
def api_live_game_boxscore(game_id):
    """Returns detailed real-time box score for a specific game."""
    boxscore = live_service.fetch_game_boxscore(game_id)
    return jsonify(boxscore)


@app.route("/api/live/game/<game_id>/playbyplay", methods=["GET"])
def api_live_game_playbyplay(game_id):
    """Returns real-time play-by-play actions for a specific game."""
    pbp = live_service.fetch_game_playbyplay(game_id)
    return jsonify(pbp)


@app.route("/api/live/scheduler", methods=["GET"])
def api_live_scheduler_status():
    """Returns the operational status of the live score scheduler."""
    return jsonify(live_scheduler.get_status())


@app.route("/api/live/scheduler/start", methods=["POST"])
def api_live_scheduler_start():
    """Starts the adaptive background live score updater."""
    live_scheduler.start()
    return jsonify({"status": "started", "scheduler": live_scheduler.get_status()})


@app.route("/api/live/scheduler/stop", methods=["POST"])
def api_live_scheduler_stop():
    """Stops the adaptive background live score updater."""
    live_scheduler.stop()
    return jsonify({"status": "stopped", "scheduler": live_scheduler.get_status()})


@app.route("/api/live/refresh", methods=["POST"])
def api_live_refresh():
    """Triggers an immediate poll of the live scoreboard."""
    res = live_scheduler.poll_once()
    return jsonify(res)


# --- AI Chart Studio & Conversational Stats Agent Routes ---

from .ai_agent import NBAAIAgent

ai_agent = NBAAIAgent(db=db)


@app.route("/api/chart-agent", methods=["POST"])
def api_chart_agent():
    """Processes natural language questions into data, Chart DSL, and narrative analysis."""
    payload = request.get_json() or {}
    prompt = payload.get("prompt", "").strip()
    history = payload.get("history", [])
    api_key = payload.get("api_key")
    model = payload.get("model", "gemini-flash-latest")

    if not prompt:
        return jsonify({"success": False, "error": "Prompt cannot be empty."}), 400

    result = ai_agent.process_query(
        prompt=prompt,
        history=history,
        api_key=api_key,
        model=model
    )
    return jsonify(result)


@app.route("/api/chart-agent/presets", methods=["GET"])
def api_chart_agent_presets():
    """Returns curated demo presets for zero-configuration testing."""
    return jsonify(ai_agent.get_presets())


@app.route("/api/chart-agent/validate-key", methods=["POST"])
def api_chart_agent_validate_key():
    """Validates if a provided Gemini API key is functional."""
    payload = request.get_json() or {}
    api_key = payload.get("api_key", "").strip()
    model = payload.get("model", "gemini-flash-latest")

    valid, msg = ai_agent.validate_api_key(api_key=api_key, model=model)
    return jsonify({"valid": valid, "message": msg})


# --- Lineup Synergy & Team Composition Routes ---

from .lineup_synergy import LineupSynergyModel

lineup_synergy_model = LineupSynergyModel(db=db)


@app.route("/api/lineup/evaluate", methods=["POST"])
def api_lineup_evaluate():
    """Evaluates a 5-player lineup, computing talent baseline, synergy, spacing, and predicted net rating."""
    payload = request.get_json() or {}
    players = payload.get("players", [])
    season = payload.get("season", "2024-25")

    if not players or len(players) != 5:
        return jsonify({"success": False, "error": "Must provide exactly 5 players in the 'players' array."}), 400

    res = lineup_synergy_model.evaluate_lineup(players, season=season)
    if "error" in res:
        return jsonify({"success": False, "error": res["error"], "details": res}), 400

    lineup_synergy_model.save_lineup_evaluation(res)
    return jsonify({"success": True, "evaluation": res})


@app.route("/api/lineup/optimize", methods=["GET"])
def api_lineup_optimize():
    """Optimizes and returns the highest-synergy 5-man lineups for a given team roster."""
    team = request.args.get("team", "DEN").upper()
    season = request.args.get("season", "2024-25")
    top_k = int(request.args.get("top", 5))
    min_minutes = float(request.args.get("min_minutes", 200.0))

    lineups = lineup_synergy_model.optimize_team_lineup(team=team, season=season, top_k=top_k, min_minutes=min_minutes)
    return jsonify({
        "success": True,
        "team": team,
        "season": season,
        "count": len(lineups),
        "lineups": lineups
    })


@app.route("/api/lineup/archetype-matrix", methods=["GET"])
def api_lineup_archetype_matrix():
    """Returns the 8x8 pairwise archetype synergy matrix."""
    season = request.args.get("season", "2024-25")
    matrix_data = lineup_synergy_model.compute_archetype_synergy_matrix(season=season)
    return jsonify({"success": True, **matrix_data})


@app.route("/api/lineup/trade-fit", methods=["POST"])
def api_lineup_trade_fit():
    """Evaluates marginal chemistry and net rating impact of replacing a player in a lineup."""
    payload = request.get_json() or {}
    target = payload.get("target")
    replace = payload.get("replace")
    lineup = payload.get("lineup", [])
    season = payload.get("season", "2024-25")

    if not target or not replace or not lineup:
        return jsonify({"success": False, "error": "Must provide 'target', 'replace', and 'lineup' (5 players)."}), 400

    res = lineup_synergy_model.evaluate_trade_fit(
        target_player=target,
        current_lineup=lineup,
        replaced_player=replace,
        season=season
    )
    if "error" in res:
        return jsonify({"success": False, "error": res["error"]}), 400

    return jsonify({"success": True, "trade_fit": res})


@app.route("/api/lineup/saved", methods=["GET"])
def api_lineup_saved():
    """Returns previously evaluated and saved lineups."""
    season = request.args.get("season", "2024-25")
    team = request.args.get("team")
    limit = int(request.args.get("limit", 25))

    df = helper.get_lineup_evaluations(season=season, team=team, limit=limit)
    return jsonify({"success": True, "count": len(df), "lineups": df.to_dict(orient="records")})


# --- Capology, Contracts, Trade Simulator & Tax Events API ---

from .capology_ingestion import CapologyIngestion
from .tax_calculator import TaxCalculator
from .contract_valuation import ContractValuationEngine
from .trade_machine import TradeMachine
from .scenario_manager import ScenarioManager

capology_ingestion = CapologyIngestion(db=db)
contract_valuation_engine = ContractValuationEngine(db=db)
trade_machine = TradeMachine(db=db)
scenario_manager = ScenarioManager(db=db)


@app.route("/api/capology/settings", methods=["GET"])
def api_capology_settings():
    """Returns CBA cap parameters, thresholds, and exception levels."""
    season = request.args.get("season", "2023-24")
    settings = capology_ingestion.get_cba_settings(season)
    return jsonify({"success": True, "season": season, "settings": settings})


@app.route("/api/capology/teams", methods=["GET"])
def api_capology_teams():
    """Returns league-wide cap sheets and payroll status for all 30 teams."""
    season = request.args.get("season", "2023-24")
    sql = """
    SELECT 
        t.team_id,
        t.abbreviation,
        t.full_name,
        tcs.season,
        tcs.active_salary,
        tcs.dead_money,
        tcs.total_cap_allocations,
        tcs.cap_space,
        tcs.tax_room,
        tcs.first_apron_room,
        tcs.second_apron_room,
        tcs.tax_bill,
        tcs.is_repeater,
        tcs.hard_capped_at
    FROM team_cap_sheets tcs
    JOIN teams t ON tcs.team_id = t.team_id
    WHERE tcs.season = ?
    ORDER BY tcs.total_cap_allocations DESC
    """
    rows = db.execute_query(sql, (season,))
    cba = capology_ingestion.get_cba_settings(season)
    
    teams = []
    for r in rows:
        d = dict(r)
        # Classify tier
        status = TaxCalculator.evaluate_cap_status(
            total_payroll=d["total_cap_allocations"],
            cap_settings=cba,
            is_repeater=bool(d["is_repeater"]),
            hard_capped_at=d["hard_capped_at"]
        )
        d["tier"] = status["tier"]
        d["tier_code"] = status["tier_code"]
        d["penalties"] = status["penalties"]
        d["warnings"] = status["warnings"]
        teams.append(d)

    return jsonify({"success": True, "season": season, "count": len(teams), "teams": teams})


@app.route("/api/capology/team/<team_abbr>", methods=["GET"])
def api_capology_team(team_abbr: str):
    """Returns detailed cap sheet, multi-year contracts, dead money, and TPEs for a single franchise."""
    season = request.args.get("season", "2023-24")
    tabbr = team_abbr.upper().strip()

    # Recalculate to ensure freshest state
    sheet = capology_ingestion.recalculate_team_cap_sheet(tabbr, season)
    
    # Roster contracts
    sql_contracts = """
    SELECT 
        pc.contract_id,
        pc.player_id,
        pc.player_name,
        pc.contract_type,
        pc.total_years,
        pc.total_value,
        pc.trade_kicker_pct,
        pc.poison_pill,
        pc.no_trade_clause,
        cy.season,
        cy.cap_hit,
        cy.base_salary,
        cy.option_type,
        cy.is_guaranteed
    FROM player_contracts pc
    JOIN contract_years cy ON pc.contract_id = cy.contract_id
    WHERE pc.team_abbreviation = ? AND cy.season = ? AND pc.is_active = 1
    ORDER BY cy.cap_hit DESC
    """
    contracts_rows = db.execute_query(sql_contracts, (tabbr, season))
    contracts = [dict(r) for r in contracts_rows]

    # Also fetch all future years for multi-year view
    pids = [c["player_id"] for c in contracts]
    multi_year_map = {}
    if pids:
        placeholders = ",".join("?" for _ in pids)
        sql_future = f"""
        SELECT pc.player_id, cy.season, cy.cap_hit, cy.option_type
        FROM player_contracts pc
        JOIN contract_years cy ON pc.contract_id = cy.contract_id
        WHERE pc.player_id IN ({placeholders})
        ORDER BY cy.season ASC
        """
        f_rows = db.execute_query(sql_future, tuple(pids))
        for fr in f_rows:
            pid = fr["player_id"]
            if pid not in multi_year_map:
                multi_year_map[pid] = {}
            multi_year_map[pid][fr["season"]] = {
                "cap_hit": fr["cap_hit"],
                "option_type": fr["option_type"]
            }

    for c in contracts:
        c["all_years"] = multi_year_map.get(c["player_id"], {})

    # Dead money
    dead_rows = db.execute_query(
        "SELECT * FROM dead_money WHERE team_abbreviation = ? AND season = ?",
        (tabbr, season)
    )
    dead_money = [dict(r) for r in dead_rows]

    # TPEs
    tpe_rows = db.execute_query(
        "SELECT * FROM trade_exceptions WHERE team_abbreviation = ?",
        (tabbr,)
    )
    trade_exceptions = [dict(r) for r in tpe_rows]

    return jsonify({
        "success": True,
        "team_abbreviation": tabbr,
        "season": season,
        "cap_sheet": sheet,
        "contracts": contracts,
        "dead_money": dead_money,
        "trade_exceptions": trade_exceptions
    })


@app.route("/api/capology/valuation", methods=["GET"])
def api_capology_valuation():
    """Returns player contract valuation leaderboard with Box LEBRON surplus value and ROI %."""
    season = request.args.get("season", "2023-24")
    team = request.args.get("team")
    tier = request.args.get("tier")
    sort_by = request.args.get("sort_by", "surplus_value")
    order = request.args.get("order", "desc")
    limit = int(request.args.get("limit", 100))
    ascending = (order.lower() == "asc")

    df = contract_valuation_engine.get_valuation_leaderboard(
        season=season,
        team_abbreviation=team,
        tier=tier,
        sort_by=sort_by,
        ascending=ascending,
        limit=limit
    )

    records = df.to_dict(orient="records") if not df.empty else []
    return jsonify({
        "success": True,
        "season": season,
        "count": len(records),
        "players": records
    })


@app.route("/api/capology/trade/simulate", methods=["POST"])
def api_capology_trade_simulate():
    """Simulates a multi-team trade with 2023 CBA rules, apron restrictions, and tax impact."""
    payload = request.get_json() or {}
    season = payload.get("season", "2023-24")
    
    result = trade_machine.simulate_trade(trade_data=payload, season=season)
    return jsonify(result)


@app.route("/api/capology/events/waive-stretch", methods=["POST"])
def api_capology_waive_stretch():
    """Simulates waiving and stretching a player contract over (2*years)+1 seasons."""
    payload = request.get_json() or {}
    player_id = payload.get("player_id")
    season = payload.get("season", "2023-24")

    if not player_id:
        return jsonify({"success": False, "error": "player_id required"}), 400

    # Query remaining contract years
    sql = """
    SELECT pc.player_name, cy.season, cy.cap_hit, cy.guaranteed_amount
    FROM player_contracts pc
    JOIN contract_years cy ON pc.contract_id = cy.contract_id
    WHERE pc.player_id = ? AND cy.season >= ?
    ORDER BY cy.season ASC
    """
    rows = db.execute_query(sql, (player_id, season))
    if not rows:
        return jsonify({"success": False, "error": f"No remaining contract years found for player {player_id}"}), 404

    contract_years = [dict(r) for r in rows]
    stretch_result = TaxCalculator.calculate_waive_and_stretch(contract_years, waived_season=season)

    return jsonify({"success": True, "stretch_result": stretch_result})


@app.route("/api/capology/scenarios", methods=["GET"])
def api_capology_scenarios():
    """Lists saved simulation scenarios."""
    scenarios = scenario_manager.list_scenarios()
    return jsonify({"success": True, "scenarios": scenarios})


@app.route("/api/capology/scenarios/<scenario_id>", methods=["GET"])
def api_capology_scenario_get(scenario_id: str):
    """Fetches a saved scenario by ID."""
    scn = scenario_manager.get_scenario(scenario_id)
    if not scn:
        return jsonify({"success": False, "error": "Scenario not found"}), 404
    return jsonify({"success": True, "scenario": scn})


@app.route("/api/capology/scenarios/save", methods=["POST"])
def api_capology_scenarios_save():
    """Saves a simulation scenario."""
    payload = request.get_json() or {}
    name = payload.get("name", "Untitled Trade Scenario").strip()
    description = payload.get("description", "").strip()
    state = payload.get("state", {})
    scenario_id = payload.get("scenario_id")

    res = scenario_manager.save_scenario(
        name=name,
        description=description,
        state=state,
        scenario_id=scenario_id
    )
    return jsonify({"success": True, "scenario": res})


@app.route("/api/capology/scenarios/<scenario_id>", methods=["DELETE"])
def api_capology_scenarios_delete(scenario_id: str):
    """Deletes a saved scenario."""
    deleted = scenario_manager.delete_scenario(scenario_id)
    return jsonify({"success": deleted})


@app.route("/api/capology/scenarios/apply", methods=["POST"])
def api_capology_scenarios_apply():
    """Commits a simulated trade result to active rosters and updates team cap sheets."""
    payload = request.get_json() or {}
    trade_result = payload.get("trade_result")
    season = payload.get("season", "2023-24")

    if not trade_result:
        return jsonify({"success": False, "error": "trade_result required"}), 400

    try:
        res = scenario_manager.apply_trade_to_active(trade_result, season=season)
        return jsonify({"success": True, "result": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/capology/scenarios/reset", methods=["POST"])
def api_capology_scenarios_reset():
    """Resets all player contracts and team cap sheets to official baseline."""
    res = scenario_manager.reset_to_baseline()
    return jsonify({"success": True, "result": res})


def run_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):

    """Starts the Flask server."""
    print(f"Starting NBA Stats DB Server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    run_server(port=port)
