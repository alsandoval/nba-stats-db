import argparse
import sys
import logging
from tabulate import tabulate

# Ensure UTF-8 output in Windows consoles for international player names (e.g., Dončić, Jokić)
if sys.stdout.encoding != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .database import NBADatabase
from .ingestion import NBADataIngestor
from .queries import NBAQueryHelper


def print_df(df, title: str = None):
    """Pretty-prints a pandas dataframe using tabulate."""
    if title:
        print(f"\n=== {title} ===")
    if df.empty:
        print("No records found.")
    else:
        print(tabulate(df, headers="keys", tablefmt="psql", showindex=False))
    print()


def cmd_init(args, db: NBADatabase):
    db.init_database()
    print(f"Successfully initialized NBA Stats database at: {db.db_path}")


def cmd_status(args, db: NBADatabase):
    counts = db.get_table_counts()
    print(f"\n=== Database Status ({db.db_path}) ===")
    rows = [{"Table": tbl, "Row Count": f"{cnt:,}"} for tbl, cnt in counts.items()]
    import pandas as pd
    print(tabulate(pd.DataFrame(rows), headers="keys", tablefmt="psql", showindex=False))
    print()


def cmd_populate(args, db: NBADatabase):
    ingestor = NBADataIngestor(db=db)
    if args.teams_only:
        ingestor.ingest_teams()
    elif args.players_only:
        ingestor.ingest_players()
    elif args.standings_only:
        ingestor.ingest_standings(season=args.season)
    elif args.stats_only:
        ingestor.ingest_player_season_stats(season=args.season)
    elif args.games_only:
        ingestor.ingest_games_and_game_logs(season=args.season)
    else:
        # Full population
        ingestor.ingest_all(season=args.season)

    cmd_status(args, db)


def cmd_top_scorers(args, db: NBADatabase):
    helper = NBAQueryHelper(db=db)
    df = helper.get_top_scorers(season=args.season, limit=args.limit, min_gp=args.min_gp)
    print_df(df, f"Top {args.limit} Scorers (Season {args.season})")


def cmd_standings(args, db: NBADatabase):
    helper = NBAQueryHelper(db=db)
    df = helper.get_standings(season=args.season, conference=args.conference)
    title = f"{args.conference + ' ' if args.conference else ''}Standings (Season {args.season})"
    print_df(df, title)


def cmd_player_logs(args, db: NBADatabase):
    helper = NBAQueryHelper(db=db)
    df = helper.get_player_game_logs(player_name=args.name, limit=args.limit)
    print_df(df, f"Game Logs for '{args.name}' (Last {args.limit} games)")


def cmd_high_scores(args, db: NBADatabase):
    helper = NBAQueryHelper(db=db)
    df = helper.get_highest_scoring_games(limit=args.limit)
    print_df(df, f"Highest Single-Game Scoring Performances (Top {args.limit})")


def cmd_triple_doubles(args, db: NBADatabase):
    helper = NBAQueryHelper(db=db)
    df = helper.get_triple_doubles(limit=args.limit)
    print_df(df, f"Recent Triple-Double Games (Top {args.limit})")


def cmd_h2h(args, db: NBADatabase):
    helper = NBAQueryHelper(db=db)
    df = helper.get_head_to_head(args.team1.upper(), args.team2.upper())
    print_df(df, f"Head-to-Head: {args.team1.upper()} vs. {args.team2.upper()}")


def cmd_sql(args, db: NBADatabase):
    helper = NBAQueryHelper(db=db)
    try:
        df = helper.execute_sql(args.query)
        print_df(df, "Query Results")
    except Exception as e:
        print(f"SQL Error: {e}", file=sys.stderr)


def cmd_serve(args, db: NBADatabase):
    from .server import run_server
    run_server(host=args.host, port=args.port)


def cmd_compare_players(args, db: NBADatabase):
    helper = NBAQueryHelper(db=db)
    res = helper.compare_players(args.player1, args.player2, season=args.season)
    if "error" in res:
        print(f"Error: {res['error']}", file=sys.stderr)
        return
    import pandas as pd
    p1 = res["player1"]
    p2 = res["player2"]
    metrics = ["gp", "mpg", "ppg", "rpg", "apg", "spg", "bpg", "fg_pct", "fg3_pct", "ft_pct", "plus_minus"]
    rows = []
    for m in metrics:
        rows.append({
            p1["name"]: p1.get(m, "-"),
            "Metric": m.upper(),
            p2["name"]: p2.get(m, "-"),
        })
    print_df(pd.DataFrame(rows), f"Comparison: {p1['name']} vs. {p2['name']} ({args.season})")
    h2h = res["h2h"]
    print(f"Direct Head-to-Head Record: {p1['name']} {h2h['player1_wins']}W - {p2['name']} {h2h['player2_wins']}W ({h2h['total_games']} games)")


def cmd_compare_teams(args, db: NBADatabase):
    helper = NBAQueryHelper(db=db)
    res = helper.compare_teams(args.team1, args.team2, season=args.season)
    import pandas as pd
    t1 = res["team1"]
    t2 = res["team2"]
    metrics = ["w", "l", "win_pct", "ppg", "opp_ppg", "diff", "off_rating", "def_rating", "net_rating", "pace", "ts_pct"]
    rows = []
    for m in metrics:
        rows.append({
            t1["name"]: t1.get(m, "-"),
            "Metric": m.upper(),
            t2["name"]: t2.get(m, "-"),
        })
    print_df(pd.DataFrame(rows), f"Comparison: {t1['name']} vs. {t2['name']} ({args.season})")
    h2h = res["h2h"]
    print(f"Head-to-Head Record: {t1['abbr']} {h2h['team1_wins']}W - {t2['abbr']} {h2h['team2_wins']}W ({h2h['total_games']} games)")


