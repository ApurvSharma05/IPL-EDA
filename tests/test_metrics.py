"""Unit tests for analytical calculation functions."""

import pandas as pd
import pytest

import inspect

from src import metrics
from src.config import MIN_BATTER_MATCHES_FILTER, MIN_BOWLER_OVERS_FILTER
from src.metrics import (
    count_dismissals,
    economy_rate,
    get_chase_success_rates,
    get_team_win_statistics,
    get_top_batsmen,
    get_top_bowlers,
    strike_rate,
    summarize_bowler,
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


def test_economy_uses_unrounded_overs():
    # 100 balls = 16.667 overs; 130 runs -> exactly 7.80. Rounding overs to 16.7 first would give 7.78.
    assert economy_rate(130, 100) == 7.8
    assert economy_rate(0, 0) == 0.0  # no balls, no division error
    assert strike_rate(30, 20) == 150.0
    assert strike_rate(5, 0) == 0.0


def test_shared_formulas_accept_series_and_scalars():
    runs = pd.Series([130, 10, 3])
    balls = pd.Series([100, 0, 6])
    assert economy_rate(runs, balls).tolist() == [7.8, 0.0, 3.0]


def test_bowler_summary_matches_leaderboard_row():
    rows = 100  # a bowler with 100 balls, 130 runs, 2 bowler wickets
    df = pd.DataFrame({
        "match_id": [i // 25 for i in range(rows)],
        "bowler": ["B1"] * rows,
        "runs_conceded_bowler": [1] * 70 + [2] * 30,
        "is_wicket": [1, 1] + [0] * (rows - 2),
    })
    line = summarize_bowler(df)
    board = get_top_bowlers(df, min_overs=0).iloc[0]
    assert line["economy_rate"] == board["economy_rate"] == 7.8
    assert line["overs_bowled"] == board["overs"] == 16.7
    assert line["wickets"] == board["wickets"] == 2


def test_wicket_flag_is_bowler_credited_and_dismissals_counted_separately():
    df = pd.DataFrame({
        "is_wicket": [0, 1, 0, 0],
        "player_dismissed": ["Not Out", "A", "B", "Not Out"],  # row 2 is a run out
    })
    assert int(df["is_wicket"].sum()) == 1
    assert count_dismissals(df) == 2


def test_leaderboard_defaults_come_from_config():
    assert inspect.signature(metrics.get_top_batsmen).parameters["min_matches"].default == MIN_BATTER_MATCHES_FILTER
    assert inspect.signature(metrics.get_top_bowlers).parameters["min_overs"].default == MIN_BOWLER_OVERS_FILTER
