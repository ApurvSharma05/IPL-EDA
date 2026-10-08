"""Tests for Pandera validation and evaluation benchmark."""

import pandas as pd
import pandera.errors as pa_errors
import pytest

from src.validation import run_evaluation_suite, validate_deliveries_dataframe


def test_validation_schema_valid_data():
    valid_df = pd.DataFrame({
        "match_id": [1, 2],
        "innings": [1, 2],
        "over": [0, 19],
        "ball": [1, 6],
        "batting_team": ["Mumbai Indians", "Chennai Super Kings"],
        "bowling_team": ["Chennai Super Kings", "Mumbai Indians"],
        "batter": ["RG Sharma", "MS Dhoni"],
        "bowler": ["DJ Bravo", "JJ Bumrah"],
        "runs": [4, 6],
        "extras": [0, 1],
        "runs_total": [4, 7],
        "is_wicket": [0, 0],
    })

    result = validate_deliveries_dataframe(valid_df)
    assert len(result) == 2


def test_validation_schema_invalid_over():
    invalid_df = pd.DataFrame({
        "match_id": [1],
        "innings": [1],
        "over": [25],  # Invalid over (> 19)
        "ball": [1],
        "batting_team": ["Mumbai Indians"],
        "bowling_team": ["Chennai Super Kings"],
        "batter": ["RG Sharma"],
        "bowler": ["DJ Bravo"],
        "runs": [4],
        "extras": [0],
        "runs_total": [4],
        "is_wicket": [0],
    })

    with pytest.raises(pa_errors.SchemaError):
        validate_deliveries_dataframe(invalid_df)
