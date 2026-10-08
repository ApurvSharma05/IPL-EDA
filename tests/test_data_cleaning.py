"""Unit tests for data cleaning and feature engineering functions."""

import pandas as pd
import pytest

from src.data_cleaning import assign_over_phase, clean_ipl_telemetry


def test_assign_over_phase():
    assert assign_over_phase(0) == "PowerPlay (1-6)"
    assert assign_over_phase(5) == "PowerPlay (1-6)"
    assert assign_over_phase(6) == "Middle (7-15)"
    assert assign_over_phase(14) == "Middle (7-15)"
    assert assign_over_phase(15) == "Death (16-20)"
    assert assign_over_phase(19) == "Death (16-20)"


def test_clean_ipl_telemetry_team_standardization():
    raw_data = pd.DataFrame({
        "match_id": [1, 2],
        "season": ["2008", "2020/21"],
        "date": ["2008-04-18", "2020-10-15"],
        "batting_team": ["Delhi Daredevils", "Kings XI Punjab"],
        "bowling_team": ["Royal Challengers Bangalore", "Rising Pune Supergiants"],
        "match_won_by": ["Delhi Daredevils", "Kings XI Punjab"],
        "toss_winner": ["Delhi Daredevils", "Kings XI Punjab"],
        "over": [0, 18],
        "ball": [1, 5],
        "batter": ["V Kohli", "KL Rahul"],
        "bowler": ["Z Khan", "JJ Bumrah"],
        "runs_batter": [4, 6],
        "runs_extras": [0, 1],
        "bowler_wicket": [0, 1],
    })

    cleaned = clean_ipl_telemetry(raw_data)

    assert cleaned["batting_team"].iloc[0] == "Delhi Capitals"
    assert cleaned["batting_team"].iloc[1] == "Punjab Kings"
    assert cleaned["bowling_team"].iloc[0] == "Royal Challengers Bengaluru"
    assert cleaned["bowling_team"].iloc[1] == "Rising Pune Supergiant"
    assert cleaned["match_won_by"].iloc[0] == "Delhi Capitals"
    assert cleaned["winning_team"].iloc[0] == "Delhi Capitals"
    assert cleaned["season_year"].iloc[0] == 2008
    assert cleaned["season_year"].iloc[1] == 2020


def test_clean_ipl_telemetry_metrics_derivation():
    raw_data = pd.DataFrame({
        "match_id": [101, 101],
        "season": ["2015", "2015"],
        "date": ["2015-05-01", "2015-05-01"],
        "batting_team": ["Mumbai Indians", "Mumbai Indians"],
        "bowling_team": ["Chennai Super Kings", "Chennai Super Kings"],
        "over": [1, 2],
        "ball": [1, 2],
        "batter": ["RG Sharma", "RG Sharma"],
        "bowler": ["R Ashwin", "R Ashwin"],
        "runs_batter": [0, 4],
        "runs_extras": [4, 0],
        "extra_type": ["byes", None],
        "bowler_wicket": [0, 1],
    })

    cleaned = clean_ipl_telemetry(raw_data)

    # Ball 1 had 4 byes: total runs = 4, but bowler conceded = 0
    assert cleaned["runs_total"].iloc[0] == 4
    assert cleaned["runs_conceded_bowler"].iloc[0] == 0

    # Ball 2 was a boundary: total runs = 4, bowler conceded = 4, wicket = 1
    assert cleaned["runs_total"].iloc[1] == 4
    assert cleaned["runs_conceded_bowler"].iloc[1] == 4
    assert cleaned["is_wicket"].iloc[1] == 1
