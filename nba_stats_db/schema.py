"""
schema.py - SQLite schema definitions, DDL statements, and indexes for NBA Stats DB.
"""

SCHEMA_DDL = """
-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    abbreviation TEXT NOT NULL,
    nickname TEXT,
    city TEXT,
    state TEXT,
    year_founded INTEGER
);

-- Players table
CREATE TABLE IF NOT EXISTS players (
    player_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    is_active INTEGER DEFAULT 0
);

-- Games table
CREATE TABLE IF NOT EXISTS games (
    game_id TEXT PRIMARY KEY,
    season_id TEXT,
    season_type TEXT,
    game_date TEXT,
    matchup TEXT,
    home_team_id INTEGER REFERENCES teams(team_id),
    visitor_team_id INTEGER REFERENCES teams(team_id),
    home_team_pts INTEGER,
    visitor_team_pts INTEGER,
    winner_team_id INTEGER REFERENCES teams(team_id)
);

-- Player Game Logs
CREATE TABLE IF NOT EXISTS player_game_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL REFERENCES games(game_id),
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    game_date TEXT,
    matchup TEXT,
    wl TEXT,
    min REAL,
    fgm REAL,
    fga REAL,
    fg_pct REAL,
    fg3m REAL,
    fg3a REAL,
    fg3_pct REAL,
    ftm REAL,
    fta REAL,
    ft_pct REAL,
    oreb REAL,
    dreb REAL,
    reb REAL,
    ast REAL,
    stl REAL,
    blk REAL,
    tov REAL,
    pf REAL,
    pts REAL,
    plus_minus REAL,
    video_available INTEGER DEFAULT 0,
    UNIQUE(player_id, game_id)
);

-- Team Game Logs
CREATE TABLE IF NOT EXISTS team_game_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    game_id TEXT NOT NULL REFERENCES games(game_id),
    game_date TEXT,
    matchup TEXT,
    wl TEXT,
    min REAL,
    fgm REAL,
    fga REAL,
    fg_pct REAL,
    fg3m REAL,
    fg3a REAL,
    fg3_pct REAL,
    ftm REAL,
    fta REAL,
    ft_pct REAL,
    oreb REAL,
    dreb REAL,
    reb REAL,
    ast REAL,
    stl REAL,
    blk REAL,
    tov REAL,
    pf REAL,
    pts REAL,
    plus_minus REAL,
    video_available INTEGER DEFAULT 0,
    UNIQUE(team_id, game_id)
);

-- Player Season Stats (Totals and per-game averages)
CREATE TABLE IF NOT EXISTS player_season_stats (
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    season TEXT NOT NULL,
    season_type TEXT NOT NULL,
    team_id INTEGER REFERENCES teams(team_id),
    team_abbreviation TEXT,
    age REAL,
    gp INTEGER,
    w INTEGER,
    l INTEGER,
    min REAL,
    fgm REAL,
    fga REAL,
    fg_pct REAL,
    fg3m REAL,
    fg3a REAL,
    fg3_pct REAL,
    ftm REAL,
    fta REAL,
    ft_pct REAL,
    oreb REAL,
    dreb REAL,
    reb REAL,
    ast REAL,
    tov REAL,
    stl REAL,
    blk REAL,
    pf REAL,
    pts REAL,
    plus_minus REAL,
    PRIMARY KEY (player_id, season, season_type)
);

-- Team Season Stats (Standings & records)
CREATE TABLE IF NOT EXISTS team_season_stats (
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    season TEXT NOT NULL,
    season_type TEXT NOT NULL,
    conference TEXT,
    division TEXT,
    w INTEGER,
    l INTEGER,
    win_pct REAL,
    conf_rank INTEGER,
    div_rank INTEGER,
    home_record TEXT,
    road_record TEXT,
    l10 TEXT,
    strk TEXT,
    pts REAL,
    opp_pts REAL,
    diff REAL,
    PRIMARY KEY (team_id, season, season_type)
);

-- Player Advanced Stats
CREATE TABLE IF NOT EXISTS player_advanced_stats (
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    season TEXT NOT NULL,
    season_type TEXT NOT NULL,
    team_id INTEGER REFERENCES teams(team_id),
    team_abbreviation TEXT,
    age REAL,
    gp INTEGER,
    min REAL,
    off_rating REAL,
    def_rating REAL,
    net_rating REAL,
    ast_pct REAL,
    ast_to REAL,
    ast_ratio REAL,
    oreb_pct REAL,
    dreb_pct REAL,
    reb_pct REAL,
    tm_tov_pct REAL,
    efg_pct REAL,
    ts_pct REAL,
    usg_pct REAL,
    pace REAL,
    pie REAL,
    poss REAL,
    PRIMARY KEY (player_id, season, season_type)
);

-- Team Advanced Stats
CREATE TABLE IF NOT EXISTS team_advanced_stats (
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    season TEXT NOT NULL,
    season_type TEXT NOT NULL,
    gp INTEGER,
    w INTEGER,
    l INTEGER,
    w_pct REAL,
    min REAL,
    off_rating REAL,
    def_rating REAL,
    net_rating REAL,
    ast_pct REAL,
    ast_to REAL,
    ast_ratio REAL,
    oreb_pct REAL,
    dreb_pct REAL,
    reb_pct REAL,
    tm_tov_pct REAL,
    efg_pct REAL,
    ts_pct REAL,
    pace REAL,
    pie REAL,
    PRIMARY KEY (team_id, season, season_type)
);

-- Player Profiles (Historical & Career Info)
CREATE TABLE IF NOT EXISTS player_profiles (
    player_id INTEGER PRIMARY KEY REFERENCES players(player_id),
    display_first_last TEXT,
    roster_status TEXT,
    from_year INTEGER,
    to_year INTEGER,
    team_id INTEGER REFERENCES teams(team_id),
    team_city TEXT,
    team_name TEXT,
    team_abbreviation TEXT
);

-- Indexes for optimal query performance
CREATE INDEX IF NOT EXISTS idx_players_name ON players(full_name);
CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date);
CREATE INDEX IF NOT EXISTS idx_games_season ON games(season_id);
CREATE INDEX IF NOT EXISTS idx_pgl_player ON player_game_logs(player_id);
CREATE INDEX IF NOT EXISTS idx_pgl_game ON player_game_logs(game_id);
CREATE INDEX IF NOT EXISTS idx_pgl_date ON player_game_logs(game_date);
CREATE INDEX IF NOT EXISTS idx_pgl_pts ON player_game_logs(pts);
CREATE INDEX IF NOT EXISTS idx_tgl_team ON team_game_logs(team_id);
CREATE INDEX IF NOT EXISTS idx_tgl_game ON team_game_logs(game_id);
CREATE INDEX IF NOT EXISTS idx_pss_season ON player_season_stats(season, season_type);
CREATE INDEX IF NOT EXISTS idx_tss_season ON team_season_stats(season, season_type);
CREATE INDEX IF NOT EXISTS idx_pas_season ON player_advanced_stats(season, season_type);
CREATE INDEX IF NOT EXISTS idx_tas_season ON team_advanced_stats(season, season_type);

-- NBA API Endpoints Catalog Table
CREATE TABLE IF NOT EXISTS nba_api_endpoints_catalog (
    endpoint_name TEXT PRIMARY KEY,
    module TEXT NOT NULL,
    category TEXT NOT NULL,
    docstring TEXT,
    required_params TEXT,
    default_params TEXT,
    status TEXT DEFAULT 'PENDING',
    result_sets_count INTEGER DEFAULT 0,
    total_rows INTEGER DEFAULT 0,
    table_names TEXT,
    last_downloaded_at TEXT,
    error_message TEXT
);

-- Endpoint Datasets Metadata Table
CREATE TABLE IF NOT EXISTS endpoint_datasets_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint_name TEXT NOT NULL REFERENCES nba_api_endpoints_catalog(endpoint_name),
    dataset_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    row_count INTEGER DEFAULT 0,
    columns_json TEXT,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_ep_cat_status ON nba_api_endpoints_catalog(status);
CREATE INDEX IF NOT EXISTS idx_ep_cat_category ON nba_api_endpoints_catalog(category);
CREATE INDEX IF NOT EXISTS idx_ep_meta_endpoint ON endpoint_datasets_meta(endpoint_name);

-- Live Game Scoreboard Table
CREATE TABLE IF NOT EXISTS live_scoreboard (
    game_id TEXT PRIMARY KEY,
    game_code TEXT,
    game_status INTEGER,
    game_status_text TEXT,
    period INTEGER,
    game_clock TEXT,
    home_team_id INTEGER,
    home_team_name TEXT,
    home_team_tricode TEXT,
    home_team_score INTEGER,
    away_team_id INTEGER,
    away_team_name TEXT,
    away_team_tricode TEXT,
    away_team_score INTEGER,
    game_leaders_json TEXT,
    raw_game_json TEXT,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_live_status ON live_scoreboard(game_status);

-- Box LEBRON Ratings Table
CREATE TABLE IF NOT EXISTS box_lebron_ratings (
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    season TEXT NOT NULL,
    season_type TEXT NOT NULL,
    player_name TEXT NOT NULL,
    team_abbreviation TEXT,
    age REAL,
    gp INTEGER,
    min REAL,
    possessions REAL,
    offensive_archetype TEXT,
    defensive_archetype TEXT,
    o_lebron REAL,
    d_lebron REAL,
    box_lebron REAL,
    wins_added REAL,
    o_lebron_percentile REAL,
    d_lebron_percentile REAL,
    box_lebron_percentile REAL,
    usage_pct REAL,
    ts_pct REAL,
    ast_pct REAL,
    reb_pct REAL,
    stl_pct REAL,
    blk_pct REAL,
    rim_defense_diff REAL,
    deflections_per_100 REAL,
    updated_at TEXT,
    PRIMARY KEY (player_id, season, season_type)
);

CREATE INDEX IF NOT EXISTS idx_blr_season ON box_lebron_ratings(season, season_type);
CREATE INDEX IF NOT EXISTS idx_blr_box_lebron ON box_lebron_ratings(box_lebron);
CREATE INDEX IF NOT EXISTS idx_blr_wins_added ON box_lebron_ratings(wins_added);
CREATE INDEX IF NOT EXISTS idx_blr_o_archetype ON box_lebron_ratings(offensive_archetype);
CREATE INDEX IF NOT EXISTS idx_blr_d_archetype ON box_lebron_ratings(defensive_archetype);

-- Unsupervised Player Position Clusters Table
CREATE TABLE IF NOT EXISTS player_position_clusters (
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    season TEXT NOT NULL,
    season_type TEXT NOT NULL,
    player_name TEXT NOT NULL,
    team_abbreviation TEXT,
    gp INTEGER,
    min REAL,
    cluster_id INTEGER NOT NULL,
    cluster_name TEXT NOT NULL,
    tsne_x REAL,
    tsne_y REAL,
    tsne_z REAL,
    usg_pct REAL,
    ts_pct REAL,
    ast_pct REAL,
    reb_pct REAL,
    oreb_pct REAL,
    dreb_pct REAL,
    fg3a_rate REAL,
    stl_per_36 REAL,
    blk_per_36 REAL,
    box_lebron REAL,
    o_lebron REAL,
    d_lebron REAL,
    updated_at TEXT,
    PRIMARY KEY (player_id, season, season_type)
);

CREATE INDEX IF NOT EXISTS idx_ppc_season ON player_position_clusters(season, season_type);
CREATE INDEX IF NOT EXISTS idx_ppc_cluster ON player_position_clusters(cluster_id);
CREATE INDEX IF NOT EXISTS idx_ppc_cluster_name ON player_position_clusters(cluster_name);

-- Team Lineup Synergy & Composition Evaluations Table
CREATE TABLE IF NOT EXISTS team_lineup_evaluations (
    lineup_id TEXT NOT NULL,
    season TEXT NOT NULL,
    season_type TEXT NOT NULL DEFAULT 'Regular Season',
    team_abbreviation TEXT,
    player_names TEXT NOT NULL,
    player_ids TEXT NOT NULL,
    archetype_mix TEXT NOT NULL,
    raw_lebron_sum REAL NOT NULL,
    offensive_synergy REAL NOT NULL,
    defensive_synergy REAL NOT NULL,
    usage_penalty REAL NOT NULL,
    spacing_rating REAL NOT NULL,
    predicted_net_rating REAL NOT NULL,
    balance_grade TEXT NOT NULL,
    evaluation_json TEXT,
    updated_at TEXT,
    PRIMARY KEY (lineup_id, season, season_type)
);

CREATE INDEX IF NOT EXISTS idx_tle_season ON team_lineup_evaluations(season, season_type);
CREATE INDEX IF NOT EXISTS idx_tle_team ON team_lineup_evaluations(team_abbreviation);
CREATE INDEX IF NOT EXISTS idx_tle_net_rtg ON team_lineup_evaluations(predicted_net_rating);
CREATE INDEX IF NOT EXISTS idx_tle_grade ON team_lineup_evaluations(balance_grade);
"""

# Import Capology DDL
try:
    from .capology_schema import CAPOLOGY_SCHEMA_DDL, CAPOLOGY_INDEXES_DDL
    SCHEMA_DDL = SCHEMA_DDL + "\n" + CAPOLOGY_SCHEMA_DDL + "\n" + CAPOLOGY_INDEXES_DDL
except ImportError:
    pass

