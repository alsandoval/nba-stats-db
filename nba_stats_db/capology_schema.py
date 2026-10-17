"""
capology_schema.py - Schema definitions, DDL statements, and indexes for NBA Capology,
Contracts, Luxury Tax, and Trade Simulation.
"""

CAPOLOGY_SCHEMA_DDL = """
-- CBA Cap Settings per season
CREATE TABLE IF NOT EXISTS cba_cap_settings (
    season TEXT PRIMARY KEY,
    salary_cap REAL NOT NULL,
    tax_level REAL NOT NULL,
    first_apron REAL NOT NULL,
    second_apron REAL NOT NULL,
    min_team_salary REAL NOT NULL,
    tax_bracket_size REAL DEFAULT 5000000.0,
    nontaxpayer_mle REAL DEFAULT 12822000.0,
    taxpayer_mle REAL DEFAULT 5168000.0,
    room_mle REAL DEFAULT 7983000.0,
    biannual_exception REAL DEFAULT 4668000.0,
    cost_per_win REAL DEFAULT 3500000.0
);

-- Master Player Contracts
CREATE TABLE IF NOT EXISTS player_contracts (
    contract_id TEXT PRIMARY KEY,
    player_id INTEGER REFERENCES players(player_id),
    player_name TEXT NOT NULL,
    team_id INTEGER REFERENCES teams(team_id),
    team_abbreviation TEXT NOT NULL,
    total_years INTEGER NOT NULL DEFAULT 1,
    total_value REAL NOT NULL DEFAULT 0.0,
    contract_type TEXT DEFAULT 'Standard',
    signed_using TEXT DEFAULT 'Bird Rights',
    bird_rights TEXT DEFAULT 'Full Bird',
    trade_kicker_pct REAL DEFAULT 0.0,
    poison_pill INTEGER DEFAULT 0,
    no_trade_clause INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);

-- Contract Breakdown by Season
CREATE TABLE IF NOT EXISTS contract_years (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id TEXT NOT NULL REFERENCES player_contracts(contract_id) ON DELETE CASCADE,
    season TEXT NOT NULL,
    base_salary REAL NOT NULL,
    cap_hit REAL NOT NULL,
    guaranteed_amount REAL NOT NULL,
    option_type TEXT DEFAULT NULL,
    is_guaranteed INTEGER DEFAULT 1,
    UNIQUE(contract_id, season)
);

-- Team Cap Sheets per Season
CREATE TABLE IF NOT EXISTS team_cap_sheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    team_abbreviation TEXT NOT NULL,
    season TEXT NOT NULL,
    active_salary REAL DEFAULT 0.0,
    dead_money REAL DEFAULT 0.0,
    total_cap_allocations REAL DEFAULT 0.0,
    cap_space REAL DEFAULT 0.0,
    tax_room REAL DEFAULT 0.0,
    first_apron_room REAL DEFAULT 0.0,
    second_apron_room REAL DEFAULT 0.0,
    tax_bill REAL DEFAULT 0.0,
    is_repeater INTEGER DEFAULT 0,
    hard_capped_at TEXT DEFAULT NULL,
    updated_at TEXT,
    UNIQUE(team_id, season)
);

-- Traded Player Exceptions (TPE)
CREATE TABLE IF NOT EXISTS trade_exceptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    team_abbreviation TEXT NOT NULL,
    amount REAL NOT NULL,
    created_season TEXT NOT NULL,
    expires_date TEXT,
    source_player TEXT,
    notes TEXT,
    UNIQUE(team_abbreviation, source_player, created_season)
);

-- Dead Money (Waived / Stretched contracts)
CREATE TABLE IF NOT EXISTS dead_money (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    team_abbreviation TEXT NOT NULL,
    player_name TEXT NOT NULL,
    season TEXT NOT NULL,
    amount REAL NOT NULL,
    is_stretched INTEGER DEFAULT 0,
    notes TEXT,
    UNIQUE(team_abbreviation, player_name, season)
);

-- Saved Simulation Scenarios (Sandbox)
CREATE TABLE IF NOT EXISTS cap_scenarios (
    scenario_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    state_json TEXT NOT NULL,
    created_at TEXT,
    updated_at TEXT
);
"""

CAPOLOGY_INDEXES_DDL = """
CREATE INDEX IF NOT EXISTS idx_contracts_player ON player_contracts(player_id);
CREATE INDEX IF NOT EXISTS idx_contracts_team ON player_contracts(team_abbreviation);
CREATE INDEX IF NOT EXISTS idx_contract_years_season ON contract_years(season);
CREATE INDEX IF NOT EXISTS idx_contract_years_contract ON contract_years(contract_id);
CREATE INDEX IF NOT EXISTS idx_team_cap_sheets_season ON team_cap_sheets(season, team_abbreviation);
CREATE INDEX IF NOT EXISTS idx_trade_exceptions_team ON trade_exceptions(team_abbreviation);
CREATE INDEX IF NOT EXISTS idx_dead_money_team_season ON dead_money(team_abbreviation, season);
"""
