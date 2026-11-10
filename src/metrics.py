"""Pure analytical and statistical aggregation metrics for IPL telemetry."""

import logging
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd

from src.config import (
    MIN_BATTER_MATCHES_FILTER,
    MIN_BOWLER_OVERS_FILTER,
    MIN_TEAM_MATCHES_CONSISTENCY,
    PHASE_ORDER,
    TARGET_HIGH,
    TARGET_LOW,
    TARGET_MEDIUM,
    TARGET_ORDER,
)

logger = logging.getLogger(__name__)


# --- Shared metric formulas (single source of truth for the API and the metrics module) ---

def _safe_ratio(numerator, denominator, decimals: int = 2):
    """Rounded numerator / denominator; 0.0 wherever the denominator is not positive.

    Works on plain numbers and on aligned pandas Series, so row-level (API) and
    leaderboard-level (groupby) code share exactly one implementation.
    """
    if np.ndim(denominator) == 0:
        if denominator <= 0:
            return 0.0
        return round(float(numerator) / float(denominator), decimals)
    ratio = numerator / denominator.where(denominator > 0)
    return ratio.fillna(0.0).round(decimals)


def balls_to_overs(balls):
    """Converts a ball count to fractional overs (balls / 6). Never rounded here."""
    return balls / 6.0


def strike_rate(runs, balls):
    """Batting strike rate: runs per 100 balls."""
    return _safe_ratio(runs * 100, balls)


def economy_rate(runs_conceded, balls):
    """Bowling economy: runs conceded per over, computed from balls / 6 without pre-rounding overs."""
    return _safe_ratio(runs_conceded, balls_to_overs(balls))


def per_match(total, matches):
    """Average of a counting stat per match played."""
    return _safe_ratio(total, matches)


def resolve_bowling_columns(df: pd.DataFrame) -> Tuple[str, str]:
    """Returns (runs_conceded_column, bowler_wicket_column) for the given schema.

    Note: `is_wicket` in the cleaned data is bowler-credited wickets only (it equals the raw
    `bowler_wicket` flag and excludes run outs, retired out, etc.). See `count_dismissals`
    for every dismissal.
    """
    runs_col = "runs_conceded_bowler" if "runs_conceded_bowler" in df.columns else "runs_total"
    wicket_col = "is_wicket" if "is_wicket" in df.columns else "wickets"
    return runs_col, wicket_col


def count_dismissals(df: pd.DataFrame) -> int:
    """Total dismissals of any kind (bowler-credited wickets plus run outs and similar).

    On the full dataset this is larger than `df["is_wicket"].sum()` (14,705 vs 13,488),
    because `is_wicket` only counts wickets credited to the bowler.
    """
    dismissed = df["player_dismissed"]
    return int((dismissed.notna() & (dismissed != "Not Out")).sum())


def summarize_batter(player_df: pd.DataFrame) -> Dict[str, Any]:
    """Career batting line for the deliveries faced by one batter."""
    runs = int(player_df["runs"].sum())
    balls = int(len(player_df))
    matches = int(player_df["match_id"].nunique())
    return {
        "total_runs": runs,
        "balls_faced": balls,
        "strike_rate": strike_rate(runs, balls),
        "matches_played": matches,
        "runs_per_match": per_match(runs, matches),
    }


def summarize_bowler(player_df: pd.DataFrame) -> Dict[str, Any]:
    """Career bowling line for the deliveries bowled by one bowler (bowler-credited wickets)."""
    runs_col, wicket_col = resolve_bowling_columns(player_df)
    runs = int(player_df[runs_col].sum())
    wickets = int(player_df[wicket_col].sum())
    balls = int(len(player_df))
    matches = int(player_df["match_id"].nunique())
    return {
        "wickets": wickets,
        "runs_conceded": runs,
        "overs_bowled": round(balls_to_overs(balls), 1),
        "economy_rate": economy_rate(runs, balls),
        "wickets_per_match": per_match(wickets, matches),
    }


