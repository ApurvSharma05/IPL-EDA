"""Unit tests for analytical calculation functions."""

import pandas as pd
import pytest

from src.metrics import (
    get_chase_success_rates,
    get_team_win_statistics,
    get_top_batsmen,
    get_top_bowlers,
)


@pytest.fixture
def sample_match_data():
    return pd.DataFrame({
        "match_id": [1, 1, 1, 1, 2, 2, 2, 2],
        "season_year": [2021, 2021, 2021, 2021, 2022, 2022, 2022, 2022],
        "innings": [1, 1, 2, 2, 1, 1, 2, 2],
        "over": [0, 19, 0, 18, 1, 15, 2, 19],
        "ball": [1, 6, 1, 5, 2, 3, 4, 6],
        "batting_team": [
            "Chennai Super Kings", "Chennai Super Kings",
            "Delhi Capitals", "Delhi Capitals",
            "Mumbai Indians", "Mumbai Indians",
            "Kolkata Knight Riders", "Kolkata Knight Riders",
        ],
        "bowling_team": [
            "Delhi Capitals", "Delhi Capitals",
            "Chennai Super Kings", "Chennai Super Kings",
            "Kolkata Knight Riders", "Kolkata Knight Riders",
            "Mumbai Indians", "Mumbai Indians",
        ],
        "batter": [
            "RD Gaikwad", "MS Dhoni", "RR Pant", "RR Pant",
            "RG Sharma", "SA Yadav", "SS Iyer", "SS Iyer",
        ],
        "bowler": [
            "Avesh Khan", "Avesh Khan", "DJ Bravo", "DJ Bravo",
            "TG Southee", "TG Southee", "JJ Bumrah", "JJ Bumrah",
        ],
        "runs": [4, 6, 4, 4, 6, 6, 1, 4],
        "extras": [0, 0, 0, 1, 0, 0, 0, 0],
        "runs_total": [4, 6, 4, 5, 6, 6, 1, 4],
        "runs_conceded_bowler": [4, 6, 4, 5, 6, 6, 1, 4],
        "is_wicket": [0, 0, 0, 1, 0, 0, 1, 0],
        "match_won_by": [
            "Delhi Capitals", "Delhi Capitals", "Delhi Capitals", "Delhi Capitals",
            "Mumbai Indians", "Mumbai Indians", "Mumbai Indians", "Mumbai Indians",
        ],
    })


def test_get_top_batsmen(sample_match_data):
    top_bats = get_top_batsmen(sample_match_data, min_matches=1, limit=5)
    assert not top_bats.empty
    # SA Yadav scored 6 runs in 1 ball -> SR = 600.0
    sky = top_bats[top_bats["batter"] == "SA Yadav"].iloc[0]
    assert sky["total_runs"] == 6
    assert sky["balls_faced"] == 1
    assert sky["strike_rate"] == 600.0


def test_get_chase_success_accuracy(sample_match_data):
    # Match 1: CSK batted 1st (total 10), DC chased (total 9), match_won_by = DC -> Chase Successful
    # Match 2: MI batted 1st (total 12), KKR chased (total 5), match_won_by = MI -> Chase Failed
    # Overall chase rate should be 1/2 = 50%
    overall_rate, range_df = get_chase_success_rates(sample_match_data)
    assert overall_rate == 50.0
    assert len(range_df) > 0


def test_get_team_win_statistics(sample_match_data):
    stats = get_team_win_statistics(sample_match_data)
    # DC: 1 played, 1 won -> 100%
    dc = stats[stats["team"] == "Delhi Capitals"].iloc[0]
    assert dc["matches_played"] == 1
    assert dc["matches_won"] == 1
    assert dc["win_percentage"] == 100.0

    # CSK: 1 played, 0 won -> 0%
    csk = stats[stats["team"] == "Chennai Super Kings"].iloc[0]
    assert csk["matches_played"] == 1
    assert csk["matches_won"] == 0
    assert csk["win_percentage"] == 0.0