def main():
    parser = argparse.ArgumentParser(
        prog="nba-stats-db",
        description="CLI tool for managing and querying the NBA Stats SQLite Database.",
    )
    parser.add_argument(
        "--db",
        default="nba_stats.db",
        help="Path to the SQLite database file (default: nba_stats.db)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # init
    p_init = subparsers.add_parser("init", help="Initialize the database schema")

    # status
    p_status = subparsers.add_parser("status", help="Show database table record counts")

    # populate
    p_pop = subparsers.add_parser("populate", help="Ingest NBA data from API into database")
    p_pop.add_argument("--season", default="2023-24", help="NBA Season (e.g. 2023-24)")
    p_pop.add_argument("--teams-only", action="store_true", help="Only ingest franchises")
    p_pop.add_argument("--players-only", action="store_true", help="Only ingest players")
    p_pop.add_argument("--standings-only", action="store_true", help="Only ingest standings")
    p_pop.add_argument("--stats-only", action="store_true", help="Only ingest player stats")
    p_pop.add_argument("--games-only", action="store_true", help="Only ingest games & logs")

    # top-scorers
    p_scorers = subparsers.add_parser("top-scorers", help="View league scoring leaders")
    p_scorers.add_argument("--season", default="2023-24", help="NBA Season (e.g. 2023-24)")
    p_scorers.add_argument("--limit", type=int, default=10, help="Number of records")
    p_scorers.add_argument("--min-gp", type=int, default=20, help="Minimum games played")

    # standings
    p_standings = subparsers.add_parser("standings", help="View league standings")
    p_standings.add_argument("--season", default="2023-24", help="NBA Season (e.g. 2023-24)")
    p_standings.add_argument("--conference", choices=["East", "West"], default=None, help="Filter by conference")

    # player-logs
    p_plogs = subparsers.add_parser("player-logs", help="View player game logs")
    p_plogs.add_argument("--name", required=True, help="Player full or partial name")
    p_plogs.add_argument("--limit", type=int, default=10, help="Number of games")

    # compare-players
    p_cp = subparsers.add_parser("compare-players", help="Compare two players side-by-side")
    p_cp.add_argument("--player1", "-p1", required=True, help="First player name")
    p_cp.add_argument("--player2", "-p2", required=True, help="Second player name")
    p_cp.add_argument("--season", default="2023-24", help="NBA Season")

    # compare-teams
    p_ct = subparsers.add_parser("compare-teams", help="Compare two teams side-by-side")
    p_ct.add_argument("--team1", "-t1", required=True, help="First team abbreviation (e.g. BOS)")
    p_ct.add_argument("--team2", "-t2", required=True, help="Second team abbreviation (e.g. DAL)")
    p_ct.add_argument("--season", default="2023-24", help="NBA Season")

    # high-scores
    p_high = subparsers.add_parser("high-scores", help="View highest single-game scoring marks")
    p_high.add_argument("--limit", type=int, default=10, help="Number of games")

    # triple-doubles
    p_td = subparsers.add_parser("triple-doubles", help="View triple-double performances")
    p_td.add_argument("--limit", type=int, default=10, help="Number of games")

    # h2h
    p_h2h = subparsers.add_parser("h2h", help="View head-to-head match history between two teams")
    p_h2h.add_argument("--team1", required=True, help="First team abbreviation (e.g. BOS)")
    p_h2h.add_argument("--team2", required=True, help="Second team abbreviation (e.g. NYK)")

    # sql
    p_sql = subparsers.add_parser("sql", help="Execute arbitrary SQL against the database")
    p_sql.add_argument("query", help="SQL query string to run")

    # serve
    p_serve = subparsers.add_parser("serve", help="Launch the Web Frontend & REST API Server")
    p_serve.add_argument("--host", default="127.0.0.1", help="Host IP (default: 127.0.0.1)")
    p_serve.add_argument("--port", type=int, default=5000, help="Port number (default: 5000)")

    # endpoints-list
    p_eplist = subparsers.add_parser("endpoints-list", help="List all 138 NBA API endpoints and download status")
    p_eplist.add_argument("--category", default=None, help="Filter by category")
    p_eplist.add_argument("--status", default=None, help="Filter by status (SUCCESS, EMPTY, DEPRECATED, PENDING, ERROR)")

    # download-endpoints
    p_epdl = subparsers.add_parser("download-endpoints", help="Download all or selected NBA API endpoints")
    p_epdl.add_argument("--endpoint", default=None, help="Download a specific endpoint")
    p_epdl.add_argument("--category", default=None, help="Filter by category")
    p_epdl.add_argument("--force", action="store_true", help="Force re-download")
    p_epdl.add_argument("--delay", type=float, default=0.75, help="Delay between calls in seconds")

    # endpoint-info
    p_epinfo = subparsers.add_parser("endpoint-info", help="View metadata, tables, and sample rows for an endpoint")
    p_epinfo.add_argument("name", help="Endpoint name (e.g. AllTimeLeadersGrids)")

    # validate
    p_val = subparsers.add_parser("validate", help="Run comprehensive data integrity validator across all tables and endpoints")

    # live-scores
    p_live = subparsers.add_parser("live-scores", help="View current live NBA scoreboard and games")
    p_live.add_argument("--refresh", action="store_true", help="Fetch fresh data from live CDN before displaying")
    p_live.add_argument("--demo", action="store_true", help="Display simulated games if currently in offseason")

    # live-poll
    p_lpoll = subparsers.add_parser("live-poll", help="Run adaptive real-time live score updater daemon")
    p_lpoll.add_argument("--live-interval", type=int, default=20, help="Polling interval during live games in seconds (default: 20)")
    p_lpoll.add_argument("--upcoming-interval", type=int, default=120, help="Polling interval for upcoming games in seconds (default: 120)")
    p_lpoll.add_argument("--idle-interval", type=int, default=900, help="Polling interval when idle / no games in seconds (default: 900)")

    # lebron
    p_leb = subparsers.add_parser("lebron", help="View Box LEBRON impact ratings, archetypes, and Wins Added")
    p_leb.add_argument("--season", default="2023-24", help="NBA Season (default: 2023-24)")
    p_leb.add_argument("--top", type=int, default=20, help="Number of players to display (default: 20)")
    p_leb.add_argument("--min-minutes", type=float, default=500.0, help="Minimum minutes played filter (default: 500)")
    p_leb.add_argument("--sort-by", choices=["box_lebron", "o_lebron", "d_lebron", "wins_added"], default="box_lebron", help="Sort criterion")
    p_leb.add_argument("--player", default=None, help="Filter by player name for full career Box LEBRON history")
    p_leb.add_argument("--archetypes", action="store_true", help="Display archetype summary and distributions")

    # compute-lebron
    p_cleb = subparsers.add_parser("compute-lebron", help="Calculate and store Box LEBRON ratings in the database")
    p_cleb.add_argument("--season", default="2023-24", help="Season to calculate (default: 2023-24)")
    p_cleb.add_argument("--all", action="store_true", help="Compute for all seasons present in database")

    # train-lebron
    p_tleb = subparsers.add_parser("train-lebron", help="Train Machine Learning model weights for Box LEBRON on historical data")
    p_tleb.add_argument("--estimator", choices=["ridge", "elasticnet"], default="ridge", help="Regression algorithm (default: ridge)")
    p_tleb.add_argument("--cv", type=int, default=5, help="Cross-validation folds (default: 5)")
    p_tleb.add_argument("--min-minutes", type=float, default=400.0, help="Minimum minutes filter for training samples (default: 400)")
    p_tleb.add_argument("--recalculate", action="store_true", help="Automatically recalculate ratings across all seasons after training")

    # cluster-positions
    p_clust = subparsers.add_parser("cluster-positions", help="Discover modern position archetypes via K-Means and 3D t-SNE")
    p_clust.add_argument("--season", default="2023-24", help="NBA Season (default: 2023-24)")
    p_clust.add_argument("--k", type=int, default=None, help="Number of clusters (default: automatically finds optimal k)")
    p_clust.add_argument("--min-minutes", type=float, default=300.0, help="Minimum total minutes filter (default: 300)")
    p_clust.add_argument("--find-k", action="store_true", help="Scan and display Silhouette & Elbow Inertia scores across k=3..12")
    p_clust.add_argument("--viz", action="store_true", help="Generate interactive 3D t-SNE HTML Plotly visualization")
    p_clust.add_argument("--viz-file", default="nba_stats_db/static/clustering_3d.html", help="Output path for HTML visualization")

    # evaluate-lineup
    p_eval = subparsers.add_parser("evaluate-lineup", help="Evaluate 5-man lineup synergy, chemistry, and predicted net rating")
    p_eval.add_argument("--players", required=True, help="Comma-separated list of 5 player names (e.g. 'Jokic, Murray, MPJ, Gordon, Braun')")
    p_eval.add_argument("--season", default="2024-25", help="NBA Season (default: 2024-25)")

    # optimize-team-lineup
    p_opt = subparsers.add_parser("optimize-team-lineup", help="Find most synergistic 5-man lineups from a team's roster")
    p_opt.add_argument("--team", required=True, help="Team abbreviation (e.g. DEN, BOS, OKC)")
    p_opt.add_argument("--season", default="2024-25", help="NBA Season (default: 2024-25)")
    p_opt.add_argument("--top", type=int, default=5, help="Number of top lineups to display (default: 5)")
    p_opt.add_argument("--min-minutes", type=float, default=200.0, help="Minimum player minutes filter (default: 200)")

    # archetype-synergy
    p_asyn = subparsers.add_parser("archetype-synergy", help="Display pairwise archetype synergy compatibility matrix")
    p_asyn.add_argument("--season", default="2024-25", help="NBA Season (default: 2024-25)")

    # trade-fit
    p_trd = subparsers.add_parser("trade-fit", help="Evaluate marginal chemistry and net rating impact of replacing a player in a lineup")
    p_trd.add_argument("--target", required=True, help="Target player name being acquired")
    p_trd.add_argument("--replace", required=True, help="Current player being replaced")
    p_trd.add_argument("--lineup", required=True, help="Comma-separated current 5-man lineup")
    p_trd.add_argument("--season", default="2024-25", help="NBA Season (default: 2024-25)")

    # cap-sheet
    p_cs = subparsers.add_parser("cap-sheet", help="Display team salary cap sheet, tax room, and apron status")
    p_cs.add_argument("team", help="Team abbreviation (e.g. LAL, BOS, GSW)")
    p_cs.add_argument("--season", default="2023-24", help="NBA Season (default: 2023-24)")

    # contract-values
    p_cv = subparsers.add_parser("contract-values", help="Display player contract valuation and surplus WAR leaderboard")
    p_cv.add_argument("--season", default="2023-24", help="NBA Season (default: 2023-24)")
    p_cv.add_argument("--team", help="Filter by team abbreviation")
    p_cv.add_argument("--tier", help="Filter by tier (Super Bargain, High Surplus Value, Fair Market Value, Overpaid, Toxic Contract)")
    p_cv.add_argument("--sort", default="surplus_value", help="Sort field (surplus_value, roi_pct, cap_hit, fair_market_value)")
    p_cv.add_argument("--top", type=int, default=20, help="Number of rows (default: 20)")
    p_cv.add_argument("--asc", action="store_true", help="Sort ascending (worst contracts first)")

    # simulate-trade
    p_st = subparsers.add_parser("simulate-trade", help="Simulate a trade under 2023 CBA rules")
    p_st.add_argument("--teams", required=True, help="Comma-separated participating teams (e.g. LAL,BOS)")
    p_st.add_argument("--send", required=True, help="Comma-separated team:player_id (e.g. LAL:2544,BOS:1628369)")
    p_st.add_argument("--season", default="2023-24", help="NBA Season (default: 2023-24)")

    # tax-bill
    p_tb = subparsers.add_parser("tax-bill", help="Display team progressive luxury tax bill and apron bracket breakdown")
    p_tb.add_argument("team", help="Team abbreviation")
    p_tb.add_argument("--season", default="2023-24", help="NBA Season (default: 2023-24)")

    # seed-capology
    p_sc = subparsers.add_parser("seed-capology", help="Seed/reset contracts and capology database")
    p_sc.add_argument("--file", help="Path to seed json file (optional)")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    db = NBADatabase(db_path=args.db)

    def cmd_endpoints_list(args, db: NBADatabase):
        catalog = db.get_endpoints_catalog(category=args.category, status=args.status)
        import pandas as pd
        rows = [
            {
                "Endpoint": ep["endpoint_name"],
                "Category": ep["category"],
                "Status": ep.get("status", "PENDING"),
                "Rows": f"{ep.get('total_rows', 0):,}",
                "Tables": ep.get("result_sets_count", 0),
            }
            for ep in catalog
        ]
        print_df(pd.DataFrame(rows), f"NBA API Endpoints ({len(catalog)} total)")

    def cmd_download_endpoints(args, db: NBADatabase):
        from .endpoints_downloader import NBAEndpointDownloader
        downloader = NBAEndpointDownloader(db=db)
        if args.endpoint:
            print(f"Downloading endpoint: {args.endpoint}...")
            res = downloader.download_endpoint(args.endpoint, force=args.force)
            print(f"Status: {res['status']} | Total Rows: {res['total_rows']} | Tables: {res['result_sets_count']}")
        else:
            cats = [args.category] if args.category else None
            print(f"Starting batch download (category={args.category}, force={args.force})...")
            res = downloader.download_all_endpoints(categories=cats, force=args.force, delay=args.delay)
            print(f"Done! Succeeded: {res['succeeded']}, Empty: {res['empty']}, Deprecated: {res['deprecated']}, Error: {res['error']}")

    def cmd_endpoint_info(args, db: NBADatabase):
        detail = db.get_endpoint_detail(args.name)
        if not detail:
            print(f"Endpoint '{args.name}' not found in catalog.")
            return
        print(f"\n=== Endpoint: {detail['endpoint_name']} ===")
        print(f"Category: {detail['category']}")
        print(f"Status:   {detail.get('status', 'PENDING')}")
        print(f"Doc:      {detail.get('docstring', 'N/A')}")
        print(f"Rows:     {detail.get('total_rows', 0):,}")
        datasets = detail.get("datasets", [])
        print(f"Datasets ({len(datasets)}):")
        for ds in datasets:
            print(f"\n  Dataset: {ds['dataset_name']} -> Table: {ds['table_name']} ({ds['row_count']} rows)")
            import pandas as pd
            if ds.get("preview_rows"):
                preview = pd.DataFrame(ds["preview_rows"])
                print(tabulate(preview.iloc[:3, :6], headers="keys", tablefmt="psql", showindex=False))

    def cmd_validate(args, db: NBADatabase):
        from .validator import NBADataValidator
        validator = NBADataValidator(db=db)
        results = validator.run_all_validations()
        table_rows = []
        for r in results:
            st = "PASS" if r.status == "PASS" else "WARN" if r.status == "WARN" else "FAIL"
            table_rows.append([r.category, r.name, st, r.message])
        import pandas as pd
        print_df(pd.DataFrame(table_rows, columns=["Category", "Check", "Status", "Details"]), "Data Validation Report")
        passed = sum(1 for r in results if r.status == "PASS")
        print(f"Summary: {passed}/{len(results)} checks passed.")

    def cmd_live_scores(args, db: NBADatabase):
        from .live_scores import NBALiveService
        service = NBALiveService(db=db)
        if args.refresh:
            print("Fetching live data from NBA CDN...")
            raw = service.fetch_todays_scoreboard()
            service.save_live_scoreboard(raw)

        data = service.get_cached_scoreboard()
        games = data.get("games", [])

        if not games and args.demo:
            print("No active games on today's schedule (off-season). Showing demo game:")
            games = [
                {
                    "game_id": "0022300001",
                    "game_status_text": "Q3 04:12 (LIVE DEMO)",
                    "away_team": {"tricode": "LAL", "score": 80},
                    "home_team": {"tricode": "DEN", "score": 87},
                    "game_leaders": {
                        "awayLeaders": {"name": "LeBron James", "points": 21, "rebounds": 8, "assists": 5},
                        "homeLeaders": {"name": "Nikola Jokic", "points": 29, "rebounds": 13, "assists": 11},
                    },
                }
            ]

        if not games:
            print("\nNo live NBA games on the schedule for today.")
            print("Use 'python -m nba_stats_db.cli live-scores --demo' to preview.")
            return

        print(f"\n=== Live NBA Scoreboard ({len(games)} games) ===")
        import pandas as pd
        rows = []
        for g in games:
            home = g.get("home_team", {})
            away = g.get("away_team", {})
            st = g.get("game_status_text", "")
            matchup = f"{away.get('tricode', '')} @ {home.get('tricode', '')}"
            score = f"{away.get('score', 0)} - {home.get('score', 0)}"
            leaders = g.get("game_leaders", {})
            away_ldr = leaders.get("awayLeaders", {}).get("name", "")
            home_ldr = leaders.get("homeLeaders", {}).get("name", "")
            ldr_str = f"{away_ldr} / {home_ldr}" if (away_ldr or home_ldr) else "-"
            rows.append({
                "Game ID": g.get("game_id", ""),
                "Matchup": matchup,
                "Status / Clock": st,
                "Score (Away - Home)": score,
                "Leaders": ldr_str,
            })
        print_df(pd.DataFrame(rows))

    def cmd_live_poll(args, db: NBADatabase):
        from .live_scheduler import NBALiveScheduler
        print("=" * 65)
        print(" 🏀 NBA Stats DB - Live Schedule-Aware Polling Daemon")
        print(f" Live Game Interval : {args.live_interval}s")
        print(f" Upcoming Interval  : {args.upcoming_interval}s")
        print(f" Idle / Off Interval: {args.idle_interval}s")
        print(" Press Ctrl+C to terminate.")
        print("=" * 65)

        def on_update(summary):
            t = summary.get("poll_time", "")[:19]
            total = summary.get("total_games", 0)
            live = summary.get("live_games", 0)
            nxt = summary.get("next_interval_sec", 0)
            print(f"[{t}] Poll complete | Games today: {total} | LIVE: {live} | Next poll in {nxt}s", flush=True)

        scheduler = NBALiveScheduler(
            db=db,
            live_interval=args.live_interval,
            upcoming_interval=args.upcoming_interval,
            idle_interval=args.idle_interval,
            on_update=on_update,
        )
        try:
            scheduler.start()
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping live polling daemon...")
            scheduler.stop()
            print("Daemon stopped.")

    def cmd_lebron(args, db: NBADatabase):
        helper = NBAQueryHelper(db=db)
        if args.player:
            players_df = helper.search_players(args.player)
            if players_df.empty:
                print(f"Player '{args.player}' not found.")
                return
            p_id = int(players_df.iloc[0]["player_id"])
            p_name = players_df.iloc[0]["full_name"]
            history_df = helper.get_player_box_lebron_history(player_id=p_id)
            if history_df.empty:
                print(f"No Box LEBRON ratings found for {p_name}. Run 'compute-lebron' first.")
                return
            print_df(history_df, f"Box LEBRON Career History: {p_name}")
            return

        if args.archetypes:
            arch_df = helper.get_box_lebron_archetype_distribution(season=args.season)
            print_df(arch_df, f"Box LEBRON Offensive Archetype Distribution (Season {args.season})")
            return

        df = helper.get_box_lebron_leaderboard(
            season=args.season,
            min_minutes=args.min_minutes,
            limit=args.top,
            sort_by=args.sort_by,
        )
        if df.empty:
            print(f"No Box LEBRON records found for season {args.season}. Running computation now...")
            from .box_lebron import BoxLEBRONModel
            model = BoxLEBRONModel(db=db)
            model.save_season_box_lebron(season=args.season)
            df = helper.get_box_lebron_leaderboard(
                season=args.season,
                min_minutes=args.min_minutes,
                limit=args.top,
                sort_by=args.sort_by,
            )

        title = f"Top {args.top} Box LEBRON Leaders (Season {args.season}, Min {args.min_minutes:.0f} mins, Sorted by {args.sort_by})"
        print_df(df, title)

    def cmd_compute_lebron(args, db: NBADatabase):
        from .box_lebron import BoxLEBRONModel
        model = BoxLEBRONModel(db=db)
        if args.all:
            print("Calculating Box LEBRON for ALL available seasons in database...")
            res = model.compute_all_seasons()
            for s, cnt in res.items():
                print(f"  Season {s}: {cnt} player ratings stored.")
        else:
            print(f"Calculating Box LEBRON for season {args.season}...")
            cnt = model.save_season_box_lebron(season=args.season)
            print(f"Successfully computed and stored {cnt} player ratings for {args.season}.")

    def cmd_train_lebron(args, db: NBADatabase):
        from .trainer import BoxLEBRONTrainer
        from .box_lebron import BoxLEBRONModel
        import pandas as pd
        print(f"\n=== Training Machine Learning Model for Box LEBRON ({args.estimator.upper()}, CV={args.cv}) ===")
        trainer = BoxLEBRONTrainer(db=db)
        meta = trainer.train(estimator=args.estimator, cv=args.cv, min_minutes=args.min_minutes)
        save_path = trainer.save_model()
        print(f"Model saved to: {save_path}")

        print(f"\n--- Model Evaluation (Out-of-Sample Test Set) ---")
        o_m = meta["offensive_metrics"]
        d_m = meta["defensive_metrics"]
        eval_df = pd.DataFrame([
            {"Sub-Model": "O-LEBRON (Offense)", "R2 Score": o_m["r2"], "RMSE": o_m["rmse"], "MAE": o_m["mae"], "Best Alpha": o_m["best_alpha"]},
            {"Sub-Model": "D-LEBRON (Defense)", "R2 Score": d_m["r2"], "RMSE": d_m["rmse"], "MAE": d_m["mae"], "Best Alpha": d_m["best_alpha"]},
        ])
        print_df(eval_df)

        print("\n--- Learned Offensive Feature Weights ---")
        o_weights = meta["offensive_weights"]
        o_std = meta["offensive_weights_standardized"]
        o_rows = [{"Feature": k, "Raw Weight": round(v, 4), "Standardized Weight": round(o_std.get(k, 0.0), 4)} for k, v in o_weights.items()]
        print_df(pd.DataFrame(o_rows).sort_values(by="Standardized Weight", ascending=False))

        print("\n--- Learned Defensive Feature Weights ---")
        d_weights = meta["defensive_weights"]
        d_std = meta["defensive_weights_standardized"]
        d_rows = [{"Feature": k, "Raw Weight": round(v, 4), "Standardized Weight": round(d_std.get(k, 0.0), 4)} for k, v in d_weights.items()]
        print_df(pd.DataFrame(d_rows).sort_values(by="Standardized Weight", ascending=False))

        if args.recalculate:
            print("\nRecalculating Box LEBRON across all database seasons with updated weights...")
            model = BoxLEBRONModel(db=db)
            res = model.compute_all_seasons()
            print(f"Recalculation complete across {len(res)} seasons.")

    def cmd_cluster_positions(args, db: NBADatabase):
        from .clustering import PositionClusteringModel
        import pandas as pd

        model = PositionClusteringModel(db=db)

        if args.find_k:
            print(f"\n=== Scanning Optimal Cluster Count (k=3..12) for Season {args.season} ===")
            opt = model.find_optimal_k(k_range=(3, 12), season=args.season, min_minutes=args.min_minutes)
            rows = []
            for k_val, sil, ine in zip(opt["k_values"], opt["silhouette_scores"], opt["inertias"]):
                rows.append({"k": k_val, "Silhouette Score": sil, "Inertia (Elbow)": ine, "Is Optimal": "⭐ YES" if k_val == opt["optimal_k"] else ""})
            print_df(pd.DataFrame(rows))
            print(f"Optimal Cluster Count: k={opt['optimal_k']} (Silhouette: {opt['max_silhouette_score']})\n")
            if args.k is None:
                args.k = opt["optimal_k"]

        k_target = args.k
        if k_target is None:
            opt = model.find_optimal_k(k_range=(4, 10), season=args.season, min_minutes=args.min_minutes)
            k_target = opt["optimal_k"]

        print(f"\n=== Fitting K-Means Clustering (k={k_target}) & 3D t-SNE (Season {args.season}) ===")
        df = model.fit_clusters(k=k_target, season=args.season, min_minutes=args.min_minutes)
        df_3d = model.compute_3d_tsne()
        saved = model.save_to_db()
        print(f"Saved {saved} player position cluster records to database.")

        print(f"\n=== Discovered Position Archetypes (Season {args.season}, k={k_target}) ===")
        summary_rows = []
        for cid, p in model.cluster_profiles.items():
            summary_rows.append({
                "Cluster ID": cid,
                "Archetype Name": p["name"],
                "Count": f"{p['count']} ({p['pct_of_league']}%)",
                "Flagship Players": ", ".join(p["flagship_players"][:3]),
                "Avg USG%": f"{p['centroid_stats']['usg_pct']}%",
                "Avg AST%": f"{p['centroid_stats']['ast_pct']}%",
                "Avg REB%": f"{p['centroid_stats']['reb_pct']}%",
                "Avg 3PA%": f"{p['centroid_stats']['fg3a_rate']}%",
                "Avg Box LEBRON": f"{p['centroid_stats']['box_lebron']:+.2f}",
            })
        print_df(pd.DataFrame(summary_rows))

        if args.viz:
            out_file = args.viz_file
            model.generate_3d_plot_html(output_file=out_file)
            print(f"\nSuccessfully generated interactive 3D t-SNE visualization at: {out_file}")

    def cmd_evaluate_lineup(args, db: NBADatabase):
        from .lineup_synergy import LineupSynergyModel
        import pandas as pd
        import sys
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")

        players = [p.strip() for p in args.players.split(",") if p.strip()]
        if len(players) != 5:
            print(f"Error: Please provide exactly 5 players separated by commas. Received {len(players)}.")
            return

        model = LineupSynergyModel(db=db)
        res = model.evaluate_lineup(players, season=args.season)
        if "error" in res:
            print(f"Error evaluating lineup: {res['error']}")
            if "resolved_players" in res and res["resolved_players"]:
                print(f"Resolved: {', '.join(res['resolved_players'])}")
            return

        model.save_lineup_evaluation(res)

        print(f"\n=== 🏀 Lineup Synergy & Composition Evaluation ({args.season}) ===")
        print(f" Lineup: {res['player_names']}")
        print(f" Team Representation: {res['team']}")
        print(f" Alagappan Balance Grade: ⭐ {res['balance_grade']} (Score: {res['balance_score']}/100)")
        print(f" Predicted Net Rating: {res['predicted_net_rating']:+.2f} pts/100 poss")
        print("-" * 65)

        print("\n--- 5-Man Player Breakdown ---")
        p_rows = []
        for p in res["players"]:
            p_rows.append({
                "Player": p["player_name"],
                "Team": p["team"],
                "Archetype": p["archetype"],
                "USG%": f"{p['usg_pct']}%",
                "3PA% (3P%)": f"{p['fg3a_rate']}% ({p['fg3_pct']}%)",
                "AST%": f"{p['ast_pct']}%",
                "Box LEBRON": f"{p['box_lebron']:+.2f}",
            })
        print_df(pd.DataFrame(p_rows))

        print("\n--- Synergy & Fit Analytics (White Paper Metrics) ---")
        syn_rows = [
            {"Factor": "Raw Talent Baseline (Sum of LEBRON)", "Value": f"{res['raw_lebron_sum']:+.2f}"},
            {"Factor": "Spatial Perimeter Spacing Bonus", "Value": f"{res['offensive_synergy']:+.2f}"},
            {"Factor": "Interior & PoA Defense Synergy", "Value": f"{res['defensive_synergy']:+.2f}"},
            {"Factor": "Usage Collision / Cannibalization Tax", "Value": f"-{res['usage_penalty']:.2f}"},
            {"Factor": "Net Non-Linear Synergy Score", "Value": f"{res['total_synergy']:+.2f}"},
            {"Factor": "Perimeter Spacers Count", "Value": f"{res['num_shooters']} / 5"},
            {"Factor": "Total Assigned Usage%", "Value": f"{res['total_usage_pct']}%"},
        ]
        print_df(pd.DataFrame(syn_rows))

    def cmd_optimize_team_lineup(args, db: NBADatabase):
        from .lineup_synergy import LineupSynergyModel
        import pandas as pd
        import sys
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")

        model = LineupSynergyModel(db=db)
        print(f"\n=== Optimizing 5-Man Roster Lineups for {args.team.upper()} ({args.season}) ===")
        lineups = model.optimize_team_lineup(team=args.team.upper(), season=args.season, top_k=args.top, min_minutes=args.min_minutes)

        if not lineups:
            print(f"No qualified roster found for team {args.team.upper()} in season {args.season}.")
            return

        rows = []
        for i, l in enumerate(lineups):
            rows.append({
                "Rank": f"#{i+1}",
                "Grade": l["balance_grade"],
                "Pred NetRtg": f"{l['predicted_net_rating']:+.2f}",
                "Raw LEBRON": f"{l['raw_lebron_sum']:+.2f}",
                "Synergy": f"{l['total_synergy']:+.2f}",
                "Spacing": f"{l['num_shooters']}/5",
                "Lineup": l["player_names"],
            })
        print_df(pd.DataFrame(rows))

    def cmd_archetype_synergy(args, db: NBADatabase):
        from .lineup_synergy import LineupSynergyModel
        import pandas as pd

        model = LineupSynergyModel(db=db)
        res = model.compute_archetype_synergy_matrix(season=args.season)

        print(f"\n=== 8x8 Pairwise Archetype Synergy Matrix (Season {args.season}) ===")
        print("Positive (+) = Complementary Skill Multiplication | Negative (-) = Skill Cannibalization\n")

        short_names = {
            "Versatile 3-and-D Wing": "3&D Wing",
            "Two-Way Mobile Big & Stretch Anchor": "Stretch Big",
            "Point-of-Attack Defensive Disruptor": "PoA Disrupt",
            "Heliocentric MVP Engine & Focal Hub": "Helio Engine",
            "Primary Playmaker / Floor General": "Playmaker",
            "Dynamic Shot Creator / Slasher": "Slasher",
            "Rim-Protecting Roll Anchor": "Roll Anchor",
            "3-and-D Movement Specialist": "3&D Shooter",
        }

        cols = [short_names.get(a, a) for a in res["archetypes"]]
        matrix_data = []
        for row in res["matrix"]:
            row_dict = {"Archetype": short_names.get(row["archetype"], row["archetype"])}
            for col_name, val in zip(cols, row["synergies"]):
                row_dict[col_name] = f"{val:+.2f}"
            matrix_data.append(row_dict)

        print_df(pd.DataFrame(matrix_data))

    def cmd_trade_fit(args, db: NBADatabase):
        from .lineup_synergy import LineupSynergyModel
        import pandas as pd
        import sys
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")

        players = [p.strip() for p in args.lineup.split(",") if p.strip()]
        model = LineupSynergyModel(db=db)
        res = model.evaluate_trade_fit(
            target_player=args.target.strip(),
            current_lineup=players,
            replaced_player=args.replace.strip(),
            season=args.season
        )

        if "error" in res:
            print(f"Error evaluating trade fit: {res['error']}")
            return

        print(f"\n=== 🔄 Trade / Free Agency Chemistry Evaluation ({args.season}) ===")
        print(f" Outgoing: {res['replaced_player']}")
        print(f" Incoming: {res['target_player']}")
        print(f" Verdict: {res['synergy_verdict']}")
        print(f" Marginal Net Rating Delta: {res['delta_predicted_net_rating']:+.2f} pts/100 poss")
        print(f" Marginal Chemistry Synergy Delta: {res['delta_total_synergy']:+.2f}")
        print(f" Marginal Raw Talent Delta: {res['delta_raw_lebron_sum']:+.2f}")

    def cmd_cap_sheet(args, db: NBADatabase):
        import pandas as pd
        from .capology_ingestion import CapologyIngestion
        ing = CapologyIngestion(db=db)
        tabbr = args.team.upper().strip()
        sheet = ing.recalculate_team_cap_sheet(tabbr, season=args.season)

        print(f"\n=== 💰 Team Salary Cap Sheet: {tabbr} ({args.season}) ===")
        print(f" Total Payroll Allocations: ${sheet['total_payroll']/1e6:.2f}M")
        print(f"   - Active Roster Salary : ${sheet['active_salary']/1e6:.2f}M")
        print(f"   - Dead Money           : ${sheet['dead_money']/1e6:.2f}M")
        print(f" Cap Status Tier          : {sheet['tier']}")
        print(f" Cap Space                : ${sheet['cap_space']/1e6:.2f}M")
        print(f" Luxury Tax Room          : ${sheet['tax_room']/1e6:.2f}M")
        print(f" First Apron Room         : ${sheet['first_apron_room']/1e6:.2f}M")
        print(f" Second Apron Room        : ${sheet['second_apron_room']/1e6:.2f}M")
        print(f" Luxury Tax Bill          : ${sheet['tax_bill']/1e6:.2f}M ({'Repeater Rate' if sheet['is_repeater'] else 'Standard Rate'})")
        print(f" Total Franchise Expense  : ${sheet['total_team_cost']/1e6:.2f}M")

        if sheet["penalties"]:
            print("\n🚨 CBA Penalties & Restrictions:")
            for p in sheet["penalties"]:
                print(f"   * {p}")

        # List players
        contracts = db.execute_query(
            """
            SELECT pc.player_name, pc.contract_type, cy.cap_hit, cy.option_type
            FROM player_contracts pc
            JOIN contract_years cy ON pc.contract_id = cy.contract_id
            WHERE pc.team_abbreviation = ? AND cy.season = ? AND pc.is_active = 1
            ORDER BY cy.cap_hit DESC
            """,
            (tabbr, args.season)
        )
        if contracts:
            rows = []
            for r in contracts:
                rows.append({
                    "Player": r["player_name"],
                    "Contract Type": r["contract_type"],
                    "Cap Hit ($M)": f"${r['cap_hit']/1e6:.2f}M",
                    "Option": r["option_type"] or "-"
                })
            print_df(pd.DataFrame(rows), f"{tabbr} Roster Payroll Breakdown")

    def cmd_contract_values(args, db: NBADatabase):
        import pandas as pd
        from .contract_valuation import ContractValuationEngine
        eng = ContractValuationEngine(db=db)
        df = eng.get_valuation_leaderboard(
            season=args.season,
            team_abbreviation=args.team.upper().strip() if args.team else None,
            tier=args.tier,
            sort_by=args.sort,
            ascending=args.asc,
            limit=args.top
        )
        if df.empty:
            print("No contract records found matching query.")
            return

        rows = []
        for _, r in df.iterrows():
            rows.append({
                "Player": r["player_name"],
                "Team": r["team_abbreviation"],
                "Cap Hit ($M)": f"${r['cap_hit']/1e6:.2f}M",
                "WAR": f"{r['wins_added']:.1f}",
                "Market Val ($M)": f"${r['fair_market_value']/1e6:.2f}M",
                "Surplus ($M)": f"{r['surplus_value']/1e6:+.2f}M",
                "ROI %": f"{r['roi_pct']:.0f}%",
                "Tier": r["value_tier"]
            })
        print_df(pd.DataFrame(rows), f"NBA Contract Valuation Leaderboard ({args.season})")

    def cmd_simulate_trade(args, db: NBADatabase):
        from .trade_machine import TradeMachine
        teams_list = [t.strip().upper() for t in args.teams.split(",") if t.strip()]
        if len(teams_list) < 2:
            print("Error: Trade simulation requires at least 2 teams (e.g. --teams LAL,BOS).")
            return

        # Parse --send (e.g. LAL:2544,BOS:1628369)
        trade_payload = {"teams": {t: {"sending_player_ids": []} for t in teams_list}}
        for pair in args.send.split(","):
            if ":" in pair:
                tabbr, pid_str = pair.split(":", 1)
                tabbr = tabbr.strip().upper()
                if tabbr in trade_payload["teams"]:
                    try:
                        trade_payload["teams"][tabbr]["sending_player_ids"].append(int(pid_str.strip()))
                    except ValueError:
                        pass

        tm = TradeMachine(db=db)
        res = tm.simulate_trade(trade_data=trade_payload, season=args.season)

        print(f"\n=== 🔄 2023 CBA Trade Machine Simulation ({args.season}) ===")
        print(f" Status  : {'✅ PASS - 100% CBA LEGAL' if res['is_valid'] else '❌ FAIL - CBA VIOLATION DETECTED'}")
        print(f" Summary : {res['summary']}\n")

        for tabbr, tr in res["team_results"].items():
            print(f"--- Team: {tabbr} [{'PASS' if tr['is_valid'] else 'FAIL'}] ---")
            print(f" Rule Applied     : {tr['cba_rule_applied']}")
            print(f" Outgoing Salary  : ${tr['outgoing_salary']/1e6:.2f}M")
            print(f" Incoming Salary  : ${tr['incoming_salary']/1e6:.2f}M (Max allowed: ${tr['max_allowed_incoming']/1e6:.2f}M)")
            print(f" Net Salary Delta : ${tr['net_salary_change']/1e6:+.2f}M")
            print(f" Payroll Impact   : ${tr['pre_trade_payroll']/1e6:.2f}M -> ${tr['post_trade_payroll']/1e6:.2f}M")
            print(f" Tax Bill Impact  : ${tr['pre_trade_tax']/1e6:.2f}M -> ${tr['post_trade_tax']/1e6:.2f}M (${tr['tax_difference']/1e6:+.2f}M)")
            print(f" Cap Tier Status  : {tr['pre_trade_tier']} -> {tr['post_trade_tier']}")
            if tr["generated_tpe"] > 0:
                print(f" 🎟️ Generated TPE : ${tr['generated_tpe']/1e6:.2f}M")

            if tr["violations"]:
                print(" ❌ Violations:")
                for v in tr["violations"]:
                    print(f"    * {v}")
            if tr["warnings"]:
                print(" ⚠️ Notices & Warnings:")
                for w in tr["warnings"]:
                    print(f"    * {w}")
            print()

    def cmd_tax_bill(args, db: NBADatabase):
        import pandas as pd
        from .capology_ingestion import CapologyIngestion
        ing = CapologyIngestion(db=db)
        tabbr = args.team.upper().strip()
        sheet = ing.recalculate_team_cap_sheet(tabbr, season=args.season)

        print(f"\n=== 🏛️ Progressive Luxury Tax Breakdown: {tabbr} ({args.season}) ===")
        print(f" Total Payroll    : ${sheet['total_payroll']/1e6:.2f}M")
        print(f" Repeater Status  : {'Yes (Repeater Tax Rates Apply)' if sheet['is_repeater'] else 'No (Standard Tax Rates)'}")
        print(f" Total Tax Bill   : ${sheet['tax_bill']/1e6:.2f}M")
        print(f" Total Cash Outlay: ${sheet['total_team_cost']/1e6:.2f}M\n")

        if sheet["tax_breakdown"]:
            print_df(pd.DataFrame(sheet["tax_breakdown"]), "Tax Bracket Breakdown")
        else:
            print("Team is below the Luxury Tax threshold. No luxury tax owed.")

    def cmd_seed_capology(args, db: NBADatabase):
        from .capology_ingestion import CapologyIngestion
        ing = CapologyIngestion(db=db)
        print("Seeding Capology contracts, cap settings, and team payroll sheets...")
        counts = ing.seed_from_file(args.file)
        print(f"Capology seeding complete! Results: {counts}")

    commands = {
        "init": cmd_init,
        "status": cmd_status,
        "populate": cmd_populate,
        "top-scorers": cmd_top_scorers,
        "standings": cmd_standings,
        "player-logs": cmd_player_logs,
        "compare-players": cmd_compare_players,
        "compare-teams": cmd_compare_teams,
        "high-scores": cmd_high_scores,
        "triple-doubles": cmd_triple_doubles,
        "h2h": cmd_h2h,
        "sql": cmd_sql,
        "serve": cmd_serve,
        "endpoints-list": cmd_endpoints_list,
        "download-endpoints": cmd_download_endpoints,
        "endpoint-info": cmd_endpoint_info,
        "validate": cmd_validate,
        "live-scores": cmd_live_scores,
        "live-poll": cmd_live_poll,
        "lebron": cmd_lebron,
        "compute-lebron": cmd_compute_lebron,
        "train-lebron": cmd_train_lebron,
        "cluster-positions": cmd_cluster_positions,
        "evaluate-lineup": cmd_evaluate_lineup,
        "optimize-team-lineup": cmd_optimize_team_lineup,
        "archetype-synergy": cmd_archetype_synergy,
        "trade-fit": cmd_trade_fit,
        "cap-sheet": cmd_cap_sheet,
        "contract-values": cmd_contract_values,
        "simulate-trade": cmd_simulate_trade,
        "tax-bill": cmd_tax_bill,
        "seed-capology": cmd_seed_capology,
    }

    if args.command in commands:
        commands[args.command](args, db)
    else:
        parser.print_help()



if __name__ == "__main__":
    main()
