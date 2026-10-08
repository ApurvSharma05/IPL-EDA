"""Integration tests for FastAPI endpoints."""

from fastapi.testclient import TestClient
import pytest

from src.api import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["records_loaded"] > 0
    assert "version" in data


def test_get_batsman_endpoint_valid():
    response = client.get("/api/v1/players/batting?name=V%20Kohli")
    assert response.status_code == 200
    data = response.json()
    assert data["batter"] == "V Kohli"
    assert data["total_runs"] > 8000
    assert data["strike_rate"] > 100.0


def test_get_batsman_endpoint_not_found():
    response = client.get("/api/v1/players/batting?name=NoSuchPlayerXYZ")
    assert response.status_code == 404


def test_get_bowler_endpoint_valid():
    response = client.get("/api/v1/players/bowling?name=YS%20Chahal")
    assert response.status_code == 200
    data = response.json()
    assert data["bowler"] == "YS Chahal"
    assert data["wickets"] > 150
    assert data["economy_rate"] > 6.0


def test_get_teams_summary():
    response = client.get("/api/v1/teams/summary")
    assert response.status_code == 200
    teams = response.json()
    assert len(teams) >= 10
    mi = next((t for t in teams if t["team"] == "Mumbai Indians"), None)
    assert mi is not None
    assert mi["matches_won"] > 100


def test_get_chase_analytics():
    response = client.get("/api/v1/analytics/chase-success")
    assert response.status_code == 200
    data = response.json()
    assert 48.0 <= data["overall_chase_win_pct"] <= 56.0
    assert len(data["breakdown"]) == 3


def test_get_phase_analytics():
    response = client.get("/api/v1/analytics/over-phases")
    assert response.status_code == 200
    data = response.json()
    phases = data["phases"]
    assert len(phases) == 3
    phase_names = [p["phase"] for p in phases]
    assert "PowerPlay (1-6)" in phase_names
    assert "Death (16-20)" in phase_names
