"""
populate_historical_aggregates.py - Aggregates historical game logs into player_season_stats
for all seasons prior to 1996-97 so that season-level queries and comparisons work seamlessly
across all 79 NBA seasons (1946-2025).
"""

import sys
import time
from nba_stats_db.database import NBADatabase

if sys.stdout.encoding != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def populate_historical_aggregates():
    db = NBADatabase()
    print("=" * 60)
    print("Populating player_season_stats from player_game_logs for pre-1996 seasons...")
    print("=" * 60)
    
    start_time = time.time()
    sql = """
    INSERT OR IGNORE INTO player_season_stats (
        player_id,
        season,
        season_type,
        team_id,
        team_abbreviation,
        gp,
        w,
        l,
        min,
        fgm,
        fga,
        fg_pct,
        fg3m,
        fg3a,
        fg3_pct,
        ftm,
        fta,
        ft_pct,
        oreb,
        dreb,
        reb,
        ast,
        tov,
        stl,
        blk,
        pf,
        pts,
        plus_minus
    )
    SELECT 
        l.player_id,
        CASE 
            WHEN length(g.season_id) = 5 THEN substr(g.season_id, 2, 4) || '-' || substr(cast(cast(substr(g.season_id, 2, 4) as integer) + 1 as text), 3, 2)
            ELSE g.season_id
        END AS season,
        g.season_type,
        l.team_id,
        MAX(t.abbreviation) AS team_abbreviation,
        COUNT(l.id) AS gp,
        SUM(CASE WHEN l.wl = 'W' THEN 1 ELSE 0 END) AS w,
        SUM(CASE WHEN l.wl = 'L' THEN 1 ELSE 0 END) AS l,
        ROUND(AVG(l.min), 1) AS min,
        ROUND(AVG(l.fgm), 1) AS fgm,
        ROUND(AVG(l.fga), 1) AS fga,
        ROUND(SUM(l.fgm) * 1.0 / NULLIF(SUM(l.fga), 0), 3) AS fg_pct,
        ROUND(AVG(l.fg3m), 1) AS fg3m,
        ROUND(AVG(l.fg3a), 1) AS fg3a,
        ROUND(SUM(l.fg3m) * 1.0 / NULLIF(SUM(l.fg3a), 0), 3) AS fg3_pct,
        ROUND(AVG(l.ftm), 1) AS ftm,
        ROUND(AVG(l.fta), 1) AS fta,
        ROUND(SUM(l.ftm) * 1.0 / NULLIF(SUM(l.fta), 0), 3) AS ft_pct,
        ROUND(AVG(l.oreb), 1) AS oreb,
        ROUND(AVG(l.dreb), 1) AS dreb,
        ROUND(AVG(l.reb), 1) AS reb,
        ROUND(AVG(l.ast), 1) AS ast,
        ROUND(AVG(l.tov), 1) AS tov,
        ROUND(AVG(l.stl), 1) AS stl,
        ROUND(AVG(l.blk), 1) AS blk,
        ROUND(AVG(l.pf), 1) AS pf,
        ROUND(AVG(l.pts), 1) AS pts,
        ROUND(AVG(l.plus_minus), 1) AS plus_minus
    FROM player_game_logs l
    JOIN games g ON l.game_id = g.game_id
    LEFT JOIN teams t ON l.team_id = t.team_id
    WHERE cast(substr(g.season_id, 2, 4) as integer) < 1996
    GROUP BY l.player_id, season, g.season_type;
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        inserted = cursor.rowcount
        conn.commit()
        
    elapsed = round(time.time() - start_time, 2)
    print(f"Successfully inserted {inserted:,} historical player season stats in {elapsed}s.")
    
    # Check total player_season_stats now
    total = db.query_df("SELECT COUNT(*) as cnt FROM player_season_stats").iloc[0]["cnt"]
    distinct_seasons = db.query_df("SELECT COUNT(DISTINCT season) as cnt FROM player_season_stats").iloc[0]["cnt"]
    print(f"player_season_stats now has {total:,} rows across {distinct_seasons} distinct seasons!")

if __name__ == "__main__":
    populate_historical_aggregates()
