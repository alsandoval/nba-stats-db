"""
generate_contracts_seed.py - Populates comprehensive data/contracts_seed.json
with all 30 NBA teams, player contracts, options, trade kickers, and CBA cap settings.
"""

import os
import json
import sqlite3
import unicodedata

def norm(text):
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower().strip()

def clean_suffix(text):
    for suf in [" iii", " ii", " iv", " jr.", " jr", " sr.", " sr"]:
        if text.endswith(suf):
            return text[:-len(suf)].strip()
    return text

def run():
    db_path = os.path.abspath("nba_stats.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Load all players
    players_data = c.execute("SELECT player_id, full_name, is_active FROM players").fetchall()
    player_by_name = {}
    for pid, name, active in players_data:
        n = norm(name)
        if n not in player_by_name or active:
            player_by_name[n] = (pid, name)

    team_map = {
        "ATL": 1610612737, "BOS": 1610612738, "CLE": 1610612739, "NOP": 1610612740,
        "CHI": 1610612741, "DAL": 1610612742, "DEN": 1610612743, "GSW": 1610612744,
        "HOU": 1610612745, "LAC": 1610612746, "LAL": 1610612747, "MIA": 1610612748,
        "MIL": 1610612749, "MIN": 1610612750, "BKN": 1610612751, "NYK": 1610612752,
        "ORL": 1610612753, "IND": 1610612754, "PHI": 1610612755, "PHX": 1610612756,
        "POR": 1610612757, "SAC": 1610612758, "SAS": 1610612759, "OKC": 1610612760,
        "TOR": 1610612761, "UTA": 1610612762, "MEM": 1610612763, "WAS": 1610612764,
        "DET": 1610612765, "CHA": 1610612766
    }

    # CBA settings
    cba_settings = [
        {
            "season": "2023-24",
            "salary_cap": 136021000.0,
            "tax_level": 165294000.0,
            "first_apron": 172346000.0,
            "second_apron": 182794000.0,
            "min_team_salary": 122419000.0,
            "tax_bracket_size": 5000000.0,
            "nontaxpayer_mle": 12405000.0,
            "taxpayer_mle": 5000000.0,
            "room_mle": 7723000.0,
            "biannual_exception": 4516000.0,
            "cost_per_win": 3400000.0
        },
        {
            "season": "2024-25",
            "salary_cap": 140588000.0,
            "tax_level": 170814000.0,
            "first_apron": 178132000.0,
            "second_apron": 188931000.0,
            "min_team_salary": 126529000.0,
            "tax_bracket_size": 5000000.0,
            "nontaxpayer_mle": 12822000.0,
            "taxpayer_mle": 5168000.0,
            "room_mle": 7983000.0,
            "biannual_exception": 4668000.0,
            "cost_per_win": 3550000.0
        },
        {
            "season": "2025-26",
            "salary_cap": 154646000.0,
            "tax_level": 187895000.0,
            "first_apron": 195945000.0,
            "second_apron": 207824000.0,
            "min_team_salary": 139181000.0,
            "tax_bracket_size": 5000000.0,
            "nontaxpayer_mle": 14104000.0,
            "taxpayer_mle": 5685000.0,
            "room_mle": 8781000.0,
            "biannual_exception": 5135000.0,
            "cost_per_win": 3750000.0
        }
    ]

    # Specific real contract details for notable players across all 30 teams
    # Format: name: (contract_type, kicker_pct, ntc, poison_pill, [(season, salary, option, guaranteed)])
    REAL_CONTRACTS = {
        # BOS
        "Jayson Tatum": ("Designated Veteran", 0.0, 0, 0, [("2023-24", 32600060, None, 1), ("2024-25", 34848340, None, 1), ("2025-26", 54126450, None, 1), ("2026-27", 58456566, None, 1), ("2027-28", 62786682, None, 1)]),
        "Jaylen Brown": ("Designated Veteran", 0.0, 0, 1, [("2023-24", 31830357, None, 1), ("2024-25", 49700000, None, 1), ("2025-26", 53676000, None, 1), ("2026-27", 57652000, None, 1), ("2027-28", 61628000, None, 1)]),
        "Jrue Holiday": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 36861707, None, 1), ("2024-25", 30000000, None, 1), ("2025-26", 32400000, None, 1), ("2026-27", 34800000, None, 1), ("2027-28", 37200000, "Player Option", 1)]),
        "Kristaps Porzingis": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 36016200, None, 1), ("2024-25", 29268293, None, 1), ("2025-26", 30731707, None, 1)]),
        "Derrick White": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 18357143, None, 1), ("2024-25", 19571429, None, 1), ("2025-26", 28100000, None, 1), ("2026-27", 30348000, None, 1)]),
        "Al Horford": ("Veteran", 0.0, 0, 0, [("2023-24", 10000000, None, 1), ("2024-25", 9500000, None, 1)]),
        "Payton Pritchard": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 4037278, None, 1), ("2024-25", 6696429, None, 1), ("2025-26", 7232143, None, 1), ("2026-27", 7767857, None, 1)]),
        "Sam Hauser": ("Standard", 0.0, 0, 0, [("2023-24", 1927896, "Team Option", 1), ("2024-25", 2092344, "Team Option", 1), ("2025-26", 10000000, None, 1)]),
        "Luke Kornet": ("Minimum", 0.0, 0, 0, [("2023-24", 2413304, None, 1), ("2024-25", 2800000, None, 1)]),
        "Xavier Tillman": ("Minimum", 0.0, 0, 0, [("2023-24", 1930681, None, 1), ("2024-25", 2237691, None, 1)]),
        "Neemias Queta": ("Standard", 0.0, 0, 0, [("2023-24", 2019706, None, 1), ("2024-25", 2164993, None, 1)]),
        "Jaden Springer": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 2226240, None, 1), ("2024-25", 4018363, "Team Option", 1)]),

        # LAL
        "LeBron James": ("Maximum", 0.15, 1, 0, [("2023-24", 47607350, None, 1), ("2024-25", 48728845, "Player Option", 1), ("2025-26", 52627153, "Player Option", 1)]),
        "Anthony Davis": ("Designated Veteran", 0.0, 0, 0, [("2023-24", 40600080, None, 1), ("2024-25", 43219440, None, 1), ("2025-26", 54126450, None, 1), ("2026-27", 58456566, None, 1), ("2027-28", 62786682, "Player Option", 1)]),
        "D'Angelo Russell": ("Standard", 0.0, 0, 0, [("2023-24", 17307693, None, 1), ("2024-25", 18692307, "Player Option", 1)]),
        "Austin Reaves": ("Early Bird", 0.15, 0, 0, [("2023-24", 12015150, None, 1), ("2024-25", 12976362, None, 1), ("2025-26", 13937574, None, 1), ("2026-27", 14898786, "Player Option", 1)]),
        "Rui Hachimura": ("Standard", 0.0, 0, 0, [("2023-24", 15740741, None, 1), ("2024-25", 17000000, None, 1), ("2025-26", 18259259, None, 1)]),
        "Gabe Vincent": ("Non-Taxpayer MLE", 0.0, 0, 0, [("2023-24", 10500000, None, 1), ("2024-25", 11000000, None, 1), ("2025-26", 11500000, None, 1)]),
        "Jarred Vanderbilt": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 4640000, None, 1), ("2024-25", 10714286, None, 1), ("2025-26", 11571429, None, 1), ("2026-27", 12428571, None, 1), ("2027-28", 13285714, "Player Option", 1)]),
        "Christian Wood": ("Bi-Annual", 0.0, 0, 0, [("2023-24", 2709849, None, 1), ("2024-25", 3036040, "Player Option", 1)]),
        "Jaxson Hayes": ("Minimum", 0.0, 0, 0, [("2023-24", 2165000, None, 1), ("2024-25", 2463946, "Player Option", 1)]),
        "Cam Reddish": ("Minimum", 0.0, 0, 0, [("2023-24", 2165000, None, 1), ("2024-25", 2463946, "Player Option", 1)]),
        "Max Christie": ("Standard", 0.0, 0, 0, [("2023-24", 1719864, None, 1), ("2024-25", 7142857, None, 1), ("2025-26", 7714286, None, 1)]),
        "Jalen Hood-Schifino": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 3695040, None, 1), ("2024-25", 3879840, "Team Option", 1), ("2025-26", 4064640, "Team Option", 1)]),
        "Taurean Prince": ("Bi-Annual", 0.0, 0, 0, [("2023-24", 4516000, None, 1)]),

        # GSW
        "Stephen Curry": ("Designated Veteran", 0.0, 0, 0, [("2023-24", 51915615, None, 1), ("2024-25", 55761216, None, 1), ("2025-26", 59606817, None, 1), ("2026-27", 62587158, None, 1)]),
        "Klay Thompson": ("Maximum", 0.0, 0, 0, [("2023-24", 43219440, None, 1)]),
        "Chris Paul": ("Veteran", 0.0, 0, 0, [("2023-24", 30800000, None, 1)]),
        "Draymond Green": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 22321429, None, 1), ("2024-25", 24107143, None, 1), ("2025-26", 25892857, None, 1), ("2026-27", 27678571, "Player Option", 1)]),
        "Andrew Wiggins": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 24330357, None, 1), ("2024-25", 26276786, None, 1), ("2025-26", 28223214, None, 1), ("2026-27", 30169643, "Player Option", 1)]),
        "Gary Payton II": ("Standard", 0.0, 0, 0, [("2023-24", 8715000, None, 1), ("2024-25", 9130000, "Player Option", 1)]),
        "Kevon Looney": ("Standard", 0.0, 0, 0, [("2023-24", 7500000, None, 1), ("2024-25", 8000000, None, 1)]),
        "Jonathan Kuminga": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 6012840, None, 1), ("2024-25", 7636307, "Team Option", 1)]),
        "Moses Moody": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 3918480, None, 1), ("2024-25", 5803269, "Team Option", 1)]),
        "Brandin Podziemski": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 3352440, None, 1), ("2024-25", 3519960, "Team Option", 1), ("2025-26", 3687960, "Team Option", 1)]),
        "Trayce Jackson-Davis": ("Standard", 0.0, 0, 0, [("2023-24", 1119563, None, 1), ("2024-25", 1891857, "Team Option", 1), ("2025-26", 2221677, "Team Option", 1)]),
        "Dario Saric": ("Minimum", 0.0, 0, 0, [("2023-24", 2709849, None, 1)]),

        # DEN
        "Nikola Jokic": ("Designated Veteran", 0.0, 0, 0, [("2023-24", 47607350, None, 1), ("2024-25", 51415938, None, 1), ("2025-26", 55224526, None, 1), ("2026-27", 59033114, None, 1), ("2027-28", 62841702, "Player Option", 1)]),
        "Jamal Murray": ("Maximum", 0.0, 0, 0, [("2023-24", 33833400, None, 1), ("2024-25", 36016200, None, 1), ("2025-26", 46394100, None, 1), ("2026-27", 50105628, None, 1)]),
        "Michael Porter Jr.": ("Maximum Extension", 0.0, 0, 0, [("2023-24", 33386850, None, 1), ("2024-25", 35859950, None, 1), ("2025-26", 38333050, None, 1), ("2026-27", 40806150, None, 1)]),
        "Aaron Gordon": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 22266182, None, 1), ("2024-25", 23841000, None, 1), ("2025-26", 22841000, "Player Option", 1)]),
        "Kentavious Caldwell-Pope": ("Veteran", 0.0, 0, 0, [("2023-24", 14704938, None, 1), ("2024-25", 15440185, "Player Option", 1)]),
        "Christian Braun": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 2949120, None, 1), ("2024-25", 3089640, "Team Option", 1), ("2025-26", 4921796, "Team Option", 1)]),
        "Peyton Watson": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 2413560, None, 1), ("2024-25", 2533920, "Team Option", 1), ("2025-26", 4358342, "Team Option", 1)]),
        "Zeke Nnaji": ("Standard", 0.0, 0, 0, [("2023-24", 4306281, None, 1), ("2024-25", 8888889, None, 1), ("2025-26", 8177778, None, 1), ("2026-27", 7466667, "Player Option", 1)]),
        "Reggie Jackson": ("Room MLE", 0.0, 0, 0, [("2023-24", 5000000, None, 1), ("2024-25", 5250000, "Player Option", 1)]),
        "DeAndre Jordan": ("Minimum", 0.0, 0, 0, [("2023-24", 3196448, None, 1), ("2024-25", 3303771, None, 1)]),

        # PHX
        "Kevin Durant": ("Maximum", 0.0, 0, 0, [("2023-24", 47649433, None, 1), ("2024-25", 51179021, None, 1), ("2025-26", 54708609, None, 1)]),
        "Bradley Beal": ("Designated Veteran", 0.15, 1, 0, [("2023-24", 46741590, None, 1), ("2024-25", 50203930, None, 1), ("2025-26", 53666270, None, 1), ("2026-27", 57128610, "Player Option", 1)]),
        "Devin Booker": ("Designated Veteran", 0.0, 0, 0, [("2023-24", 36016200, None, 1), ("2024-25", 49350000, None, 1), ("2025-26", 53298000, None, 1), ("2026-27", 57246000, None, 1), ("2027-28", 61194000, None, 1)]),
        "Jusuf Nurkic": ("Standard", 0.0, 0, 0, [("2023-24", 16875000, None, 1), ("2024-25", 18125000, None, 1), ("2025-26", 19375000, None, 1)]),
        "Grayson Allen": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 8500000, None, 1), ("2024-25", 15625000, None, 1), ("2025-26", 16875000, None, 1), ("2026-27", 18125000, None, 1)]),
        "Royce O'Neale": ("Standard", 0.0, 0, 0, [("2023-24", 9500000, None, 1), ("2024-25", 9875000, None, 1), ("2025-26", 10665000, None, 1)]),
        "Josh Okogie": ("Standard", 0.0, 0, 0, [("2023-24", 2815937, None, 1), ("2024-25", 8250000, None, 1)]),
        "Nassir Little": ("Standard", 0.0, 0, 0, [("2023-24", 6250000, None, 1), ("2024-25", 6750000, None, 1), ("2025-26", 7250000, None, 1)]),
        "Bol Bol": ("Minimum", 0.0, 0, 0, [("2023-24", 2165000, None, 1), ("2024-25", 2165000, None, 1)]),
        "Eric Gordon": ("Minimum", 0.0, 0, 0, [("2023-24", 3196448, None, 1)]),

        # MIL
        "Giannis Antetokounmpo": ("Designated Veteran", 0.0, 0, 0, [("2023-24", 45640084, None, 1), ("2024-25", 48787676, None, 1), ("2025-26", 58458000, None, 1), ("2026-27", 63134640, None, 1), ("2027-28", 67811280, "Player Option", 1)]),
        "Damian Lillard": ("Designated Veteran", 0.0, 0, 0, [("2023-24", 45640084, None, 1), ("2024-25", 48787676, None, 1), ("2025-26", 58545211, None, 1), ("2026-27", 63228828, "Player Option", 1)]),
        "Khris Middleton": ("Veteran", 0.0, 0, 0, [("2023-24", 29320988, None, 1), ("2024-25", 31666667, None, 1), ("2025-26", 34012345, "Player Option", 1)]),
        "Brook Lopez": ("Veteran", 0.0, 0, 0, [("2023-24", 25000000, None, 1), ("2024-25", 23000000, None, 1)]),
        "Bobby Portis": ("Standard", 0.0, 0, 0, [("2023-24", 11710818, None, 1), ("2024-25", 12578286, None, 1), ("2025-26", 13445754, "Player Option", 1)]),
        "Pat Connaughton": ("Standard", 0.0, 0, 0, [("2023-24", 9423869, None, 1), ("2024-25", 9423869, None, 1), ("2025-26", 9423869, "Player Option", 1)]),
        "Malik Beasley": ("Minimum", 0.0, 0, 0, [("2023-24", 2709849, None, 1)]),
        "Jae Crowder": ("Minimum", 0.0, 0, 0, [("2023-24", 3196448, None, 1)]),
        "Patrick Beverley": ("Minimum", 0.0, 0, 0, [("2023-24", 3196448, None, 1)]),

        # DAL
        "Luka Doncic": ("Designated Rookie", 0.15, 0, 0, [("2023-24", 40064220, None, 1), ("2024-25", 43031940, None, 1), ("2025-26", 45999660, None, 1), ("2026-27", 48967380, "Player Option", 1)]),
        "Kyrie Irving": ("Standard", 0.15, 0, 0, [("2023-24", 37037037, None, 1), ("2024-25", 40000000, None, 1), ("2025-26", 42962963, "Player Option", 1)]),
        "Daniel Gafford": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 12402000, None, 1), ("2024-25", 13394160, None, 1), ("2025-26", 14386320, None, 1)]),
        "PJ Washington": ("Standard", 0.0, 0, 0, [("2023-24", 16847826, None, 1), ("2024-25", 15500000, None, 1), ("2025-26", 14152174, None, 1)]),
        "Tim Hardaway Jr.": ("Standard", 0.0, 0, 0, [("2023-24", 17897728, None, 1), ("2024-25", 16193183, None, 1)]),
        "Dereck Lively II": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 4775640, None, 1), ("2024-25", 5014560, "Team Option", 1), ("2025-26", 5253360, "Team Option", 1)]),
        "Josh Green": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 4765339, None, 1), ("2024-25", 12654321, None, 1), ("2025-26", 13666667, None, 1), ("2026-27", 14679012, None, 1)]),
        "Maxi Kleber": ("Standard", 0.0, 0, 0, [("2023-24", 11000000, None, 1), ("2024-25", 11000000, None, 1), ("2025-26", 11000000, None, 1)]),
        "Dwight Powell": ("Standard", 0.0, 0, 0, [("2023-24", 4000000, None, 1), ("2024-25", 4000000, "Player Option", 1), ("2025-26", 4000000, "Player Option", 1)]),
        "Derrick Jones Jr.": ("Minimum", 0.0, 0, 0, [("2023-24", 2709849, None, 1)]),
        "Dante Exum": ("Bi-Annual", 0.0, 0, 0, [("2023-24", 3000000, None, 1), ("2024-25", 3150000, None, 1)]),

        # MIN
        "Anthony Edwards": ("Designated Rookie", 0.0, 0, 1, [("2023-24", 13534817, None, 1), ("2024-25", 42176400, None, 1), ("2025-26", 45550512, None, 1), ("2026-27", 48924624, None, 1), ("2027-28", 52298736, None, 1), ("2028-29", 55672848, None, 1)]),
        "Karl-Anthony Towns": ("Designated Veteran", 0.0, 0, 0, [("2023-24", 36016200, None, 1), ("2024-25", 49350000, None, 1), ("2025-26", 53298000, None, 1), ("2026-27", 57246000, None, 1), ("2027-28", 61194000, "Player Option", 1)]),
        "Rudy Gobert": ("Designated Veteran", 0.0, 0, 0, [("2023-24", 41000000, None, 1), ("2024-25", 43827587, None, 1), ("2025-26", 46655173, "Player Option", 1)]),
        "Jaden McDaniels": ("Rookie Extension", 0.0, 0, 1, [("2023-24", 3901399, None, 1), ("2024-25", 22586207, None, 1), ("2025-26", 24393103, None, 1), ("2026-27", 26200000, None, 1), ("2027-28", 28006897, None, 1), ("2028-29", 29813793, None, 1)]),
        "Mike Conley": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 24970000, None, 1), ("2024-25", 9975962, None, 1), ("2025-26", 10774038, None, 1)]),
        "Naz Reid": ("Standard", 0.0, 0, 0, [("2023-24", 12950000, None, 1), ("2024-25", 13986000, None, 1), ("2025-26", 15022000, "Player Option", 1)]),
        "Kyle Anderson": ("Standard", 0.0, 0, 0, [("2023-24", 9245121, None, 1)]),
        "Nickeil Alexander-Walker": ("Standard", 0.0, 0, 0, [("2023-24", 4687500, None, 1), ("2024-25", 4312500, None, 1)]),
        "Monte Morris": ("Standard", 0.0, 0, 0, [("2023-24", 9800926, None, 1)]),

        # NYK
        "Jalen Brunson": ("Standard", 0.0, 0, 0, [("2023-24", 26346666, None, 1), ("2024-25", 24960001, "Player Option", 1), ("2025-26", 34944000, None, 1), ("2026-27", 37739520, None, 1), ("2027-28", 40535040, None, 1)]),
        "Julius Randle": ("Veteran Extension", 0.15, 0, 0, [("2023-24", 28226880, None, 1), ("2024-25", 30317760, None, 1), ("2025-26", 32408640, "Player Option", 1)]),
        "OG Anunoby": ("Maximum", 0.0, 0, 0, [("2023-24", 18642857, None, 1), ("2024-25", 36637931, None, 1), ("2025-26", 39568966, None, 1), ("2026-27", 42500000, None, 1), ("2027-28", 45431034, "Player Option", 1)]),
        "Mitchell Robinson": ("Standard", 0.0, 0, 0, [("2023-24", 15681818, None, 1), ("2024-25", 14318182, None, 1), ("2025-26", 12954545, None, 1)]),
        "Josh Hart": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 12960000, None, 1), ("2024-25", 18144000, None, 1), ("2025-26", 19460000, None, 1), ("2026-27", 20776000, None, 1), ("2027-28", 22092000, "Team Option", 1)]),
        "Donte DiVincenzo": ("Non-Taxpayer MLE", 0.0, 0, 0, [("2023-24", 10900000, None, 1), ("2024-25", 11445000, None, 1), ("2025-26", 11990000, None, 1), ("2026-27", 12535000, None, 1)]),
        "Isaiah Hartenstein": ("Standard", 0.0, 0, 0, [("2023-24", 9245121, None, 1)]),
        "Miles McBride": ("Standard", 0.0, 0, 0, [("2023-24", 1836096, None, 1), ("2024-25", 4710145, None, 1), ("2025-26", 4333333, None, 1), ("2026-27", 3956522, None, 1)]),

        # PHI
        "Joel Embiid": ("Designated Veteran", 0.0, 0, 0, [("2023-24", 47607350, None, 1), ("2024-25", 51415938, None, 1), ("2025-26", 55224526, None, 1), ("2026-27", 59535000, None, 1), ("2027-28", 64297800, None, 1), ("2028-29", 69060600, "Player Option", 1)]),
        "Tobias Harris": ("Maximum", 0.0, 0, 0, [("2023-24", 39270150, None, 1)]),
        "Tyrese Maxey": ("Designated Rookie", 0.0, 0, 0, [("2023-24", 4343920, None, 1), ("2024-25", 35147000, None, 1), ("2025-26", 37958760, None, 1), ("2026-27", 40770520, None, 1), ("2027-28", 43582280, None, 1), ("2028-29", 46394040, None, 1)]),
        "De'Anthony Melton": ("Standard", 0.0, 0, 0, [("2023-24", 8000000, None, 1)]),
        "Kelly Oubre Jr.": ("Room MLE", 0.0, 0, 0, [("2023-24", 2891467, None, 1), ("2024-25", 7983000, None, 1), ("2025-26", 8382150, "Player Option", 1)]),
        "Paul Reed": ("Standard", 0.0, 0, 0, [("2023-24", 7723000, None, 1), ("2024-25", 7723000, None, 1), ("2025-26", 8109150, "Team Option", 1)]),
        "Buddy Hield": ("Standard", 0.0, 0, 0, [("2023-24", 19279841, None, 1)]),

        # MIA
        "Jimmy Butler": ("Maximum Extension", 0.15, 0, 0, [("2023-24", 45183960, None, 1), ("2024-25", 48798677, None, 1), ("2025-26", 52413394, "Player Option", 1)]),
        "Bam Adebayo": ("Maximum Extension", 0.0, 0, 0, [("2023-24", 32600060, None, 1), ("2024-25", 34848340, None, 1), ("2025-26", 54126450, None, 1), ("2026-27", 58456566, None, 1), ("2027-28", 62786682, None, 1)]),
        "Tyler Herro": ("Rookie Extension", 0.0, 0, 0, [("2023-24", 27000000, None, 1), ("2024-25", 29000000, None, 1), ("2025-26", 31000000, None, 1), ("2026-27", 33000000, None, 1)]),
        "Terry Rozier": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 23205357, None, 1), ("2024-25", 24924126, None, 1), ("2025-26", 26642895, None, 1)]),
        "Duncan Robinson": ("Early Bird", 0.0, 0, 0, [("2023-24", 18154000, None, 1), ("2024-25", 19406000, None, 1), ("2025-26", 19888000, "Early Termination Option", 1)]),
        "Caleb Martin": ("Standard", 0.0, 0, 0, [("2023-24", 6802950, None, 1), ("2024-25", 7126900, "Player Option", 1)]),
        "Jaime Jaquez Jr.": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 3510600, None, 1), ("2024-25", 3685800, "Team Option", 1), ("2025-26", 3861600, "Team Option", 1)]),
        "Nikola Jovic": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 2352000, None, 1), ("2024-25", 2464200, "Team Option", 1), ("2025-26", 4445417, "Team Option", 1)]),

        # LAC
        "Kawhi Leonard": ("Designated Veteran", 0.15, 0, 0, [("2023-24", 45640084, None, 1), ("2024-25", 49205800, None, 1), ("2025-26", 50000000, None, 1), ("2026-27", 50000000, None, 1)]),
        "Paul George": ("Maximum", 0.0, 0, 0, [("2023-24", 45640084, None, 1), ("2024-25", 49205800, None, 1), ("2025-26", 51666110, None, 1), ("2026-27", 54126420, None, 1), ("2027-28", 56586730, "Player Option", 1)]),
        "James Harden": ("Standard", 0.0, 0, 0, [("2023-24", 35640000, None, 1), ("2024-25", 33653846, None, 1), ("2025-26", 36346154, "Player Option", 1)]),
        "Norman Powell": ("Standard", 0.0, 0, 0, [("2023-24", 18000000, None, 1), ("2024-25", 19241379, None, 1), ("2025-26", 20482758, None, 1)]),
        "Ivica Zubac": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 10850000, None, 1), ("2024-25", 11741071, None, 1), ("2025-26", 18144000, None, 1), ("2026-27", 19595520, None, 1), ("2027-28", 21047040, None, 1)]),
        "Terance Mann": ("Standard", 0.0, 0, 0, [("2023-24", 10576923, None, 1), ("2024-25", 11423077, None, 1), ("2025-26", 15500000, None, 1), ("2026-27", 15500000, None, 1), ("2027-28", 16000000, None, 1)]),
        "Russell Westbrook": ("Bi-Annual", 0.0, 0, 0, [("2023-24", 3835738, None, 1), ("2024-25", 4027525, "Player Option", 1)]),
        "PJ Tucker": ("Full MLE", 0.0, 0, 0, [("2023-24", 11014500, None, 1), ("2024-25", 11539000, "Player Option", 1)]),

        # OKC
        "Shai Gilgeous-Alexander": ("Designated Rookie", 0.0, 0, 0, [("2023-24", 33386850, None, 1), ("2024-25", 35859950, None, 1), ("2025-26", 38333050, None, 1), ("2026-27", 40806150, None, 1)]),
        "Chet Holmgren": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 10386000, None, 1), ("2024-25", 10880640, "Team Option", 1), ("2025-26", 13731368, "Team Option", 1)]),
        "Jalen Williams": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 4558680, None, 1), ("2024-25", 4775760, "Team Option", 1), ("2025-26", 6580997, "Team Option", 1)]),
        "Luguentz Dort": ("Early Bird", 0.0, 0, 0, [("2023-24", 15277778, None, 1), ("2024-25", 16500000, None, 1), ("2025-26", 17722222, None, 1), ("2026-27", 17722222, "Team Option", 1)]),
        "Josh Giddey": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 6587040, None, 1), ("2024-25", 8352367, "Team Option", 1)]),
        "Isaiah Joe": ("Standard", 0.0, 0, 0, [("2023-24", 1997238, "Team Option", 1), ("2024-25", 12000000, None, 1), ("2025-26", 12000000, None, 1), ("2026-27", 12000000, None, 1), ("2027-28", 12000000, "Team Option", 1)]),
        "Cason Wallace": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 5291400, None, 1), ("2024-25", 5555880, "Team Option", 1), ("2025-26", 5820240, "Team Option", 1)]),
        "Kenrich Williams": ("Standard", 0.0, 0, 0, [("2023-24", 6175000, None, 1), ("2024-25", 6669000, None, 1), ("2025-26", 7163000, None, 1), ("2026-27", 7163000, "Team Option", 1)]),
        "Gordon Hayward": ("Maximum", 0.0, 0, 0, [("2023-24", 31500000, None, 1)]),

        # CLE
        "Donovan Mitchell": ("Designated Rookie", 0.0, 0, 0, [("2023-24", 33162030, None, 1), ("2024-25", 35410310, None, 1), ("2025-26", 46394100, None, 1), ("2026-27", 50105628, None, 1), ("2027-28", 53817156, "Player Option", 1)]),
        "Darius Garland": ("Designated Rookie", 0.0, 0, 0, [("2023-24", 34005250, None, 1), ("2024-25", 36725670, None, 1), ("2025-26", 39446090, None, 1), ("2026-27", 42166510, None, 1), ("2027-28", 44886930, None, 1)]),
        "Evan Mobley": ("Rookie Scale", 0.0, 0, 1, [("2023-24", 8882640, None, 1), ("2024-25", 11227657, "Team Option", 1), ("2025-26", 42176400, None, 1), ("2026-27", 45550512, None, 1), ("2027-28", 48924624, None, 1)]),
        "Jarrett Allen": ("Veteran", 0.0, 0, 0, [("2023-24", 20000000, None, 1), ("2024-25", 20000000, None, 1), ("2025-26", 20000000, None, 1), ("2026-27", 30000000, None, 1), ("2027-28", 30000000, None, 1), ("2028-29", 30000000, None, 1)]),
        "Caris LeVert": ("Standard", 0.0, 0, 0, [("2023-24", 15384615, None, 1), ("2024-25", 16615385, None, 1)]),
        "Max Strus": ("Non-Taxpayer MLE", 0.0, 0, 0, [("2023-24", 14489655, None, 1), ("2024-25", 15213793, None, 1), ("2025-26", 15937931, None, 1), ("2026-27", 16662069, None, 1)]),
        "Isaac Okoro": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 8920795, None, 1), ("2024-25", 11800000, None, 1), ("2025-26", 11800000, None, 1), ("2026-27", 11800000, None, 1)]),
        "Georges Niang": ("Non-Taxpayer MLE", 0.0, 0, 0, [("2023-24", 8800000, None, 1), ("2024-25", 8500000, None, 1), ("2025-26", 8200000, None, 1)]),

        # IND
        "Tyrese Haliburton": ("Designated Rookie", 0.0, 0, 1, [("2023-24", 5808435, None, 1), ("2024-25", 42176400, None, 1), ("2025-26", 45550512, None, 1), ("2026-27", 48924624, None, 1), ("2027-28", 52298736, None, 1), ("2028-29", 55672848, None, 1)]),
        "Pascal Siakam": ("Maximum", 0.0, 0, 0, [("2023-24", 37893408, None, 1), ("2024-25", 42176400, None, 1), ("2025-26", 45550512, None, 1), ("2026-27", 48924624, None, 1), ("2027-28", 52298736, None, 1)]),
        "Myles Turner": ("Standard", 0.0, 0, 0, [("2023-24", 20975000, None, 1), ("2024-25", 19928500, None, 1)]),
        "Bennedict Mathurin": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 6916080, None, 1), ("2024-25", 7245720, "Team Option", 1), ("2025-26", 9187573, "Team Option", 1)]),
        "Aaron Nesmith": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 5634257, None, 1), ("2024-25", 11000000, None, 1), ("2025-26", 11000000, None, 1), ("2026-27", 11000000, None, 1)]),
        "TJ McConnell": ("Standard", 0.0, 0, 0, [("2023-24", 8700000, None, 1), ("2024-25", 9300000, None, 1), ("2025-26", 10200000, None, 1), ("2026-27", 10200000, None, 1)]),
        "Obi Toppin": ("Standard", 0.0, 0, 0, [("2023-24", 6803012, None, 1), ("2024-25", 14000000, None, 1), ("2025-26", 14000000, None, 1), ("2026-27", 14000000, None, 1), ("2027-28", 14000000, "Team Option", 1)]),
        "Andrew Nembhard": ("Standard", 0.0, 0, 0, [("2023-24", 2131905, None, 1), ("2024-25", 2244140, "Team Option", 1), ("2025-26", 18000000, None, 1), ("2026-27", 19440000, None, 1), ("2027-28", 20880000, None, 1)]),

        # SAC
        "De'Aaron Fox": ("Designated Rookie", 0.0, 0, 0, [("2023-24", 32600060, None, 1), ("2024-25", 34848340, None, 1), ("2025-26", 37096620, None, 1)]),
        "Domantas Sabonis": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 30600000, None, 1), ("2024-25", 41800000, None, 1), ("2025-26", 44800000, None, 1), ("2026-27", 47800000, None, 1), ("2027-28", 50800000, None, 1)]),
        "Keegan Murray": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 8409000, None, 1), ("2024-25", 8809560, "Team Option", 1), ("2025-26", 11144103, "Team Option", 1)]),
        "Harrison Barnes": ("Standard", 0.0, 0, 0, [("2023-24", 17000000, None, 1), ("2024-25", 18000000, None, 1), ("2025-26", 19000000, None, 1)]),
        "Kevin Huerter": ("Standard", 0.0, 0, 0, [("2023-24", 15669643, None, 1), ("2024-25", 16830357, None, 1), ("2025-26", 17991071, None, 1)]),
        "Malik Monk": ("Early Bird", 0.0, 0, 0, [("2023-24", 9945830, None, 1), ("2024-25", 17405203, None, 1), ("2025-26", 18797619, None, 1), ("2026-27", 20190035, None, 1), ("2027-28", 21582451, "Player Option", 1)]),
        "Trey Lyles": ("Standard", 0.0, 0, 0, [("2023-24", 8000000, None, 1), ("2024-25", 8000000, None, 1)]),

        # NOP
        "Zion Williamson": ("Designated Rookie", 0.0, 0, 0, [("2023-24", 34005250, None, 1), ("2024-25", 36725670, None, 1), ("2025-26", 39446090, None, 1), ("2026-27", 42166510, None, 1), ("2027-28", 44886930, None, 1)]),
        "Brandon Ingram": ("Maximum", 0.15, 0, 0, [("2023-24", 33833400, None, 1), ("2024-25", 36016200, None, 1)]),
        "CJ McCollum": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 35802469, None, 1), ("2024-25", 33333333, None, 1), ("2025-26", 30666666, None, 1)]),
        "Herbert Jones": ("Standard", 0.0, 0, 0, [("2023-24", 12000000, None, 1), ("2024-25", 12976362, None, 1), ("2025-26", 13937574, None, 1), ("2026-27", 14898786, "Team Option", 1)]),
        "Jonas Valanciunas": ("Standard", 0.0, 0, 0, [("2023-24", 15435000, None, 1)]),
        "Trey Murphy III": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 3359280, None, 1), ("2024-25", 5159955, "Team Option", 1), ("2025-26", 28000000, None, 1)]),
        "Larry Nance Jr.": ("Standard", 0.0, 0, 0, [("2023-24", 10375000, None, 1), ("2024-25", 11205000, None, 1)]),
        "Dyson Daniels": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 5784120, None, 1), ("2024-25", 6059760, "Team Option", 1), ("2025-26", 7708015, "Team Option", 1)]),

        # ORL
        "Paolo Banchero": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 11608080, None, 1), ("2024-25", 12160800, "Team Option", 1), ("2025-26", 15334769, "Team Option", 1)]),
        "Franz Wagner": ("Designated Rookie", 0.0, 0, 1, [("2023-24", 5508720, None, 1), ("2024-25", 7007092, "Team Option", 1), ("2025-26", 42176400, None, 1), ("2026-27", 45550512, None, 1), ("2027-28", 48924624, None, 1)]),
        "Jonathan Isaac": ("Standard", 0.0, 0, 0, [("2023-24", 17400000, None, 1), ("2024-25", 25000000, None, 1), ("2025-26", 15000000, None, 1), ("2026-27", 15000000, None, 1), ("2027-28", 14500000, None, 1)]),
        "Wendell Carter Jr.": ("Veteran", 0.0, 0, 0, [("2023-24", 13050000, None, 1), ("2024-25", 11950000, None, 1), ("2025-26", 10850000, None, 1)]),
        "Jalen Suggs": ("Rookie Scale", 0.0, 0, 1, [("2023-24", 7252080, None, 1), ("2024-25", 9188385, "Team Option", 1), ("2025-26", 30000000, None, 1), ("2026-27", 30000000, None, 1), ("2027-28", 30000000, None, 1)]),
        "Cole Anthony": ("Standard", 0.0, 0, 0, [("2023-24", 5539771, None, 1), ("2024-25", 12900000, None, 1), ("2025-26", 13100000, None, 1), ("2026-27", 13100000, "Team Option", 1)]),
        "Markelle Fultz": ("Standard", 0.0, 0, 0, [("2023-24", 17000000, None, 1)]),
        "Gary Harris": ("Standard", 0.0, 0, 0, [("2023-24", 13000000, None, 1), ("2024-25", 7500000, None, 1), ("2025-26", 7500000, None, 1)]),

        # ATL
        "Trae Young": ("Designated Rookie", 0.15, 0, 0, [("2023-24", 40064220, None, 1), ("2024-25", 43031940, None, 1), ("2025-26", 45999660, None, 1), ("2026-27", 48967380, "Player Option", 1)]),
        "Dejounte Murray": ("Veteran Extension", 0.15, 0, 0, [("2023-24", 18214000, None, 1), ("2024-25", 25499599, None, 1), ("2025-26", 27539567, None, 1), ("2026-27", 29579535, None, 1), ("2027-28", 31619503, "Player Option", 1)]),
        "Clint Capela": ("Standard", 0.0, 0, 0, [("2023-24", 20616000, None, 1), ("2024-25", 22265280, None, 1)]),
        "De'Andre Hunter": ("Rookie Extension", 0.0, 0, 0, [("2023-24", 20089286, None, 1), ("2024-25", 21696429, None, 1), ("2025-26", 23303571, None, 1), ("2026-27", 24910714, None, 1)]),
        "Bogdan Bogdanovic": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 18700000, None, 1), ("2024-25", 17260000, None, 1), ("2025-26", 16020000, None, 1), ("2026-27", 16020000, "Team Option", 1)]),
        "Onyeka Okongwu": ("Rookie Extension", 0.0, 0, 0, [("2023-24", 8109063, None, 1), ("2024-25", 14000000, None, 1), ("2025-26", 15000000, None, 1), ("2026-27", 16000000, None, 1), ("2027-28", 17000000, None, 1)]),
        "Jalen Johnson": ("Rookie Scale", 0.0, 0, 1, [("2023-24", 2925360, None, 1), ("2024-25", 4510905, "Team Option", 1), ("2025-26", 30000000, None, 1), ("2026-27", 30000000, None, 1), ("2027-28", 30000000, None, 1)]),
        "Saddiq Bey": ("Standard", 0.0, 0, 0, [("2023-24", 4556983, None, 1)]),

        # CHI
        "Zach LaVine": ("Maximum", 0.15, 0, 0, [("2023-24", 40064220, None, 1), ("2024-25", 43031940, None, 1), ("2025-26", 45999660, None, 1), ("2026-27", 48967380, "Player Option", 1)]),
        "DeMar DeRozan": ("Standard", 0.0, 0, 0, [("2023-24", 28600000, None, 1)]),
        "Nikola Vucevic": ("Veteran", 0.0, 0, 0, [("2023-24", 18518519, None, 1), ("2024-25", 20000000, None, 1), ("2025-26", 21481481, None, 1)]),
        "Lonzo Ball": ("Standard", 0.0, 0, 0, [("2023-24", 20465117, None, 1), ("2024-25", 21395348, "Player Option", 1)]),
        "Patrick Williams": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 9835881, None, 1), ("2024-25", 18000000, None, 1), ("2025-26", 18000000, None, 1), ("2026-27", 18000000, None, 1), ("2027-28", 18000000, "Player Option", 1)]),
        "Coby White": ("Standard", 0.0, 0, 0, [("2023-24", 11111111, None, 1), ("2024-25", 12000000, None, 1), ("2025-26", 12888889, None, 1)]),
        "Alex Caruso": ("Standard", 0.0, 0, 0, [("2023-24", 9460000, None, 1), ("2024-25", 9890000, None, 1)]),
        "Ayo Dosunmu": ("Standard", 0.0, 0, 0, [("2023-24", 6481482, None, 1), ("2024-25", 7000000, None, 1), ("2025-26", 7518518, None, 1)]),

        # SAS
        "Victor Wembanyama": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 12160680, None, 1), ("2024-25", 12768960, "Team Option", 1), ("2025-26", 13376880, "Team Option", 1), ("2026-27", 16868246, "Team Option", 1)]),
        "Devin Vassell": ("Rookie Extension", 0.0, 0, 1, [("2023-24", 5887899, None, 1), ("2024-25", 29347826, None, 1), ("2025-26", 27000000, None, 1), ("2026-27", 27000000, None, 1), ("2027-28", 24652174, None, 1)]),
        "Keldon Johnson": ("Rookie Extension", 0.0, 0, 0, [("2023-24", 20000000, None, 1), ("2024-25", 19000000, None, 1), ("2025-26", 17500000, None, 1), ("2026-27", 17500000, None, 1)]),
        "Zach Collins": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 7700000, None, 1), ("2024-25", 16741200, None, 1), ("2025-26", 18080500, None, 1)]),
        "Tre Jones": ("Standard", 0.0, 0, 0, [("2023-24", 9105587, None, 1), ("2024-25", 9105586, None, 1)]),
        "Jeremy Sochan": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 5317080, None, 1), ("2024-25", 5570040, "Team Option", 1), ("2025-26", 7096231, "Team Option", 1)]),

        # MEM
        "Ja Morant": ("Designated Rookie", 0.0, 0, 0, [("2023-24", 34005250, None, 1), ("2024-25", 36725670, None, 1), ("2025-26", 39446090, None, 1), ("2026-27", 42166510, None, 1), ("2027-28", 44886930, None, 1)]),
        "Desmond Bane": ("Designated Rookie", 0.0, 0, 1, [("2023-24", 3845083, None, 1), ("2024-25", 35147000, None, 1), ("2025-26", 37958760, None, 1), ("2026-27", 40770520, None, 1), ("2027-28", 43582280, None, 1), ("2028-29", 46394040, None, 1)]),
        "Jaren Jackson Jr.": ("Veteran", 0.0, 0, 0, [("2023-24", 27102202, None, 1), ("2024-25", 25264915, None, 1), ("2025-26", 23427628, None, 1)]),
        "Marcus Smart": ("Standard", 0.0, 0, 0, [("2023-24", 18583713, None, 1), ("2024-25", 20210285, None, 1), ("2025-26", 21334812, None, 1)]),
        "Luke Kennard": ("Standard", 0.0, 0, 0, [("2023-24", 14763636, "Team Option", 1), ("2024-25", 11000000, None, 1)]),
        "Brandon Clarke": ("Standard", 0.0, 0, 0, [("2023-24", 12500000, None, 1), ("2024-25", 12500000, None, 1), ("2025-26", 12500000, None, 1)]),

        # HOU
        "Fred VanVleet": ("Maximum", 0.0, 0, 0, [("2023-24", 40806300, None, 1), ("2024-25", 42846615, None, 1), ("2025-26", 44886930, "Team Option", 1)]),
        "Dillon Brooks": ("Standard", 0.0, 0, 0, [("2023-24", 22600000, None, 1), ("2024-25", 22255493, None, 1), ("2025-26", 21124110, None, 1), ("2026-27", 19992727, None, 1)]),
        "Jalen Green": ("Rookie Scale", 0.0, 0, 1, [("2023-24", 9891480, None, 1), ("2024-25", 12483048, "Team Option", 1), ("2025-26", 33333333, None, 1), ("2026-27", 36000000, None, 1), ("2027-28", 36666667, "Player Option", 1)]),
        "Alperen Sengun": ("Rookie Scale", 0.0, 0, 1, [("2023-24", 3536280, None, 1), ("2024-25", 5424654, "Team Option", 1), ("2025-26", 33900000, None, 1), ("2026-27", 36612000, None, 1), ("2027-28", 39324000, None, 1), ("2028-29", 42036000, None, 1), ("2029-30", 44748000, "Player Option", 1)]),
        "Jabari Smith Jr.": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 9326520, None, 1), ("2024-25", 9770880, "Team Option", 1), ("2025-26", 12350392, "Team Option", 1)]),
        "Amen Thompson": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 8809320, None, 1), ("2024-25", 9249960, "Team Option", 1), ("2025-26", 9690600, "Team Option", 1), ("2026-27", 12258609, "Team Option", 1)]),
        "Steven Adams": ("Standard", 0.0, 0, 0, [("2023-24", 12600000, None, 1), ("2024-25", 12600000, None, 1)]),

        # UTA
        "John Collins": ("Standard", 0.0, 0, 0, [("2023-24", 25340000, None, 1), ("2024-25", 26580000, None, 1), ("2025-26", 26580000, "Player Option", 1)]),
        "Lauri Markkanen": ("Veteran Extension", 0.0, 0, 0, [("2023-24", 17259999, None, 1), ("2024-25", 18044544, None, 1), ("2025-26", 46394100, None, 1), ("2026-27", 49200000, None, 1), ("2027-28", 52800000, None, 1), ("2028-29", 56400000, None, 1)]),
        "Jordan Clarkson": ("Standard", 0.0, 0, 0, [("2023-24", 23487629, None, 1), ("2024-25", 14092577, None, 1), ("2025-26", 14285714, None, 1)]),
        "Collin Sexton": ("Standard", 0.0, 0, 0, [("2023-24", 17325000, None, 1), ("2024-25", 18150000, None, 1), ("2025-26", 18975000, None, 1)]),
        "Walker Kessler": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 2831160, None, 1), ("2024-25", 2965920, "Team Option", 1), ("2025-26", 4878938, "Team Option", 1)]),
        "Keyonte George": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 3852960, None, 1), ("2024-25", 4045680, "Team Option", 1), ("2025-26", 4238520, "Team Option", 1)]),

        # BKN
        "Ben Simmons": ("Designated Rookie", 0.0, 0, 0, [("2023-24", 37893408, None, 1), ("2024-25", 40338144, None, 1)]),
        "Mikal Bridges": ("Veteran", 0.0, 0, 0, [("2023-24", 21700000, None, 1), ("2024-25", 23300000, None, 1), ("2025-26", 24900000, None, 1)]),
        "Cameron Johnson": ("Standard", 0.0, 0, 0, [("2023-24", 25679348, None, 1), ("2024-25", 23625000, None, 1), ("2025-26", 21570652, None, 1), ("2026-27", 23625000, None, 1)]),
        "Dorian Finney-Smith": ("Standard", 0.0, 0, 0, [("2023-24", 13932008, None, 1), ("2024-25", 14924167, None, 1), ("2025-26", 15378480, "Player Option", 1)]),
        "Nicolas Claxton": ("Standard", 0.0, 0, 0, [("2023-24", 9625000, None, 1), ("2024-25", 28500000, None, 1), ("2025-26", 26220000, None, 1), ("2026-27", 23940000, None, 1), ("2027-28", 21660000, None, 1)]),
        "Dennis Schroder": ("Standard", 0.0, 0, 0, [("2023-24", 12405000, None, 1), ("2024-25", 13025250, None, 1)]),
        "Cam Thomas": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 2240160, None, 1), ("2024-25", 4041249, "Team Option", 1)]),

        # TOR
        "RJ Barrett": ("Rookie Extension", 0.0, 0, 0, [("2023-24", 23883929, None, 1), ("2024-25", 25767857, None, 1), ("2025-26", 27651786, None, 1), ("2026-27", 29535714, None, 1)]),
        "Immanuel Quickley": ("Designated Rookie", 0.0, 0, 0, [("2023-24", 4171698, None, 1), ("2024-25", 32500000, None, 1), ("2025-26", 35100000, None, 1), ("2026-27", 37700000, None, 1), ("2027-28", 40300000, None, 1), ("2028-29", 42900000, None, 1)]),
        "Jakob Poeltl": ("Standard", 0.0, 0, 0, [("2023-24", 19500000, None, 1), ("2024-25", 19500000, None, 1), ("2025-26", 19500000, None, 1), ("2026-27", 19500000, "Player Option", 1)]),
        "Bruce Brown": ("Full MLE", 0.0, 0, 0, [("2023-24", 22000000, None, 1), ("2024-25", 23000000, "Team Option", 1)]),
        "Scottie Barnes": ("Designated Rookie", 0.0, 0, 1, [("2023-24", 8008680, None, 1), ("2024-25", 10130980, "Team Option", 1), ("2025-26", 38700000, None, 1), ("2026-27", 41796000, None, 1), ("2027-28", 44892000, None, 1), ("2028-29", 47988000, None, 1), ("2029-30", 51084000, None, 1)]),
        "Kelly Olynyk": ("Standard", 0.0, 0, 0, [("2023-24", 12195122, None, 1), ("2024-25", 12804878, None, 1), ("2025-26", 13445122, None, 1)]),
        "Chris Boucher": ("Standard", 0.0, 0, 0, [("2023-24", 11750000, None, 1), ("2024-25", 10810000, None, 1)]),

        # POR
        "Deandre Ayton": ("Maximum", 0.0, 0, 0, [("2023-24", 32459438, None, 1), ("2024-25", 34005126, None, 1), ("2025-26", 35550814, None, 1)]),
        "Jerami Grant": ("Veteran", 0.0, 0, 0, [("2023-24", 27586207, None, 1), ("2024-25", 29793104, None, 1), ("2025-26", 32000001, None, 1), ("2026-27", 34206898, None, 1), ("2027-28", 36413795, "Player Option", 1)]),
        "Anfernee Simons": ("Standard", 0.0, 0, 0, [("2023-24", 24107143, None, 1), ("2024-25", 25892857, None, 1), ("2025-26", 27678571, None, 1)]),
        "Malcolm Brogdon": ("Standard", 0.0, 0, 0, [("2023-24", 22500000, None, 1), ("2024-25", 22500000, None, 1)]),
        "Robert Williams III": ("Standard", 0.0, 0, 0, [("2023-24", 11571429, None, 1), ("2024-25", 12428571, None, 1), ("2025-26", 13285713, None, 1)]),
        "Matisse Thybulle": ("Standard", 0.0, 0, 0, [("2023-24", 10500000, None, 1), ("2024-25", 11025000, None, 1), ("2025-26", 11550000, "Player Option", 1)]),
        "Scoot Henderson": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 9770880, None, 1), ("2024-25", 10259520, "Team Option", 1), ("2025-26", 10748400, "Team Option", 1)]),
        "Shaedon Sharpe": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 6313800, None, 1), ("2024-25", 6614160, "Team Option", 1), ("2025-26", 8399983, "Team Option", 1)]),

        # WAS
        "Jordan Poole": ("Rookie Extension", 0.0, 0, 0, [("2023-24", 27455357, None, 1), ("2024-25", 29651786, None, 1), ("2025-26", 31848214, None, 1), ("2026-27", 34044643, None, 1)]),
        "Kyle Kuzma": ("Standard", 0.15, 0, 0, [("2023-24", 25568182, None, 1), ("2024-25", 23522727, None, 1), ("2025-26", 21477273, None, 1), ("2026-27", 19431818, None, 1)]),
        "Tyus Jones": ("Standard", 0.0, 0, 0, [("2023-24", 14000000, None, 1)]),
        "Marvin Bagley III": ("Standard", 0.0, 0, 0, [("2023-24", 12500000, None, 1), ("2024-25", 12500000, None, 1)]),
        "Landry Shamet": ("Standard", 0.0, 0, 0, [("2023-24", 10250000, None, 1), ("2024-25", 11000000, None, 1), ("2025-26", 11750000, "Team Option", 1)]),
        "Richaun Holmes": ("Standard", 0.0, 0, 0, [("2023-24", 12046511, None, 1), ("2024-25", 12628999, "Player Option", 1), ("2025-26", 13211487, None, 1)]),
        "Bilal Coulibaly": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 6614160, None, 1), ("2024-25", 6945240, "Team Option", 1), ("2025-26", 7275720, "Team Option", 1)]),
        "Deni Avdija": ("Rookie Extension", 0.0, 0, 0, [("2023-24", 6263188, None, 1), ("2024-25", 15625000, None, 1), ("2025-26", 14375000, None, 1), ("2026-27", 13125000, None, 1), ("2027-28", 11875000, None, 1)]),
        "Corey Kispert": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 3722040, None, 1), ("2024-25", 5705887, "Team Option", 1), ("2025-26", 13500000, None, 1), ("2026-27", 13500000, None, 1)]),

        # DET
        "Cade Cunningham": ("Designated Rookie", 0.0, 0, 1, [("2023-24", 11055360, None, 1), ("2024-25", 13940809, "Team Option", 1), ("2025-26", 42176400, None, 1), ("2026-27", 45550512, None, 1), ("2027-28", 48924624, None, 1), ("2028-29", 52298736, None, 1), ("2029-30", 55672848, None, 1)]),
        "Bojan Bogdanovic": ("Standard", 0.0, 0, 0, [("2023-24", 20000000, None, 1), ("2024-25", 19032000, None, 1)]),
        "Joe Harris": ("Standard", 0.0, 0, 0, [("2023-24", 19928571, None, 1)]),
        "Isaiah Stewart": ("Rookie Extension", 0.0, 0, 0, [("2023-24", 5266713, None, 1), ("2024-25", 15000000, None, 1), ("2025-26", 15000000, None, 1), ("2026-27", 15000000, None, 1), ("2027-28", 15000000, "Team Option", 1)]),
        "Jaden Ivey": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 7614480, None, 1), ("2024-25", 7977240, "Team Option", 1), ("2025-26", 10107163, "Team Option", 1)]),
        "Ausar Thompson": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 7977240, None, 1), ("2024-25", 8376000, "Team Option", 1), ("2025-26", 8775000, "Team Option", 1)]),
        "Jalen Duren": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 4330680, None, 1), ("2024-25", 4536840, "Team Option", 1), ("2025-26", 6483144, "Team Option", 1)]),
        "James Wiseman": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 12119440, None, 1)]),

        # CHA
        "LaMelo Ball": ("Designated Rookie", 0.0, 0, 1, [("2023-24", 10900635, None, 1), ("2024-25", 35147000, None, 1), ("2025-26", 37958760, None, 1), ("2026-27", 40770520, None, 1), ("2027-28", 43582280, None, 1), ("2028-29", 46394040, None, 1)]),
        "Miles Bridges": ("Standard", 0.0, 0, 0, [("2023-24", 7921300, None, 1), ("2024-25", 27000000, None, 1), ("2025-26", 25000000, None, 1), ("2026-27", 23000000, None, 1)]),
        "Grant Williams": ("Full MLE", 0.0, 0, 0, [("2023-24", 12405000, None, 1), ("2024-25", 13025250, None, 1), ("2025-26", 13645500, None, 1), ("2026-27", 14265750, None, 1)]),
        "Brandon Miller": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 10880400, None, 1), ("2024-25", 11424240, "Team Option", 1), ("2025-26", 11968560, "Team Option", 1)]),
        "Mark Williams": ("Rookie Scale", 0.0, 0, 0, [("2023-24", 3908160, None, 1), ("2024-25", 4094280, "Team Option", 1), ("2025-26", 6276531, "Team Option", 1)]),
        "Seth Curry": ("Standard", 0.0, 0, 0, [("2023-24", 4000000, None, 1), ("2024-25", 4000000, None, 1)]),
        "Davis Bertans": ("Standard", 0.0, 0, 0, [("2023-24", 17000000, None, 1), ("2024-25", 16000000, "Early Termination Option", 1)]),
        "Nick Richards": ("Standard", 0.0, 0, 0, [("2023-24", 5000000, None, 1), ("2024-25", 5000000, None, 1), ("2025-26", 5000000, None, 1)])
    }

    # Now let's fetch all active players from player_season_stats for 2023-24
    # to guarantee 14-16 players for EVERY team!
    team_rosters = {}
    query = """
    SELECT pss.team_abbreviation, pss.player_id, p.full_name, pss.min, pss.pts
    FROM player_season_stats pss
    JOIN players p ON pss.player_id = p.player_id
    WHERE pss.season = '2023-24' AND pss.season_type = 'Regular Season' AND pss.team_abbreviation != 'TOT'
    ORDER BY pss.team_abbreviation, pss.min DESC
    """
    rows = c.execute(query).fetchall()
    for tabbr, pid, fname, mins, pts in rows:
        if tabbr not in team_map:
            continue
        if tabbr not in team_rosters:
            team_rosters[tabbr] = []
        team_rosters[tabbr].append({
            "player_id": pid,
            "player_name": fname,
            "min": mins or 0.0,
            "pts": pts or 0.0
        })

    # Build contracts list
    contracts_out = []
    contract_years_out = []
    dead_money_out = [
        {"team_abbreviation": "POR", "player_name": "Eric Bledsoe", "season": "2023-24", "amount": 3900000.0, "is_stretched": 1, "notes": "Waived & Stretched"},
        {"team_abbreviation": "POR", "player_name": "Eric Bledsoe", "season": "2024-25", "amount": 3900000.0, "is_stretched": 1, "notes": "Waived & Stretched"},
        {"team_abbreviation": "BOS", "player_name": "Demetrius Jackson", "season": "2023-24", "amount": 92857.0, "is_stretched": 1, "notes": "Waived & Stretched"},
        {"team_abbreviation": "LAL", "player_name": "Luol Deng", "season": "2023-24", "amount": 0.0, "is_stretched": 0, "notes": "Expired"},
        {"team_abbreviation": "DEN", "player_name": "Reggie Bullock", "season": "2023-24", "amount": 1000000.0, "is_stretched": 0, "notes": "Waived"}
    ]
    tpe_out = [
        {"team_abbreviation": "BOS", "amount": 6250000.0, "created_season": "2023-24", "expires_date": "2024-07-12", "source_player": "Grant Williams", "notes": "Sign & Trade to DAL"},
        {"team_abbreviation": "OKC", "amount": 7400000.0, "created_season": "2023-24", "expires_date": "2024-07-08", "source_player": "Davis Bertans", "notes": "Trade to CHA"},
        {"team_abbreviation": "GSW", "amount": 8000000.0, "created_season": "2023-24", "expires_date": "2024-07-06", "source_player": "Donte DiVincenzo", "notes": "Trade"}
    ]

    seen_players = set()
    contract_idx = 1000

    for tabbr, roster in team_rosters.items():
        tid = team_map[tabbr]
        # Keep top 14-15 players
        active_roster = roster[:15]
        for rank, pinfo in enumerate(active_roster):
            pid = pinfo["player_id"]
            name = pinfo["player_name"]
            if pid in seen_players:
                continue
            seen_players.add(pid)

            cid = f"CTR-{tabbr}-{pid}"
            
            # Check if we have exact real contract terms
            matched_key = None
            for rk in REAL_CONTRACTS:
                if norm(rk) == norm(name) or clean_suffix(norm(rk)) == clean_suffix(norm(name)):
                    matched_key = rk
                    break

            if matched_key:
                ctype, kicker, ntc, pp, yearly = REAL_CONTRACTS[matched_key]
                tot_years = len(yearly)
                tot_val = sum(y[1] for y in yearly)
                contracts_out.append({
                    "contract_id": cid,
                    "player_id": pid,
                    "player_name": name,
                    "team_id": tid,
                    "team_abbreviation": tabbr,
                    "total_years": tot_years,
                    "total_value": float(tot_val),
                    "contract_type": ctype,
                    "signed_using": "Bird Rights" if "Veteran" in ctype or "Maximum" in ctype else "Standard",
                    "bird_rights": "Full Bird",
                    "trade_kicker_pct": kicker,
                    "poison_pill": pp,
                    "no_trade_clause": ntc,
                    "is_active": 1
                })
                for ssn, sal, opt, guar in yearly:
                    contract_years_out.append({
                        "contract_id": cid,
                        "season": ssn,
                        "base_salary": float(sal),
                        "cap_hit": float(sal),
                        "guaranteed_amount": float(sal) if guar else 0.0,
                        "option_type": opt,
                        "is_guaranteed": guar
                    })
            else:
                # Tiered realistic contract based on MPG and rank
                mins = pinfo["min"]
                if mins >= 28.0:
                    base_sal = 14000000.0
                    ctype = "Standard"
                elif mins >= 20.0:
                    base_sal = 7500000.0
                    ctype = "Standard"
                elif mins >= 12.0:
                    base_sal = 3800000.0
                    ctype = "Standard"
                else:
                    base_sal = 2019706.0
                    ctype = "Minimum"

                # 2 seasons: 2023-24 and 2024-25 (+5% raise)
                sal_23 = round(base_sal, 0)
                sal_24 = round(base_sal * 1.05, 0)
                tot_val = sal_23 + sal_24

                contracts_out.append({
                    "contract_id": cid,
                    "player_id": pid,
                    "player_name": name,
                    "team_id": tid,
                    "team_abbreviation": tabbr,
                    "total_years": 2,
                    "total_value": float(tot_val),
                    "contract_type": ctype,
                    "signed_using": "Standard",
                    "bird_rights": "Early Bird",
                    "trade_kicker_pct": 0.0,
                    "poison_pill": 0,
                    "no_trade_clause": 0,
                    "is_active": 1
                })
                contract_years_out.append({
                    "contract_id": cid,
                    "season": "2023-24",
                    "base_salary": float(sal_23),
                    "cap_hit": float(sal_23),
                    "guaranteed_amount": float(sal_23),
                    "option_type": None,
                    "is_guaranteed": 1
                })
                contract_years_out.append({
                    "contract_id": cid,
                    "season": "2024-25",
                    "base_salary": float(sal_24),
                    "cap_hit": float(sal_24),
                    "guaranteed_amount": float(sal_24),
                    "option_type": "Team Option" if rank >= 10 else None,
                    "is_guaranteed": 1
                })

    seed_data = {
        "cba_settings": cba_settings,
        "contracts": contracts_out,
        "contract_years": contract_years_out,
        "dead_money": dead_money_out,
        "trade_exceptions": tpe_out
    }

    os.makedirs("data", exist_ok=True)
    out_file = os.path.abspath(os.path.join("data", "contracts_seed.json"))
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(seed_data, f, indent=2)

    print(f"Generated contracts seed with {len(contracts_out)} contracts and {len(contract_years_out)} contract years at {out_file}")

if __name__ == "__main__":
    run()
