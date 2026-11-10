"""Integration tests for FastAPI endpoints.

All tests run against the small in-memory dataset from `conftest.py` (via the `api_client`
fixture), so they pass on a clean checkout with no `data/` files or pipeline run.
"""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src import api
from src.config import SAMPLE_DATA_PATH
from src.metrics import get_top_batsmen, get_top_bowlers


def test_health_endpoint(api_client, ipl_df):
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["records_loaded"] == len(ipl_df) == 960
    assert data["seasons_covered"] == "2022 - 2024"
    assert "version" in data


def test_get_batsman_endpoint_valid(api_client, ipl_df):
    response = api_client.get("/api/v1/players/batting?name=v%20kohli")  # case-insensitive
    assert response.status_code == 200
    data = response.json()

    kohli = ipl_df[ipl_df["batter"] == "V Kohli"]
    assert data["batter"] == "V Kohli"
    assert data["total_runs"] == int(kohli["runs"].sum())
    assert data["balls_faced"] == len(kohli)
    assert data["matches_played"] == 3
    assert data["strike_rate"] == round(kohli["runs"].sum() / len(kohli) * 100, 2)


def test_get_batsman_endpoint_not_found(api_client):
    response = api_client.get("/api/v1/players/batting?name=NoSuchPlayerXYZ")
    assert response.status_code == 404


def test_get_bowler_endpoint_valid(api_client, ipl_df):
    response = api_client.get("/api/v1/players/bowling?name=YS%20Chahal")
    assert response.status_code == 200
    data = response.json()

    chahal = ipl_df[ipl_df["bowler"] == "YS Chahal"]
    balls = len(chahal)
    runs = int(chahal["runs_conceded_bowler"].sum())
    assert data["bowler"] == "YS Chahal"
    # Bowler-credited wickets only: the run out row is excluded.
    assert data["wickets"] == 3
    assert data["runs_conceded"] == runs
    assert data["overs_bowled"] == round(balls / 6, 1)
    assert data["economy_rate"] == round(runs / (balls / 6), 2)


def test_get_bowler_endpoint_not_found(api_client):
    assert api_client.get("/api/v1/players/bowling?name=NoSuchPlayerXYZ").status_code == 404


def test_player_endpoints_match_metrics_module(api_client, ipl_df):
    """The API and the leaderboard functions must agree to the last digit (single formula source)."""
    bowlers = get_top_bowlers(ipl_df, min_overs=0, limit=100).set_index("bowler")
    for name, row in bowlers.iterrows():
        data = api_client.get("/api/v1/players/bowling", params={"name": name}).json()
        assert data["economy_rate"] == row["economy_rate"], name
        assert data["wickets"] == row["wickets"], name
        assert data["wickets_per_match"] == row["wickets_per_match"], name

    batters = get_top_batsmen(ipl_df, min_matches=1, limit=100).set_index("batter")
    for name, row in batters.iterrows():
        data = api_client.get("/api/v1/players/batting", params={"name": name}).json()
        assert data["strike_rate"] == row["strike_rate"], name
        assert data["runs_per_match"] == row["runs_per_match"], name


def test_get_teams_summary(api_client):
    response = api_client.get("/api/v1/teams/summary")
    assert response.status_code == 200
    teams = {t["team"]: t for t in response.json()}
    assert set(teams) == {"Royal Challengers Bengaluru", "Mumbai Indians", "Chennai Super Kings"}
    assert teams["Royal Challengers Bengaluru"]["matches_won"] == 3
    assert teams["Royal Challengers Bengaluru"]["win_percentage"] == 100.0
    assert teams["Chennai Super Kings"]["win_percentage"] == 50.0
    assert teams["Mumbai Indians"]["matches_won"] == 0  # never won: still listed with 0 wins


def test_get_teams_summary_min_matches_filter(api_client):
    # Default is 0 (no cutoff); an explicit cutoff drops teams with fewer matches.
    assert len(api_client.get("/api/v1/teams/summary").json()) == 3
    filtered = api_client.get("/api/v1/teams/summary?min_matches=3").json()
    assert {t["team"] for t in filtered} == {"Royal Challengers Bengaluru", "Mumbai Indians"}


def test_get_team_stats_by_name(api_client):
    response = api_client.get("/api/v1/teams/chennai%20super%20kings")
    assert response.status_code == 200
    assert response.json()["matches_played"] == 2
    assert api_client.get("/api/v1/teams/Nobody").status_code == 404


def test_get_chase_analytics(api_client):
    response = api_client.get("/api/v1/analytics/chase-success")
    assert response.status_code == 200
    data = response.json()
    assert data["overall_chase_win_pct"] == 50.0  # 2 successful chases out of 4
    breakdown = {b["target_range"]: b for b in data["breakdown"]}
    assert list(breakdown) == ["Low (<130)", "Medium (130-159)", "High (160+)"]
    assert (breakdown["Low (<130)"]["attempts"], breakdown["Low (<130)"]["successful"]) == (1, 0)
    assert (breakdown["Medium (130-159)"]["attempts"], breakdown["Medium (130-159)"]["successful"]) == (1, 1)
    assert (breakdown["High (160+)"]["attempts"], breakdown["High (160+)"]["successful"]) == (2, 1)


def test_get_phase_analytics(api_client, ipl_df):
    response = api_client.get("/api/v1/analytics/over-phases")
    assert response.status_code == 200
    phases = response.json()["phases"]
    assert [p["phase"] for p in phases] == ["PowerPlay (1-6)", "Middle (7-15)", "Death (16-20)"]
    assert sum(p["total_runs"] for p in phases) == int(ipl_df["runs_total"].sum())
    powerplay = phases[0]
    assert powerplay["overs"] == pytest.approx(len(ipl_df[ipl_df["over"] < 6]) / 6)


@pytest.mark.skipif(not SAMPLE_DATA_PATH.exists(), reason="bundled sample dataset not present")
def test_dataset_falls_back_to_bundled_sample(monkeypatch, tmp_path):
    """With no cleaned CSV on disk (fresh clone), the API serves the checked-in sample."""
    monkeypatch.setattr(api, "_DATA", None)
    monkeypatch.setattr(api, "CLEANED_DATA_PATH", tmp_path / "missing.csv")
    response = TestClient(api.app).get("/health")
    assert response.status_code == 200
    assert response.json()["records_loaded"] == len(pd.read_csv(SAMPLE_DATA_PATH, low_memory=False))
