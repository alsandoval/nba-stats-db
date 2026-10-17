"""
ai_agent.py - Conversational AI Chart & Stats Agent powered by Google Gemini.
Translates natural language questions into safe SQLite queries, analytical commentary,
and custom declarative NBA Chart JSON DSL specs rendered by Chart.js on the frontend.
"""

import os
import re
import json
import logging
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from urllib import request as url_request
from urllib.error import HTTPError, URLError

from .database import NBADatabase

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an elite NBA Analytics AI Agent and Data Visualizer.
Your mission is to answer user questions about NBA statistics, players, and teams by generating:
1. A safe, read-only SQLite query to fetch the necessary data from the local database.
2. A declarative NBA Chart JSON DSL specification to visualize the data with high impact.
3. An insightful analytical narrative explaining what the data shows.

DATABASE SCHEMA:
- teams(team_id, full_name, abbreviation, nickname, city, state, year_founded)
- players(player_id, full_name, first_name, last_name, is_active)
- games(game_id, season_id, season_type, game_date, matchup, home_team_id, visitor_team_id, home_team_pts, visitor_team_pts, winner_team_id)
- player_season_stats(player_id, season, season_type, team_id, team_abbreviation, age, gp, w, l, min, fgm, fga, fg_pct, fg3m, fg3a, fg3_pct, ftm, fta, ft_pct, oreb, dreb, reb, ast, tov, stl, blk, pf, pts, plus_minus)
  * season format: '2023-24', '2022-23', etc.
  * season_type: 'Regular Season' or 'Playoffs'
- player_advanced_stats(player_id, season, season_type, team_id, team_abbreviation, age, gp, min, off_rating, def_rating, net_rating, ast_pct, ast_to, ast_ratio, oreb_pct, dreb_pct, reb_pct, tm_tov_pct, efg_pct, ts_pct, usg_pct, pace, pie, poss)
- team_season_stats(team_id, season, season_type, conference, division, w, l, win_pct, conf_rank, div_rank, home_record, road_record, l10, strk, pts, opp_pts, diff)
- team_advanced_stats(team_id, season, season_type, gp, w, l, w_pct, min, off_rating, def_rating, net_rating, ast_pct, ast_to, ast_ratio, oreb_pct, dreb_pct, reb_pct, tm_tov_pct, efg_pct, ts_pct, pace, pie)
- player_game_logs(id, game_id, player_id, team_id, game_date, matchup, wl, min, fgm, fga, fg_pct, fg3m, fg3a, fg3_pct, ftm, fta, ft_pct, oreb, dreb, reb, ast, stl, blk, tov, pf, pts, plus_minus)

QUERY GUIDELINES:
- ONLY generate a single read-only SELECT query. Never use INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA.
- Always filter by season (e.g. season = '2023-24' or latest available) unless the user asks for historical/multi-season trends.
- When comparing players, join players with player_season_stats (and player_advanced_stats if needed) on player_id.
- For player names, use `p.full_name` or `LIKE '%name%'`.
- Limit row counts reasonably (e.g. 5 to 25 rows for bar/radar charts, up to 50 for scatter).
- Include `team_abbreviation` or `t.abbreviation` whenever possible so the frontend can apply official team colors.

CHART DSL SPECIFICATION:
Your output MUST be a valid JSON object with the following structure:
{
  "chartType": "bar" | "horizontalBar" | "line" | "scatter" | "radar",
  "title": "Clear descriptive chart title",
  "subtitle": "Subtitle with season or metric details",
  "sqlQuery": "SELECT ...",
  "dimensions": {
    "labelKey": "column_for_x_labels_or_player_names",
    "teamKey": "column_for_team_abbreviation_or_null",
    "groupKey": "optional_column_for_grouping"
  },
  "metrics": [
    {
      "key": "column_name",
      "label": "Display Name (e.g. Points Per Game)",
      "format": "decimal1" | "percent" | "integer" | "rank",
      "axis": "y" | "y1"
    }
  ],
  "scatterConfig": { // ONLY when chartType is "scatter"
    "xMetric": { "key": "col_x", "label": "X Axis Label", "format": "decimal1" },
    "yMetric": { "key": "col_y", "label": "Y Axis Label", "format": "decimal1" },
    "labelKey": "player_or_team_name",
    "teamKey": "team_abbreviation"
  },
  "benchmarks": [
    {
      "metric": "column_name",
      "value": 0.58,
      "label": "League Avg (58.0%)",
      "color": "#f59e0b"
    }
  ],
  "narrative": "A concise, sharp 2-4 sentence analytical breakdown answering the user's question directly, highlighting key outliers, leaders, and takeaways."
}

