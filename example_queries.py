import sys
from tabulate import tabulate
from nba_stats_db import NBADatabase, NBAQueryHelper

# Ensure UTF-8 output in Windows consoles for international player names (e.g., Dončić, Jokić)
if sys.stdout.encoding != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def display(df, title):
    print(f"\n{'='*20} {title} {'='*20}")
    if df.empty:
        print("No results.")
    else:
        print(tabulate(df, headers="keys", tablefmt="psql", showindex=False))


def run_examples():
    db = NBADatabase()
    helper = NBAQueryHelper(db=db)

    print("Checking database table summary...")
    counts = db.get_table_counts()
    for tbl, cnt in counts.items():
        print(f"  {tbl:20s}: {cnt:,} rows")

    # Example 1: Top 5 Scorers (2023-24)
    top_scorers = helper.get_top_scorers(season="2023-24", limit=5)
    display(top_scorers, "Top 5 Scorers (2023-24)")

    # Example 2: Eastern Conference Standings
    east_standings = helper.get_standings(season="2023-24", conference="East")
    display(east_standings.head(5), "East Top 5 Seeds (2023-24)")

    # Example 3: Luka Dončić Game Logs
    luka_logs = helper.get_player_game_logs("Luka Doncic", limit=5)
    display(luka_logs, "Luka Dončić Last 5 Games")

    # Example 4: Highest Single Game Scoring Performances
    high_games = helper.get_highest_scoring_games(limit=5)
    display(high_games, "Top 5 Single-Game Scoring Outbursts")

    # Example 5: Custom Advanced SQL Query (Team Net Rating & Scoring Margin)
    custom_sql = """
    SELECT 
        t.full_name AS Team,
        COUNT(g.id) AS GamesPlayed,
        ROUND(AVG(g.pts), 1) AS AvgPTS,
        ROUND(AVG(g.fg_pct) * 100, 1) AS `AvgFG%`,
        ROUND(AVG(g.fg3_pct) * 100, 1) AS `Avg3P%`,
        ROUND(AVG(g.plus_minus), 2) AS `Avg+/-`
    FROM team_game_logs g
    JOIN teams t ON g.team_id = t.team_id
    GROUP BY t.team_id
    ORDER BY `Avg+/-` DESC
    LIMIT 5;
    """
    team_perf = helper.execute_sql(custom_sql)
    display(team_perf, "Top 5 Teams by Average Point Differential (+/-)")


if __name__ == "__main__":
    run_examples()
