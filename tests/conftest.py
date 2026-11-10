"""Shared fixtures: a small deterministic dataset so tests never depend on data/ipl_cleaned_data.csv."""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src import api
from src.data_cleaning import assign_over_phase

BALLS_PER_INNINGS = 120

# (match_id, season_year, first-innings team, first-innings total, second-innings team,
#  second-innings total, winner). Chase buckets: Low x1, Medium x1, High x2.
_MATCHES = [
    (1, 2022, "Royal Challengers Bengaluru", 125, "Mumbai Indians", 120, "Royal Challengers Bengaluru"),
    (2, 2023, "Mumbai Indians", 145, "Royal Challengers Bengaluru", 146, "Royal Challengers Bengaluru"),
    (3, 2023, "Chennai Super Kings", 170, "Mumbai Indians", 150, "Chennai Super Kings"),
    (4, 2024, "Chennai Super Kings", 165, "Royal Challengers Bengaluru", 166, "Royal Challengers Bengaluru"),
]
_BATTERS = {
    "Royal Challengers Bengaluru": ["V Kohli", "F du Plessis", "G Maxwell"],
    "Mumbai Indians": ["RG Sharma", "Ishan Kishan", "SA Yadav"],
    "Chennai Super Kings": ["RD Gaikwad", "MS Dhoni", "RA Jadeja"],
}
_BOWLERS = {
    "Royal Challengers Bengaluru": ["YS Chahal", "Mohammed Siraj"],
    "Mumbai Indians": ["JJ Bumrah", "PP Chawla"],
    "Chennai Super Kings": ["DJ Bravo", "Deepak Chahar"],
}


def _innings(match_id, season_year, innings, bat_team, bowl_team, total, winner):
    """120 deliveries whose runs sum to `total` (1 or 2 runs a ball, so no unrealistic rows)."""
    base, extra = divmod(total, BALLS_PER_INNINGS)
    rows = []
    for i in range(BALLS_PER_INNINGS):
        runs = base + (1 if i < extra else 0)
        over = i // 6
        rows.append({
            "match_id": match_id,
            "season_year": season_year,
            "innings": innings,
            "over": over,
            "ball": i % 6 + 1,
            "batting_team": bat_team,
            "bowling_team": bowl_team,
            "batter": _BATTERS[bat_team][i % 3],
            "bowler": _BOWLERS[bowl_team][over % 2],
            "runs": runs,
            "extras": 0,
            "runs_total": runs,
            "runs_conceded_bowler": runs,
            "is_wicket": 0,
            "player_dismissed": "Not Out",
            "match_won_by": winner,
            "toss_winner": bat_team,
            "phase": assign_over_phase(over),
        })
    return rows


@pytest.fixture
def ipl_df() -> pd.DataFrame:
    """4 matches / 8 innings / 960 deliveries in the cleaned-data schema."""
    rows = []
    for match_id, season, t1, total1, t2, total2, winner in _MATCHES:
        rows += _innings(match_id, season, 1, t1, t2, total1, winner)
        rows += _innings(match_id, season, 2, t2, t1, total2, winner)
    df = pd.DataFrame(rows)

    # Chahal (RCB bowler, bowls even overs in innings where RCB bowl): 3 bowler-credited wickets
    # plus one run out that is a dismissal but NOT a bowler wicket.
    chahal = df.index[(df["bowler"] == "YS Chahal") & (df["match_id"] == 1)]
    df.loc[chahal[[0, 1, 2]], "is_wicket"] = 1
    df.loc[chahal[[0, 1, 2]], "player_dismissed"] = "Some Batter"
    df.loc[chahal[3], "player_dismissed"] = "Run Out Victim"  # is_wicket stays 0
    return df


@pytest.fixture
def api_client(monkeypatch, ipl_df) -> TestClient:
    """TestClient whose dataset singleton is the in-memory fixture (restored after each test)."""
    monkeypatch.setattr(api, "_DATA", ipl_df)
    return TestClient(api.app)