def get_season_match_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Computes unique matches played in each season."""
    year_col = "season_year" if "season_year" in df.columns else "season"
    counts = (
        df.groupby(year_col)["match_id"]
        .nunique()
        .reset_index(name="matches_count")
        .sort_values(year_col)
    )
    return counts


def get_team_win_statistics(df: pd.DataFrame, min_matches: int = 0) -> pd.DataFrame:
    """Calculates matches played, matches won, and win percentage for all franchises.

    Deduplicates correctly on match_id and merges appearances across both batting and bowling innings.
    """
    # 1. Total unique matches where team participated (either batting or bowling)
    batting_matches = df[["match_id", "batting_team"]].rename(columns={"batting_team": "team"})
    bowling_matches = df[["match_id", "bowling_team"]].rename(columns={"bowling_team": "team"})
    all_team_matches = pd.concat([batting_matches, bowling_matches]).drop_duplicates()
    
    played_counts = (
        all_team_matches.groupby("team")["match_id"]
        .nunique()
        .reset_index(name="matches_played")
    )

    # 2. Total unique matches won
    matches_unique = df.drop_duplicates(subset=["match_id"])
    win_col = "match_won_by" if "match_won_by" in df.columns else "winning_team"
    
    wins_counts = (
        matches_unique[win_col]
        .value_counts()
        .reset_index()
    )
    wins_counts.columns = ["team", "matches_won"]

    # 3. Merge and compute win percentage
    stats = played_counts.merge(wins_counts, on="team", how="left")
    stats["matches_won"] = stats["matches_won"].fillna(0).astype(int)
    stats["win_percentage"] = (
        (stats["matches_won"] / stats["matches_played"]) * 100
    ).round(2)

    if min_matches > 0:
        stats = stats[stats["matches_played"] >= min_matches]

    stats = stats.sort_values(by=["win_percentage", "matches_won"], ascending=False).reset_index(drop=True)
    return stats


def get_top_batsmen(
    df: pd.DataFrame,
    min_matches: int = MIN_BATTER_MATCHES_FILTER,
    limit: int = 15,
) -> pd.DataFrame:
    """Aggregates all-time batting performance metrics (runs, strike rate, average)."""
    batter_stats = (
        df.groupby("batter")
        .agg(
            total_runs=("runs", "sum"),
            balls_faced=("match_id", "count"),
            matches_played=("match_id", "nunique"),
        )
        .reset_index()
    )

    batter_stats = batter_stats[batter_stats["matches_played"] >= min_matches].copy()
    batter_stats["strike_rate"] = strike_rate(batter_stats["total_runs"], batter_stats["balls_faced"])
    batter_stats["runs_per_match"] = per_match(batter_stats["total_runs"], batter_stats["matches_played"])

    top_batsmen = (
        batter_stats.sort_values(by="total_runs", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
    return top_batsmen


def get_top_bowlers(
    df: pd.DataFrame,
    min_overs: float = MIN_BOWLER_OVERS_FILTER,
    limit: int = 15,
) -> pd.DataFrame:
    """Aggregates all-time bowling performance metrics (wickets, economy, average).

    Uses all delivery rows as balls bowled and bowler-conceded runs. `wickets` counts
    bowler-credited wickets only (run outs are excluded); see `count_dismissals`.
    """
    runs_col, wicket_col = resolve_bowling_columns(df)

    bowler_stats = (
        df.groupby("bowler")
        .agg(
            runs_conceded=(runs_col, "sum"),
            wickets=(wicket_col, "sum"),
            balls_bowled=("match_id", "count"),
            matches_played=("match_id", "nunique"),
        )
        .reset_index()
    )

    bowler_stats = bowler_stats[balls_to_overs(bowler_stats["balls_bowled"]) >= min_overs].copy()

    bowler_stats["economy_rate"] = economy_rate(bowler_stats["runs_conceded"], bowler_stats["balls_bowled"])
    bowler_stats["overs"] = balls_to_overs(bowler_stats["balls_bowled"]).round(1)  # display only
    bowler_stats["wickets_per_match"] = per_match(bowler_stats["wickets"], bowler_stats["matches_played"])
    bowler_stats["strike_rate_balls_per_wicket"] = np.where(
        bowler_stats["wickets"] > 0,
        (bowler_stats["balls_bowled"] / bowler_stats["wickets"]).round(1),
        np.nan,
    )

    top_bowlers = (
        bowler_stats.sort_values(by="wickets", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
    return top_bowlers


def get_toss_impact(df: pd.DataFrame) -> Dict[str, float]:
    """Calculates the proportion of matches won by the toss winning team."""
    win_col = "match_won_by" if "match_won_by" in df.columns else "winning_team"
    match_data = df.drop_duplicates(subset=["match_id"])[["match_id", "toss_winner", win_col]].copy()
    match_data = match_data.dropna(subset=["toss_winner", win_col])
    
    match_data["toss_winner_won"] = match_data["toss_winner"] == match_data[win_col]
    total_matches = len(match_data)
    won_count = int(match_data["toss_winner_won"].sum())
    lost_count = total_matches - won_count
    win_pct = round((won_count / total_matches * 100), 2) if total_matches > 0 else 0.0

    return {
        "total_matches": total_matches,
        "toss_winner_won_count": won_count,
        "toss_winner_lost_count": lost_count,
        "toss_win_percentage": win_pct,
    }


def get_innings_run_distribution(df: pd.DataFrame) -> Dict[str, float]:
    """Computes total run shares between first and second innings."""
    regular_inns = df[df["innings"].isin([1, 2])]
    runs_by_inns = regular_inns.groupby("innings")["runs_total"].sum()
    
    first = int(runs_by_inns.get(1, 0))
    second = int(runs_by_inns.get(2, 0))
    total = first + second

    return {
        "first_innings_runs": first,
        "second_innings_runs": second,
        "first_innings_share_pct": round((first / total * 100), 2) if total > 0 else 0.0,
        "second_innings_share_pct": round((second / total * 100), 2) if total > 0 else 0.0,
    }


def get_phase_scoring_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates runs per over across PowerPlay (1-6), Middle (7-15), and Death (16-20)."""
    if "phase" not in df.columns:
        from src.data_cleaning import assign_over_phase
        df = df.copy()
        df["phase"] = df["over"].apply(assign_over_phase)

    phase_stats = (
        df.groupby("phase", observed=True)
        .agg(
            total_runs=("runs_total", "sum"),
            deliveries=("match_id", "count"),
        )
        .reset_index()
    )

    phase_stats["overs"] = phase_stats["deliveries"] / 6.0
    phase_stats["runs_per_over"] = (phase_stats["total_runs"] / phase_stats["overs"]).round(2)
    phase_stats["phase"] = pd.Categorical(phase_stats["phase"], categories=PHASE_ORDER, ordered=True)
    phase_stats = phase_stats.sort_values("phase").reset_index(drop=True)
    return phase_stats


