"""Pandera data validation schemas and golden dataset evaluation harness."""

import logging
import os
from typing import Any, Dict
import pandas as pd

# Suppress pandera deprecated pandas import warning
os.environ["DISABLE_PANDERA_IMPORT_WARNING"] = "True"

try:
    import pandera.pandas as pa
    from pandera.pandas import Check, Column, DataFrameSchema
except ImportError:
    import pandera as pa
    from pandera import Check, Column, DataFrameSchema

logger = logging.getLogger(__name__)

# Pandera Schema Contract for Cleaned Deliveries
IPLDeliveriesSchema = DataFrameSchema(
    columns={
        "match_id": Column(int, Check.greater_than(0), nullable=False),
        "innings": Column(int, Check.isin([1, 2, 3, 4, 5, 6]), nullable=False),
        "over": Column(int, Check.in_range(0, 19), nullable=False),
        "ball": Column(int, Check.in_range(1, 15), nullable=False),
        "batting_team": Column(str, Check.str_length(min_value=2), nullable=False),
        "bowling_team": Column(str, Check.str_length(min_value=2), nullable=False),
        "batter": Column(str, Check.str_length(min_value=1), nullable=False),
        "bowler": Column(str, Check.str_length(min_value=1), nullable=False),
        "runs": Column(int, Check.in_range(0, 7), nullable=False),
        "extras": Column(int, Check.in_range(0, 7), nullable=False),
        "runs_total": Column(int, Check.in_range(0, 10), nullable=False),
        "is_wicket": Column(int, Check.isin([0, 1]), nullable=False),
    },
    coerce=True,
    strict=False,  # Allow additional informational columns
)


def validate_deliveries_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Validates DataFrame against the strict Pandera schema contract."""
    logger.info("Executing Pandera schema validation...")
    validated = IPLDeliveriesSchema.validate(df)
    logger.info("Pandera schema validation passed successfully.")
    return validated


def run_evaluation_suite(df: pd.DataFrame) -> Dict[str, Any]:
    """Executes golden-dataset benchmark assertions on historical IPL metrics.

    Verifies against canonical tournament facts:
    1. Schema conforms to structural constraints.
    2. V Kohli is the verified all-time leading run scorer (>8,000 runs).
    3. YS Chahal is among the top 3 all-time wicket takers (>200 wickets).
    4. Historical toss win rate sits in realistic range [47%, 54%].
    5. Historical chase win rate sits in realistic range [48%, 56%].
    """
    logger.info("Starting Golden Dataset Evaluation Suite...")
    checks_passed = 0
    total_checks = 5
    report = {}

    # Check 1: Schema validation
    try:
        validate_deliveries_dataframe(df)
        report["schema_validation"] = "PASSED"
        checks_passed += 1
    except Exception as exc:
        report["schema_validation"] = f"FAILED: {exc}"

    # Check 2: Top run scorer verification
    top_scorer_series = df.groupby("batter")["runs"].sum()
    top_batter = top_scorer_series.idxmax()
    top_batter_runs = int(top_scorer_series.max())
    if "Kohli" in top_batter and top_batter_runs >= 8000:
        report["top_batter_check"] = f"PASSED ({top_batter}: {top_batter_runs:,} runs)"
        checks_passed += 1
    else:
        report["top_batter_check"] = f"FAILED (Found {top_batter} with {top_batter_runs} runs)"

    # Check 3: Top wicket taker verification
    wicket_series = df[df["is_wicket"] > 0].groupby("bowler")["is_wicket"].sum()
    top_bowlers = wicket_series.sort_values(ascending=False).head(3).index.tolist()
    if any("Chahal" in b for b in top_bowlers):
        report["top_bowler_check"] = f"PASSED (Chahal in top 3: {top_bowlers})"
        checks_passed += 1
    else:
        report["top_bowler_check"] = f"FAILED (Top 3: {top_bowlers})"

    # Check 4: Toss win rate sanity check
    from src.metrics import get_toss_impact
    toss_stats = get_toss_impact(df)
    toss_pct = toss_stats["toss_win_percentage"]
    if 47.0 <= toss_pct <= 54.0:
        report["toss_rate_check"] = f"PASSED ({toss_pct:.1f}%)"
        checks_passed += 1
    else:
        report["toss_rate_check"] = f"FAILED ({toss_pct:.1f}% outside [47%, 54%])"

    # Check 5: Corrected chase win rate sanity check
    from src.metrics import get_chase_success_rates
    chase_pct, _ = get_chase_success_rates(df)
    if 48.0 <= chase_pct <= 56.0:
        report["chase_rate_check"] = f"PASSED ({chase_pct:.1f}%)"
        checks_passed += 1
    else:
        report["chase_rate_check"] = f"FAILED ({chase_pct:.1f}% outside [48%, 56%])"

    report["evaluation_score"] = f"{checks_passed}/{total_checks}"
    report["status"] = "ALL_CHECKS_PASSED" if checks_passed == total_checks else "FAILURES_DETECTED"
    
    logger.info(f"Evaluation finished: {report['status']} ({report['evaluation_score']})")
    return report