CHART TYPE RECOMMENDATIONS:
- "bar": Comparing 1-3 metrics across 5-15 players/teams.
- "horizontalBar": Rankings with longer player names or 10+ entries (e.g. Top 10 Scorers).
- "line": Time series, game logs, or season-by-season progression.
- "scatter": Efficiency plots (e.g. Usage% vs True Shooting%, Offensive vs Defensive Rating, Pace vs Net Rating).
- "radar": Comparing 1 or 2 specific players across 4-6 diverse skill metrics (e.g. PTS, REB, AST, STL, BLK, TS%).

Ensure all JSON keys and values are strictly valid. Return ONLY the JSON object.
"""

# Curated out-of-the-box presets that work instantly even without an API key
PRESET_QUERIES: List[Dict[str, Any]] = [
    {
        "id": "top-pgs",
        "title": "Top Point Guards: Scoring & Efficiency",
        "prompt": "Compare the top 10 PGs this season by Points Per Game and True Shooting %",
        "chartSpec": {
            "chartType": "horizontalBar",
            "title": "Top 10 Point Guards: Scoring Volume vs Efficiency (2023-24)",
            "subtitle": "Points Per Game (PPG) with True Shooting % (TS%)",
            "sqlQuery": """
                SELECT p.full_name, s.pts, ROUND(a.ts_pct * 100, 1) as ts_pct, s.team_abbreviation, s.gp
                FROM player_season_stats s
                JOIN players p ON s.player_id = p.player_id
                JOIN player_advanced_stats a ON s.player_id = a.player_id AND s.season = a.season
                WHERE s.season = '2023-24' AND s.season_type = 'Regular Season'
                  AND s.gp >= 40
                  AND p.full_name IN (
                    'Luka Doncic', 'Shai Gilgeous-Alexander', 'Jalen Brunson', 'Stephen Curry',
                    'Tyrese Haliburton', 'Damian Lillard', 'De''Aaron Fox', 'Trae Young',
                    'Tyrese Maxey', 'Jamal Murray', 'Kyrie Irving'
                  )
                ORDER BY s.pts DESC
                LIMIT 10;
            """.strip(),
            "dimensions": {
                "labelKey": "full_name",
                "teamKey": "team_abbreviation"
            },
            "metrics": [
                {"key": "pts", "label": "Points Per Game", "format": "decimal1", "axis": "y"},
                {"key": "ts_pct", "label": "True Shooting %", "format": "percent", "axis": "y1"}
            ],
            "benchmarks": [
                {"metric": "ts_pct", "value": 58.0, "label": "League Avg TS% (58.0%)", "color": "#f59e0b"}
            ],
            "narrative": "Luka Dončić and Shai Gilgeous-Alexander headline the elite tier of point guards in 2023-24, combining massive 30+ PPG volume with well-above league average true shooting efficiency (58%+). Jalen Brunson and Tyrese Maxey demonstrated breakout All-NBA campaigns with heavy scoring burdens."
        }
    },
    {
        "id": "curry-vs-luka",
        "title": "Steph Curry vs Luka Dončić: 3PT Efficiency Progression",
        "prompt": "Compare Steph Curry and Luka Doncic 3PT% and 3PM across their seasons",
        "chartSpec": {
            "chartType": "line",
            "title": "Steph Curry vs Luka Dončić: 3PT% by Season",
            "subtitle": "Season-by-season 3-point shooting percentage",
            "sqlQuery": """
                SELECT p.full_name, s.season, ROUND(s.fg3_pct * 100, 1) as fg3_pct, s.fg3m, s.team_abbreviation
                FROM player_season_stats s
                JOIN players p ON s.player_id = p.player_id
                WHERE p.full_name IN ('Stephen Curry', 'Luka Doncic')
                  AND s.season_type = 'Regular Season'
                  AND s.season >= '2018-19'
                ORDER BY s.season ASC, p.full_name ASC;
            """.strip(),
            "dimensions": {
                "labelKey": "season",
                "groupKey": "full_name",
                "teamKey": "team_abbreviation"
            },
            "metrics": [
                {"key": "fg3_pct", "label": "3-Point %", "format": "percent", "axis": "y"}
            ],
            "benchmarks": [
                {"metric": "fg3_pct", "value": 36.6, "label": "NBA Average 3P% (36.6%)", "color": "#94a3b8"}
            ],
            "narrative": "Steph Curry maintains historically elite accuracy well above 40% even on astronomical volume. Luka Dončić has shown marked evolution, progressing from mid-30s in his early seasons to a career-best 38.2% in 2023-24 despite taking predominantly difficult step-back attempts."
        }
    },
    {
        "id": "pace-vs-net-rating",
        "title": "NBA Teams: Pace vs Net Rating",
        "prompt": "Show a scatter plot of Pace vs Net Rating for all NBA teams this season",
        "chartSpec": {
            "chartType": "scatter",
            "title": "Team Landscape: Pace vs Net Rating (2023-24)",
            "subtitle": "Possessions per 48 mins vs Point Differential per 100 possessions",
            "sqlQuery": """
                SELECT t.full_name, t.abbreviation, a.pace, a.net_rating, a.off_rating, a.def_rating
                FROM team_advanced_stats a
                JOIN teams t ON a.team_id = t.team_id
                WHERE a.season = '2023-24' AND a.season_type = 'Regular Season'
                ORDER BY a.net_rating DESC;
            """.strip(),
            "dimensions": {
                "labelKey": "full_name",
                "teamKey": "abbreviation"
            },
            "scatterConfig": {
                "xMetric": {"key": "pace", "label": "Pace (Poss / 48m)", "format": "decimal1"},
                "yMetric": {"key": "net_rating", "label": "Net Rating (Pts / 100 Poss)", "format": "decimal1"},
                "labelKey": "abbreviation",
                "teamKey": "abbreviation"
            },
            "benchmarks": [
                {"metric": "net_rating", "value": 0.0, "label": "Even Net Rating", "color": "#64748b"}
            ],
            "narrative": "The Boston Celtics dominate the league with a historic +11.6 net rating operating at a deliberate, calculated half-court pace (~97.5). Meanwhile, high-tempo run-and-gun teams like the Pacers pushed pace past 101 possessions with elite offensive firepower."
        }
    },
    {
        "id": "jokic-vs-embiid-radar",
        "title": "Jokić vs Embiid: MVP Skill Profile",
        "prompt": "Radar chart comparing Nikola Jokic and Joel Embiid on PTS, REB, AST, TS%, and Net Rating",
        "chartSpec": {
            "chartType": "radar",
            "title": "MVP Center Showdown: Nikola Jokić vs Joel Embiid (2023-24)",
            "subtitle": "Skill Profile across Primary & Advanced Metrics",
            "sqlQuery": """
                SELECT p.full_name, s.pts, s.reb, s.ast, ROUND(a.ts_pct * 100, 1) as ts_pct, a.net_rating, s.team_abbreviation
                FROM player_season_stats s
                JOIN players p ON s.player_id = p.player_id
                JOIN player_advanced_stats a ON s.player_id = a.player_id AND s.season = a.season
                WHERE p.full_name IN ('Nikola Jokic', 'Joel Embiid')
                  AND s.season = '2023-24' AND s.season_type = 'Regular Season';
            """.strip(),
            "dimensions": {
                "labelKey": "full_name",
                "teamKey": "team_abbreviation"
            },
            "metrics": [
                {"key": "pts", "label": "Points (PPG)", "format": "decimal1", "axis": "y"},
                {"key": "reb", "label": "Rebounds (RPG)", "format": "decimal1", "axis": "y"},
                {"key": "ast", "label": "Assists (APG)", "format": "decimal1", "axis": "y"},
                {"key": "ts_pct", "label": "True Shooting %", "format": "percent", "axis": "y"},
                {"key": "net_rating", "label": "Net Rating", "format": "decimal1", "axis": "y"}
            ],
            "benchmarks": [],
            "narrative": "Joel Embiid posted an absurd 34.7 PPG scoring rate with towering defensive presence, while Nikola Jokić orchestrated one of the most complete offensive machines in history, nearly averaging a 26-12-9 triple-double with a +11.8 net rating."
        }
    }
]


class NBAAIAgent:
    """Agent that converts user natural language prompts into SQL, charts, and analysis."""

    def __init__(self, db: Optional[NBADatabase] = None):
        self.db = db or NBADatabase()

    def get_api_key(self, provided_key: Optional[str] = None) -> Optional[str]:
        """Returns the Gemini API key from explicit arg, environment, or .env file."""
        if provided_key:
            return provided_key
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
            if os.path.exists(env_file):
                try:
                    with open(env_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line_s = line.strip()
                            if line_s.startswith("GEMINI_API_KEY="):
                                key = line_s.split("GEMINI_API_KEY=", 1)[1].strip().strip('"').strip("'")
                                os.environ["GEMINI_API_KEY"] = key
                                break
                except Exception as e:
                    logger.warning(f"Failed to read .env file: {e}")
        return key

    def validate_sql(self, sql: str) -> Tuple[bool, str]:
        """Validates that a query is strictly read-only and safe."""
        cleaned = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
        cleaned = re.sub(r"--.*?\n", "\n", cleaned)
        cleaned_stripped = cleaned.strip()

        # Check for empty query
        if not cleaned_stripped:
            return False, "Empty SQL query."

        # Reject multi-statement queries (semicolon followed by non-whitespace)
        statements = [s.strip() for s in cleaned_stripped.split(";") if s.strip()]
        if len(statements) > 1:
            return False, "Multiple SQL statements are not permitted."

        first_stmt = statements[0]
        # Must start with SELECT or WITH
        if not re.match(r"^(SELECT|WITH)\b", first_stmt, re.IGNORECASE):
            return False, "Only SELECT queries are allowed."

        # Disallow dangerous mutation keywords
        forbidden = [
            r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
            r"\bALTER\b", r"\bCREATE\b", r"\bATTACH\b", r"\bDETACH\b",
            r"\bPRAGMA\b", r"\bREPLACE\b", r"\bEXEC\b", r"\bVACUUM\b"
        ]
        for pattern in forbidden:
            if re.search(pattern, first_stmt, re.IGNORECASE):
                return False, f"Forbidden SQL keyword detected: {pattern}"

        return True, first_stmt

    def execute_query(self, sql: str, timeout_sec: float = 5.0) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """Executes a validated read-only SQL query against SQLite."""
        is_safe, sanitized_or_err = self.validate_sql(sql)
        if not is_safe:
            return None, sanitized_or_err

        sanitized_sql = sanitized_or_err

        # Ensure safety limit if none exists
        if not re.search(r"\bLIMIT\b", sanitized_sql, re.IGNORECASE):
            sanitized_sql = f"{sanitized_sql.rstrip(';')} LIMIT 100;"

        try:
            conn = sqlite3.connect(self.db.db_path, timeout=timeout_sec)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sanitized_sql)
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            conn.close()
            return result, None
        except sqlite3.OperationalError as e:
            logger.warning(f"SQL OperationalError: {e}")
            return None, f"Database error: {str(e)}"
        except sqlite3.DatabaseError as e:
            logger.error(f"SQL DatabaseError: {e}")
            return None, f"Database execution error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected SQL error: {e}")
            return None, f"Execution failed: {str(e)}"

    def call_gemini_api(
        self,
        prompt: str,
        api_key: str,
        model: str = "gemini-flash-latest",
        history: Optional[List[Dict[str, str]]] = None,
        system_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calls Google Gemini API via REST with structured JSON response."""
        # Clean model name if full path is passed
        model_name = model.replace("models/", "")
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

        # Build contents from history + current prompt
        contents = []
        if history:
            for msg in history:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}]
                })

        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = url_request.Request(
            endpoint,
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )

        try:
            with url_request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode("utf-8")
                resp_json = json.loads(resp_body)

                # Extract generated text
                candidates = resp_json.get("candidates", [])
                if not candidates:
                    raise ValueError("No candidate generated by Gemini.")

                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise ValueError("Empty response parts from Gemini.")

                raw_text = parts[0].get("text", "")
                parsed = json.loads(raw_text)
                return parsed
        except HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            logger.error(f"Gemini API HTTPError {e.code}: {err_msg}")
            raise RuntimeError(f"Gemini API error ({e.code}): {err_msg}")
        except URLError as e:
            logger.error(f"Gemini API URLError: {e.reason}")
            raise RuntimeError(f"Network error contacting Gemini: {e.reason}")

    def build_semantic_query(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Parses natural language prompts using domain-specific NBA heuristics
        to generate valid SQL queries, Chart DSL specs, and analytical narratives.
        Ensures charts get built reliably even without an external LLM API key.
        """
        prompt_norm = prompt.lower().replace("'", "").replace("’", "").strip()

        # Detect Season
        season_match = re.search(r"(\b20\d\d-\d\d\b)", prompt)
        season = season_match.group(1) if season_match else "2023-24"

        # Detect Limit
        limit_match = re.search(r"\btop\s+(\d+)\b", prompt_norm)
        limit = int(limit_match.group(1)) if limit_match else 10
        limit = max(3, min(limit, 30))

        # Position groups
        positions = {
            "pg": ("Point Guards", [
                "Luka Doncic", "Shai Gilgeous-Alexander", "Jalen Brunson", "Stephen Curry",
                "Tyrese Haliburton", "Damian Lillard", "De''Aaron Fox", "Trae Young",
                "Tyrese Maxey", "Jamal Murray", "Kyrie Irving", "Jrue Holiday",
                "Fred VanVleet", "Darius Garland"
            ]),
            "sg": ("Shooting Guards", [
                "Anthony Edwards", "Devin Booker", "Donovan Mitchell", "Jaylen Brown",
                "Derrick White", "CJ McCollum", "Tyler Herro", "Malik Monk",
                "Bogdan Bogdanovic", "Austin Reaves"
            ]),
            "sf": ("Small Forwards", [
                "Jayson Tatum", "LeBron James", "Kawhi Leonard", "Jimmy Butler",
                "Brandon Ingram", "Franz Wagner", "Mikal Bridges", "DeMar DeRozan",
                "Michael Porter Jr."
            ]),
            "pf": ("Power Forwards", [
                "Giannis Antetokounmpo", "Kevin Durant", "Zion Williamson", "Paolo Banchero",
                "Pascal Siakam", "Lauri Markkanen", "Julius Randle", "Kyle Kuzma"
            ]),
            "c": ("Centers", [
                "Nikola Jokic", "Joel Embiid", "Anthony Davis", "Domantas Sabonis",
                "Rudy Gobert", "Bam Adebayo", "Victor Wembanyama", "Chet Holmgren",
                "Jarrett Allen", "Alperen Sengun"
            ])
        }

        matched_pos_key = None
        if re.search(r"\b(pg|pgs|point guard|point guards)\b", prompt_norm):
            matched_pos_key = "pg"
        elif re.search(r"\b(sg|sgs|shooting guard|shooting guards)\b", prompt_norm):
            matched_pos_key = "sg"
        elif re.search(r"\b(sf|sfs|small forward|small forwards)\b", prompt_norm):
            matched_pos_key = "sf"
        elif re.search(r"\b(pf|pfs|power forward|power forwards)\b", prompt_norm):
            matched_pos_key = "pf"
        elif re.search(r"\b(c|centers|center|big men|big man)\b", prompt_norm):
            matched_pos_key = "c"

        # Check for 2 specific players head-to-head comparison
        known_players = [
            "Stephen Curry", "Luka Doncic", "Nikola Jokic", "Joel Embiid", "LeBron James",
            "Giannis Antetokounmpo", "Jayson Tatum", "Kevin Durant", "Shai Gilgeous-Alexander",
            "Anthony Edwards", "Devin Booker", "Donovan Mitchell", "Jaylen Brown", "Anthony Davis"
        ]
        found_players = []
        for kp in known_players:
            last_name = kp.split()[-1].lower()
            if kp.lower() in prompt_norm or last_name in prompt_norm:
                found_players.append(kp)

        if len(found_players) >= 2:
            p1, p2 = found_players[0], found_players[1]
            sql = f"""
                SELECT p.full_name, s.pts, s.reb, s.ast, ROUND(a.ts_pct * 100, 1) as ts_pct, a.net_rating, s.team_abbreviation
                FROM player_season_stats s
                JOIN players p ON s.player_id = p.player_id
                JOIN player_advanced_stats a ON s.player_id = a.player_id AND s.season = a.season
                WHERE p.full_name IN ('{p1}', '{p2}')
                  AND s.season = '{season}' AND s.season_type = 'Regular Season';
            """.strip()

            chart_spec = {
                "chartType": "radar",
                "title": f"Head-to-Head: {p1} vs {p2} ({season})",
                "subtitle": "Multi-Dimensional Skill Profile",
                "sqlQuery": sql,
                "dimensions": { "labelKey": "full_name", "teamKey": "team_abbreviation" },
                "metrics": [
                    {"key": "pts", "label": "Points (PPG)", "format": "decimal1", "axis": "y"},
                    {"key": "reb", "label": "Rebounds (RPG)", "format": "decimal1", "axis": "y"},
                    {"key": "ast", "label": "Assists (APG)", "format": "decimal1", "axis": "y"},
                    {"key": "ts_pct", "label": "True Shooting %", "format": "percent", "axis": "y"},
                    {"key": "net_rating", "label": "Net Rating", "format": "decimal1", "axis": "y"}
                ],
                "benchmarks": [],
                "narrative": f"Direct statistical showdown between {p1} and {p2} for the {season} season across scoring, rebounding, playmaking, efficiency, and overall team net impact."
            }
            return chart_spec

        # Check for single player career progression
        if len(found_players) == 1 and any(w in prompt_norm for w in ["career", "progression", "seasons", "history", "trend"]):
            p1 = found_players[0]
            sql = f"""
                SELECT p.full_name, s.season, s.pts, s.ast, s.reb, ROUND(s.fg3_pct * 100, 1) as fg3_pct, s.team_abbreviation
                FROM player_season_stats s
                JOIN players p ON s.player_id = p.player_id
                WHERE p.full_name = '{p1}' AND s.season_type = 'Regular Season'
                ORDER BY s.season ASC;
            """.strip()

            chart_spec = {
                "chartType": "line",
                "title": f"{p1}: Career Progression by Season",
                "subtitle": "Scoring (PPG) over time",
                "sqlQuery": sql,
                "dimensions": { "labelKey": "season", "teamKey": "team_abbreviation" },
                "metrics": [
                    {"key": "pts", "label": "Points Per Game", "format": "decimal1", "axis": "y"}
                ],
                "benchmarks": [],
                "narrative": f"Career scoring progression for {p1} across all regular seasons in the NBA database."
            }
            return chart_spec

        # Check for Team Analytics (Pace vs Net Rating or Standings)
        if any(w in prompt_norm for w in ["pace", "teams", "team", "standings"]):
            if "pace" in prompt_norm or "scatter" in prompt_norm:
                sql = f"""
                    SELECT t.full_name, t.abbreviation, a.pace, a.net_rating, a.off_rating, a.def_rating
                    FROM team_advanced_stats a
                    JOIN teams t ON a.team_id = t.team_id
                    WHERE a.season = '{season}' AND a.season_type = 'Regular Season'
                    ORDER BY a.net_rating DESC;
                """.strip()

                chart_spec = {
                    "chartType": "scatter",
                    "title": f"Team Analytics: Pace vs Net Rating ({season})",
                    "subtitle": "Pace (Possessions / 48m) vs Net Rating (Points Differential / 100 Poss)",
                    "sqlQuery": sql,
                    "dimensions": { "labelKey": "full_name", "teamKey": "abbreviation" },
                    "scatterConfig": {
                        "xMetric": {"key": "pace", "label": "Pace (Poss / 48m)", "format": "decimal1"},
                        "yMetric": {"key": "net_rating", "label": "Net Rating", "format": "decimal1"},
                        "labelKey": "abbreviation",
                        "teamKey": "abbreviation"
                    },
                    "benchmarks": [
                        {"metric": "net_rating", "value": 0.0, "label": "Even Net Rating", "color": "#64748b"}
                    ],
                    "narrative": f"Team efficiency landscape for {season}. Teams in the upper right quadrant combine high pace with positive net efficiency."
                }
                return chart_spec

        # General Player Metric Leaderboard
        primary_metric = "pts"
        primary_label = "Points Per Game"
        primary_format = "decimal1"
        has_secondary = False

        if any(w in prompt_norm for w in ["assist", "apg", "playmaking", "passing"]):
            primary_metric = "ast"
            primary_label = "Assists Per Game"
        elif any(w in prompt_norm for w in ["rebound", "rpg", "boards"]):
            primary_metric = "reb"
            primary_label = "Rebounds Per Game"
        elif any(w in prompt_norm for w in ["3pt", "3-point", "three point", "3pm", "triples"]):
            primary_metric = "fg3m"
            primary_label = "3-Pointers Made"
        elif any(w in prompt_norm for w in ["steal", "stl"]):
            primary_metric = "stl"
            primary_label = "Steals Per Game"
        elif any(w in prompt_norm for w in ["block", "blk"]):
            primary_metric = "blk"
            primary_label = "Blocks Per Game"

        # Check for secondary efficiency metric (e.g. TS% or FG%)
        sec_metric = None
        if any(w in prompt_norm for w in ["ts%", "true shooting", "efficiency", "ts"]):
            has_secondary = True
            sec_metric = {"key": "ts_pct", "label": "True Shooting %", "format": "percent", "axis": "y1"}

        pos_title = "NBA"
        pos_filter = ""
        if matched_pos_key:
            pos_label, player_list = positions[matched_pos_key]
            pos_title = pos_label
            quoted_players = ", ".join(f"'{p}'" for p in player_list)
            pos_filter = f"AND p.full_name IN ({quoted_players})"

        metrics = [{"key": primary_metric, "label": primary_label, "format": primary_format, "axis": "y"}]
        benchmarks = []

        if has_secondary and sec_metric:
            metrics.append(sec_metric)
            benchmarks.append({"metric": "ts_pct", "value": 58.0, "label": "League Avg TS% (58.0%)", "color": "#f59e0b"})

        sql = f"""
            SELECT p.full_name, s.{primary_metric}, ROUND(a.ts_pct * 100, 1) as ts_pct, s.team_abbreviation, s.gp
            FROM player_season_stats s
            JOIN players p ON s.player_id = p.player_id
            JOIN player_advanced_stats a ON s.player_id = a.player_id AND s.season = a.season
            WHERE s.season = '{season}' AND s.season_type = 'Regular Season'
              AND s.gp >= 30
              {pos_filter}
            ORDER BY s.{primary_metric} DESC
            LIMIT {limit};
        """.strip()

        chart_spec = {
            "chartType": "horizontalBar",
            "title": f"Top {limit} {pos_title}: {primary_label} ({season})",
            "subtitle": f"Rankings sorted by {primary_label}" + (" with True Shooting %" if has_secondary else ""),
            "sqlQuery": sql,
            "dimensions": { "labelKey": "full_name", "teamKey": "team_abbreviation" },
            "metrics": metrics,
            "benchmarks": benchmarks,
            "narrative": f"Top {limit} {pos_title.lower()} ranked by {primary_label.lower()} in {season} with minimum 30 games played."
        }
        return chart_spec

    def process_query(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        api_key: Optional[str] = None,
        model: str = "gemini-flash-latest"
    ) -> Dict[str, Any]:
        """
        Processes a natural language query:
        1. If no API key provided, uses the intelligent semantic query builder (or presets).
        2. If API key provided, calls Gemini to generate SQL + Chart DSL + Narrative.
        3. Executes SQL query against SQLite with self-healing auto-repair.
        4. If Gemini fails, falls back gracefully to semantic query builder.
        """
        active_key = self.get_api_key(api_key)

        # If no API key is set, use our semantic query builder to dynamically construct the chart!
        if not active_key:
            chart_spec = self.build_semantic_query(prompt)
            if not chart_spec:
                # Fallback to matched or default preset
                prompt_lower = prompt.lower().strip()
                demo = PRESET_QUERIES[0]
                for preset in PRESET_QUERIES:
                    if preset["prompt"].lower() in prompt_lower or preset["id"] in prompt_lower:
                        demo = preset
                        break
                chart_spec = dict(demo["chartSpec"])

            data_rows, sql_err = self.execute_query(chart_spec["sqlQuery"])

            # Generate dynamic narrative from real rows
            narrative = chart_spec.get("narrative", "")
            if data_rows and len(data_rows) > 0:
                first_row = data_rows[0]
                name = first_row.get("full_name") or first_row.get("abbreviation") or "The leader"
                if chart_spec.get("metrics") and len(chart_spec["metrics"]) > 0:
                    m_key = chart_spec["metrics"][0]["key"]
                    m_label = chart_spec["metrics"][0].get("label", m_key)
                    val = first_row.get(m_key, "")
                    narrative += f" {name} leads this group with {val} {m_label}."
                elif chart_spec.get("scatterConfig"):
                    sc = chart_spec["scatterConfig"]
                    x_lbl = sc.get("xMetric", {}).get("label", "X")
                    y_lbl = sc.get("yMetric", {}).get("label", "Y")
                    x_val = first_row.get(sc.get("xMetric", {}).get("key", ""), "")
                    y_val = first_row.get(sc.get("yMetric", {}).get("key", ""), "")
                    narrative += f" {name} posts {x_val} ({x_lbl}) and {y_val} ({y_lbl})."

            return {
                "success": sql_err is None,
                "isDemo": True,
                "demoNotice": "Running in Smart Dynamic Mode. Configure your Gemini API Key in Settings for unlimited open-ended queries.",
                "chartSpec": chart_spec,
                "data": data_rows or [],
                "narrative": narrative,
                "sql": chart_spec["sqlQuery"],
                "error": sql_err
            }

        # Step 1: Call Gemini
        try:
            dsl_resp = self.call_gemini_api(
                prompt=prompt,
                api_key=active_key,
                model=model,
                history=history,
                system_instruction=SYSTEM_PROMPT
            )
        except Exception as e:
            logger.error(f"Failed to generate chart DSL with Gemini: {e}")
            # Fallback gracefully to semantic query builder
            semantic_spec = self.build_semantic_query(prompt)
            if semantic_spec:
                data_rows, _ = self.execute_query(semantic_spec["sqlQuery"])
                return {
                    "success": True,
                    "isDemo": True,
                    "demoNotice": f"Gemini API error ({str(e)}). Displaying semantic chart instead.",
                    "chartSpec": semantic_spec,
                    "data": data_rows or [],
                    "narrative": semantic_spec.get("narrative", ""),
                    "sql": semantic_spec["sqlQuery"],
                    "error": None
                }
            return {
                "success": False,
                "error": f"AI model error: {str(e)}"
            }

        sql_query = dsl_resp.get("sqlQuery", "")
        if not sql_query:
            return {
                "success": False,
                "error": "The AI model did not generate an SQL query."
            }

        # Step 2: Execute SQL Query
        data_rows, sql_err = self.execute_query(sql_query)

        # Step 3: Self-Healing Auto-Repair Loop (1 retry)
        if sql_err and active_key:
            logger.info(f"Triggering self-healing repair for SQL error: {sql_err}")
            repair_prompt = f"""
The previous SQL query failed with the following SQLite error:
{sql_err}

Original user request: "{prompt}"
Failed SQL query:
{sql_query}

Please fix the SQL query using the correct table schema and column names. Return the corrected complete JSON object according to the Chart DSL specification.
            """.strip()

            try:
                repaired_resp = self.call_gemini_api(
                    prompt=repair_prompt,
                    api_key=active_key,
                    model=model,
                    system_instruction=SYSTEM_PROMPT
                )
                repaired_sql = repaired_resp.get("sqlQuery", "")
                repaired_rows, repaired_err = self.execute_query(repaired_sql)
                if not repaired_err:
                    dsl_resp = repaired_resp
                    sql_query = repaired_sql
                    data_rows = repaired_rows
                    sql_err = None
                    logger.info("Self-healing repair succeeded!")
                else:
                    sql_err = f"Auto-repair failed: {repaired_err}"
            except Exception as repair_exc:
                logger.warning(f"Self-repair attempt threw exception: {repair_exc}")

        return {
            "success": sql_err is None,
            "chartSpec": dsl_resp,
            "data": data_rows or [],
            "narrative": dsl_resp.get("narrative", ""),
            "sql": sql_query,
            "error": sql_err
        }

    def validate_api_key(self, api_key: str, model: str = "gemini-flash-latest") -> Tuple[bool, str]:
        """Tests if a Gemini API key is functional."""
        if not api_key:
            return False, "API key is required."
        try:
            self.call_gemini_api(
                prompt="Respond with valid JSON: {\"status\": \"ok\"}",
                api_key=api_key,
                model=model,
                system_instruction="You are a key validation helper. Return JSON: {\"status\": \"ok\"}."
            )
            return True, "API key is valid."
        except Exception as e:
            return False, str(e)

    def get_presets(self) -> List[Dict[str, Any]]:
        """Returns list of curated demo presets."""
        return PRESET_QUERIES