def get_chase_success_rates(df: pd.DataFrame) -> Tuple[float, pd.DataFrame]:
    """Computes chase success probability overall and across target score buckets.

    BUG FIX: Both batting_team and match_won_by are verified to use identical standardized
    franchise names, preventing false mismatches for historical rebrands.
    """
    win_col = "match_won_by" if "match_won_by" in df.columns else "winning_team"

    # Max score reached in regular innings 1 and 2
    match_innings = (
        df[df["innings"].isin([1, 2])]
        .groupby(["match_id", "innings"], as_index=False)
        .agg(team_runs=("runs_total", "sum"), batting_team=("batting_team", "first"))
    )

    first_inns = match_innings[match_innings["innings"] == 1][["match_id", "team_runs"]].rename(
        columns={"team_runs": "target"}
    )
    second_inns = match_innings[match_innings["innings"] == 2][
        ["match_id", "team_runs", "batting_team"]
    ].rename(columns={"team_runs": "runs_chased"})

    match_results = df.drop_duplicates(subset=["match_id"])[["match_id", win_col]].rename(
        columns={win_col: "match_winner"}
    )

    chase_data = first_inns.merge(second_inns, on="match_id", how="inner")
    chase_data = chase_data.merge(match_results, on="match_id", how="left")
    chase_data = chase_data.dropna(subset=["match_winner"])

    # True chase victory: Team batting second matches official match winner
    chase_data["chase_successful"] = (
        chase_data["batting_team"] == chase_data["match_winner"]
    ).astype(int)

    overall_success = round(float(chase_data["chase_successful"].mean() * 100), 2)

    def categorize_target(score: float) -> str:
        if score < 130:
            return TARGET_LOW
        if score < 160:
            return TARGET_MEDIUM
        return TARGET_HIGH

    chase_data["target_range"] = chase_data["target"].apply(categorize_target)

    success_by_range = (
        chase_data.groupby("target_range", as_index=False)
        .agg(
            attempts=("match_id", "count"),
            successful=("chase_successful", "sum"),
        )
    )
    success_by_range["success_rate"] = (
        (success_by_range["successful"] / success_by_range["attempts"]) * 100
    ).round(2)

    success_by_range["target_range"] = pd.Categorical(
        success_by_range["target_range"], categories=TARGET_ORDER, ordered=True
    )
    success_by_range = success_by_range.sort_values("target_range").reset_index(drop=True)

    return overall_success, success_by_range


def get_home_away_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Computes home vs away win percentage differential per franchise."""
    win_col = "match_won_by" if "match_won_by" in df.columns else "winning_team"
    
    match_level = (
        df[["match_id", "batting_team", "venue", win_col]]
        .drop_duplicates(subset=["match_id", "batting_team"])
        .dropna(subset=[win_col])
    )
    match_level = match_level[match_level[win_col] != "Unknown"]

    # Incur primary home venue (mode venue played)
    team_home_venues = {}
    for team in match_level["batting_team"].unique():
        team_venues = (
            match_level.loc[match_level["batting_team"] == team, "venue"]
            .value_counts()
        )
        if not team_venues.empty:
            team_home_venues[team] = team_venues.index[0]

    stats_list = []
    for team, home_venue in team_home_venues.items():
        team_matches = match_level[match_level["batting_team"] == team]
        
        home = team_matches[team_matches["venue"] == home_venue]
        away = team_matches[team_matches["venue"] != home_venue]
        
        home_tot = len(home)
        home_wins = int((home[win_col] == team).sum())
        home_pct = round((home_wins / home_tot * 100), 2) if home_tot > 0 else 0.0

        away_tot = len(away)
        away_wins = int((away[win_col] == team).sum())
        away_pct = round((away_wins / away_tot * 100), 2) if away_tot > 0 else 0.0

        stats_list.append({
            "team": team,
            "home_venue": home_venue,
            "home_matches": home_tot,
            "home_wins": home_wins,
            "home_win_pct": home_pct,
            "away_matches": away_tot,
            "away_wins": away_wins,
            "away_win_pct": away_pct,
            "home_advantage": round(home_pct - away_pct, 2),
        })

    result_df = pd.DataFrame(stats_list).sort_values("home_advantage", ascending=False).reset_index(drop=True)
    return result_df


def get_cumulative_season_runs(df: pd.DataFrame) -> pd.DataFrame:
    """Computes year-by-year and cumulative tournament run growth."""
    year_col = "season_year" if "season_year" in df.columns else "season"
    regular = df[df["innings"].isin([1, 2])]
    
    annual = (
        regular.groupby(year_col)["runs_total"]
        .sum()
        .reset_index(name="annual_runs")
        .sort_values(year_col)
    )
    annual["cumulative_runs"] = annual["annual_runs"].cumsum()
    return annual


def generate_summary_statistics_df(df: pd.DataFrame) -> pd.DataFrame:
    """Compiles comprehensive high-level tournament KPI table."""
    win_col = "match_won_by" if "match_won_by" in df.columns else "winning_team"
    matches_unique = df.drop_duplicates(subset=["match_id"])
    
    overall_chase, _ = get_chase_success_rates(df)
    toss_stats = get_toss_impact(df)
    home_away = get_home_away_performance(df)
    top_bat = get_top_batsmen(df, min_matches=MIN_BATTER_MATCHES_FILTER, limit=1).iloc[0]
    top_bowl = get_top_bowlers(df, min_overs=MIN_BOWLER_OVERS_FILTER, limit=1).iloc[0]
    team_stats = get_team_win_statistics(df, min_matches=MIN_TEAM_MATCHES_CONSISTENCY).iloc[0]

    min_yr = df["season_year"].min() if "season_year" in df.columns else df["season"].min()
    max_yr = df["season_year"].max() if "season_year" in df.columns else df["season"].max()

    metrics = [
        ("Total Matches", f"{matches_unique.shape[0]:,}"),
        ("Total Deliveries Recorded", f"{len(df):,}"),
        ("Seasons Covered", f"{min_yr} - {max_yr}"),
        ("Active / Historical Franchises", str(df["batting_team"].nunique())),
        ("Venues Hosted", str(df["venue"].nunique())),
        ("Top Career Run Scorer", f"{top_bat['batter']} ({int(top_bat['total_runs']):,} runs)"),
        ("Top Career Wicket Taker", f"{top_bowl['bowler']} ({int(top_bowl['wickets']):,} wickets)"),
        ("Overall Chase Win Probability", f"{overall_chase:.1f}%"),
        ("Toss Winner Match Win Rate", f"{toss_stats['toss_win_percentage']:.1f}%"),
        ("Average Franchise Home Advantage", f"{home_away['home_advantage'].mean():.2f}%"),
        (f"Most Consistent Team (min {MIN_TEAM_MATCHES_CONSISTENCY} matches)", f"{team_stats['team']} ({team_stats['win_percentage']:.1f}%)"),
    ]

    return pd.DataFrame(metrics, columns=["Metric", "Value"])
